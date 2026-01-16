"""Round monitoring service for tracking action progress and game health.

Monitors CHECK/PUT/GET action completion rates, error rates,
and provides health status for the current round.
"""

import asyncio
import logging
from typing import Dict, Optional

from lib.models import get_session_factory
from lib.repositories import game, tasks as task_repo, teams as team_repo
from workers.action_coordinator import get_coordinator

logger = logging.getLogger(__name__)


class RoundMonitor:
    """Monitor round progress and game health.
    
    Tracks action completion, error rates, and provides
    health status (HEALTHY/DEGRADED/CRITICAL).
    """
    
    def __init__(self):
        self.current_round = 0
        self.monitoring = False
        
    async def start_monitoring(self):
        """Start monitoring loop. Polls round status every 5 seconds."""
        self.monitoring = True
        logger.info("Round monitor started")
        
        while self.monitoring:
            try:
                session_factory = get_session_factory()
                async with session_factory() as db:
                    self.current_round = await game.get_real_round_from_db(db)
                
                if self.current_round > 0:
                    await self.monitor_round(self.current_round)
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in round monitor: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop monitoring loop."""
        self.monitoring = False
        logger.info("Round monitor stopped")
    
    async def monitor_round(self, round_num: int):
        """Log round progress and errors."""
        coordinator = await get_coordinator()
        
        summary = await coordinator.get_round_summary(round_num)
        
        if summary['errors']:
            logger.warning(
                f"Round {round_num} has {len(summary['errors'])} errors: "
                f"{summary['by_status']}"
            )
            
            for error in summary['errors'][:5]:
                logger.warning(
                    f"  - Team {error['team_id']}, Task {error['task_id']}: "
                    f"{error['action'].upper()} {error['status']} - {error['message']}"
                )
        
        total = summary['total_actions']
        if total > 0:
            logger.debug(
                f"Round {round_num} progress: {total} actions completed - "
                f"CHECK: {summary['by_action']['check']}, "
                f"PUT: {summary['by_action']['put']}, "
                f"GET: {summary['by_action']['get']}"
            )
    
    async def get_round_completion_status(self, round_num: int) -> Dict:
        """Calculate round completion percentage.
        
        Returns round marked complete when progress >= 95%.
        """
        session_factory = get_session_factory()
        coordinator = await get_coordinator()
        
        async with session_factory() as db:
            teams = await team_repo.get_teams(db)
            tasks = await task_repo.get_tasks(db)
            
            # Calculate expected actions
            expected_checks = len(teams) * len(tasks)
            expected_puts = sum(task.puts for task in tasks) * len(teams)
            expected_gets = sum(task.gets for task in tasks) * len(teams)
            expected_total = expected_checks + expected_puts + expected_gets
        
        summary = await coordinator.get_round_summary(round_num)
        completed_total = summary['total_actions']
        
        progress = completed_total / expected_total if expected_total > 0 else 0.0
        completed = progress >= 0.95
        
        return {
            'round': round_num,
            'completed': completed,
            'progress': progress,
            'expected_actions': expected_total,
            'completed_actions': completed_total,
            'expected_breakdown': {
                'check': expected_checks,
                'put': expected_puts,
                'get': expected_gets,
            },
            'completed_breakdown': summary['by_action'],
            'by_status': summary['by_status'],
            'errors': summary['errors'],
        }
    
    async def get_team_task_status(
        self, 
        team_id: int, 
        task_id: int, 
        round_num: int
    ) -> Dict:
        """Get detailed status for specific team-task in round.
        
        Returns CHECK status and all PUT/GET results.
        """
        coordinator = await get_coordinator()
        results = await coordinator.get_round_results(team_id, task_id, round_num)
        
        status = {
            'team_id': team_id,
            'task_id': task_id,
            'round': round_num,
            'check': None,
            'puts': [],
            'gets': [],
            'overall_status': 'PENDING',
        }
        
        if 'check' in results:
            check = results['check']
            status['check'] = {
                'status': check.status,
                'message': check.public_message,
                'timestamp': check.timestamp,
            }
            status['overall_status'] = check.status
        
        for action_name, result in results.items():
            if action_name.startswith('put'):
                status['puts'].append({
                    'status': result.status,
                    'flag': result.flag,
                    'timestamp': result.timestamp,
                })
            elif action_name.startswith('get'):
                status['gets'].append({
                    'status': result.status,
                    'timestamp': result.timestamp,
                })
        
        return status
    
    async def get_global_health(self) -> Dict:
        """Get overall game health status.
        
        Health levels:
        - HEALTHY: < 5% error rate
        - DEGRADED: 5-15% error rate  
        - CRITICAL: > 15% error rate
        """
        coordinator = await get_coordinator()
        session_factory = get_session_factory()
        
        async with session_factory() as db:
            current_round = await game.get_real_round_from_db(db)
            game_running = await game.get_game_running(db)
        
        if current_round == 0:
            return {
                'game_running': game_running,
                'current_round': 0,
                'health': 'WAITING',
                'message': 'Game not started yet',
            }
        
        round_status = await self.get_round_completion_status(current_round)
        
        error_rate = len(round_status['errors']) / max(round_status['completed_actions'], 1)
        
        if error_rate < 0.05:
            health = 'HEALTHY'
        elif error_rate < 0.15:
            health = 'DEGRADED'
        else:
            health = 'CRITICAL'
        
        return {
            'game_running': game_running,
            'current_round': current_round,
            'health': health,
            'progress': round_status['progress'],
            'completed_actions': round_status['completed_actions'],
            'expected_actions': round_status['expected_actions'],
            'error_count': len(round_status['errors']),
            'error_rate': error_rate,
            'status_breakdown': round_status['by_status'],
        }


_monitor: Optional[RoundMonitor] = None


async def get_monitor() -> RoundMonitor:
    """Get singleton RoundMonitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = RoundMonitor()
    return _monitor


async def start_monitor_service():
    monitor = await get_monitor()
    await monitor.start_monitoring()


if __name__ == '__main__':
    asyncio.run(start_monitor_service())