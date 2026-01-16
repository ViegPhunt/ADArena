"""Game clock service that manages game start and round progression.

Responsibilities:
- Start game at configured start_time
- Advance rounds at configured intervals
- Update game state and scores
- Submit checker jobs for each round
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from lib.models import get_session_factory
from lib.repositories import game, tasks, teams, caching, teamtasks
from lib.repositories.schedules import get_last_run, save_last_run


logger = logging.getLogger('ticker')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class TickerService:
    """Game clock that starts game and advances rounds on schedule.
    
    Runs in tight loop (100ms) checking for start time and round transitions.
    Uses last_run persistence to prevent duplicate actions after restart.
    """
    
    def __init__(self):
        self.running = False
        self.game_started = False
        self.start_time: Optional[datetime] = None
        self.round_interval: Optional[timedelta] = None
        self.last_start_check: Optional[datetime] = None
        self.last_round_check: Optional[datetime] = None

    async def initialize(self):
        """Load game config and last run timestamps."""
        session_factory = get_session_factory()
        async with session_factory() as db:
            self.game_started = await game.get_game_running(db)

            config = await game.get_current_game_config(db)
            self.start_time = config.start_time
            round_time = config.round_time
            self.round_interval = timedelta(seconds=round_time)

            self.last_start_check = await get_last_run('start_game')
            self.last_round_check = await get_last_run('rounds')

        logger.info(f"Ticker initialized - Game started: {self.game_started}")
        logger.info(f"Start time: {self.start_time}, Round interval: {self.round_interval}")

    async def check_start_game(self, now: datetime):
        """Start game when reaching start_time.
        
        Uses last_run to prevent duplicate start after restart.
        """
        if self.game_started:
            return

        if now < self.start_time:
            return

        if self.last_start_check and self.last_start_check >= self.start_time:
            logger.info("Start game already executed")
            self.game_started = True
            return

        logger.info("Starting game...")
        await self.start_game()
        
        self.last_start_check = now
        await save_last_run('start_game', now)
        self.game_started = True
    
    async def start_game(self):
        """Initialize game state and submit round 0 checker jobs.
        
        Sets game_running=True, caches config to Redis, submits initial CHECKs.
        """
        session_factory = get_session_factory()
        async with session_factory() as db:
            already_started = await game.get_game_running(db)
            if already_started:
                logger.warning("Game already started")
                return
            
            await game.set_round_start(0)
            
            await game.set_game_running(db, True)
            
            # Cache config to Redis for fast access
            logger.info("Caching teams and tasks")
            await caching.cache_teams(db)
            await caching.cache_tasks(db)
            await caching.cache_game_config(db)
            
            logger.info("Initializing game state for round 0")
            game_state = await game.update_game_state(db, 0)
            
            logger.info("Submitting initial checker jobs")
            from workers.job_submitter import submit_initial_checks
            job_stats = await submit_initial_checks(db)
            logger.info(f"Initial checker jobs submitted: {job_stats}")
            
            logger.info("=== Game started successfully ===")
    
    async def check_round_tick(self, now: datetime):
        """Advance to next round when interval elapsed.
        
        Uses last_run to calculate next round time.
        """
        if not self.game_started:
            return
        
        if self.last_round_check:
            next_round_time = self.last_round_check + self.round_interval
        else:
            next_round_time = self.start_time + self.round_interval
        
        if now < next_round_time:
            return
        
        logger.info(f"Processing round tick at {now}")
        await self.process_round()
        
        self.last_round_check = now
        await save_last_run('rounds', now)
    
    async def process_round(self):
        """Advance to next round.
        
        Steps:
        1. Update game state and scores for current round
        2. Log TeamTasks to history
        3. Increment round counter
        4. Submit checker jobs for new round
        """
        session_factory = get_session_factory()
        async with session_factory() as db:
            current_round = await game.get_real_round_from_db(db)
            config = await game.get_current_game_config(db)
            
            max_round = config.max_round
            
            if max_round and current_round > max_round:
                logger.info("Reached max round, game finished")
                await game.update_round(db, current_round)
                await game.update_game_state(db, current_round)
                return
            
            logger.info(f"Processing round {current_round}")
            
            await game.update_round(db, current_round)
            new_round = current_round + 1
            
            logger.info(f"Updating game state for round {new_round}")
            await game.update_game_state(db, new_round)
            
            logger.info(f"Updating attack data for round {new_round}")
            await game.update_attack_data(db, new_round)
            
            logger.info(f"Broadcasting scoreboard update")
            await self.broadcast_scoreboard_update(db)
            
            # Archive current scores before recalculation
            logger.info(f"Logging TeamTasks to history for round {current_round}")
            all_teams = await teams.get_teams(db)
            all_tasks = await tasks.get_tasks(db)
            
            for team in all_teams:
                for task in all_tasks:
                    await teamtasks.log_teamtask_to_history(
                        db, team.id, task.id, current_round
                    )
            
            logger.info(f"Submitting checker jobs for round {new_round}")
            from workers.job_submitter import submit_round_jobs
            job_stats = await submit_round_jobs(db, new_round)
            logger.info(f"Checker jobs submitted for round {new_round}: {job_stats}")
            
            logger.info(f"Round {new_round} ready")
    
    async def broadcast_scoreboard_update(self, db):
        """Publish scoreboard update to Redis for WebSocket broadcast."""
        try:
            from lib.repositories import scoreboard
            from lib.repositories.utils import get_redis_client
            import json
            
            scoreboard_data = await scoreboard.construct_scoreboard(db)
            
            redis = get_redis_client()
            event_data = {
                "event_type": "scoreboard_update",
                "event": "update_scoreboard",
                "data": scoreboard_data["state"]
            }
            await redis.publish('adarena-events', json.dumps(event_data, default=str))
        except Exception as e:
            logger.error(f"Failed to broadcast scoreboard update: {e}", exc_info=True)
    
    async def run(self):
        """Main ticker loop. Checks every 100ms for start/round transitions."""
        self.running = True
        logger.info("Ticker service started")
        
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                await self.check_start_game(now)
                
                await self.check_round_tick(now)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in ticker loop: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def stop(self):
        """Stop ticker service and cleanup resources
        
        This method stops the main loop and should be called before shutdown.
        External cleanup (Arq pool, coordinator) should be handled by caller.
        """
        self.running = False
        logger.info("Ticker service stopping...")
        
        # Cleanup resources
        try:
            from workers.job_submitter import close_arq_pool
            from workers.action_coordinator import close_coordinator
            
            logger.info("Closing Arq pool...")
            await close_arq_pool()
            
            logger.info("Closing action coordinator...")
            await close_coordinator()
            
            logger.info("Ticker service stopped successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)


async def main():
    """Main entry point with graceful shutdown support"""
    ticker = TickerService()
    await ticker.initialize()
    
    try:
        await ticker.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        await ticker.stop()
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}", exc_info=True)
        await ticker.stop()
        raise


if __name__ == '__main__':
    asyncio.run(main())