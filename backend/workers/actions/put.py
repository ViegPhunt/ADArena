import logging
import asyncio
import secrets

from sqlalchemy import update as sql_update

from lib.models import get_session_factory, Flag, TeamTask
from lib.utils.checkers import CheckerRunner
from lib.repositories.teamtasks import get_status_update_expression, get_message_update_expression

from .helpers import (
    logger as base_logger,
    run_checker_sync,
    get_status_code,
    wait_for_check_completion,
    load_team_and_task,
    update_teamtask_skipped,
    update_teamtask_error,
    record_action_to_monitor,
    _get_executor,
)

logger = logging.getLogger(__name__)


async def put_action(
    ctx: dict,
    team_id: int,
    task_id: int,
    current_round: int,
) -> dict:
    """Execute PUT action to plant a flag on a service.
    
    Architecture:
    - Waits for CHECK completion via Redis Pub/Sub + DB fallback
    - Skips execution if CHECK failed (status 104/110)
    - Generates cryptographically secure flag
    - Caches flag in Redis for fast GET lookups
    - Runs checker in thread pool
    - Atomic SQL updates with computed overall status
    
    Flag Format:
    - flag_str: "FLAG" + 32 hex characters (secrets.token_hex)
    - public_flag_data: Random place number (1 to task.places)
    - private_flag_data: 64 hex characters for internal use
    - vuln_number: Always 1 (multi-vuln support reserved)
    
    Args:
        ctx: Arq worker context
        team_id: Target team ID
        task_id: Target task/service ID
        current_round: Current game round number
        
    Returns:
        Dictionary with keys:
        - status: Status string (UP, DOWN, MUMBLE, CORRUPT, CHECK_FAILED, SKIPPED)
        - public: Public-facing message
        - private: Admin-only debug message
        - flag: Generated flag string (None if skipped/failed)
    """
    logger.info(f"Running PUT for team {team_id} task {task_id}, round {current_round}")
    
    # Wait for CHECK completion via Pub/Sub (with DB fallback)
    # This ensures we don't waste resources on broken services
    check_status = await wait_for_check_completion(team_id, task_id, current_round)
    
    if check_status is None:
        logger.error(f"CHECK completely failed for team {team_id} task {task_id}")
    
    session_factory = get_session_factory()
    async with session_factory() as db:
        try:
            # Skip if CHECK failed
            if check_status in [110, 104]:  # CHECK_FAILED or DOWN
                logger.info(f"CHECK failed for team {team_id} task {task_id} (status={check_status}), skipping PUT")
                
                await update_teamtask_skipped(
                    db, team_id, task_id, 'put', 
                    check_status, "Skipped: CHECK failed"
                )
                
                return {
                    "status": "SKIPPED",
                    "public": "Service down, PUT skipped",
                    "private": f"CHECK status: {check_status}",
                    "flag": None,
                }
            
            # Proceed with PUT
            team, task = await load_team_and_task(db, team_id, task_id)
            
            # Generate cryptographically secure flag components
            # secrets module uses os.urandom for CSPRNG
            place = secrets.choice(range(1, task.places + 1))
            flag_str = f"FLAG{secrets.token_hex(16)}"
            
            flag = Flag(
                flag=flag_str,
                team_id=team_id,
                task_id=task_id,
                round=current_round,
                public_flag_data=str(place),
                private_flag_data=secrets.token_hex(32),
                vuln_number=1,
            )
            db.add(flag)
            await db.flush()
            
            # Cache flag in Redis
            from lib.repositories import flags as flag_repo
            from lib.repositories.config import get_current_game_config
            
            game_config = await get_current_game_config(db)
            await flag_repo.cache_flag(
                flag_id=flag.id,
                team_id=team_id,
                task_id=task_id,
                flag_str=flag_str,
                round_num=current_round,
                public_flag_data=flag.public_flag_data,
                flag_lifetime=game_config.flag_lifetime,
                round_time=game_config.round_time,
            )
            
            # Run checker
            checker = CheckerRunner(team=team, task=task, logger=logger, flag=flag)
            loop = asyncio.get_event_loop()
            verdict_obj = await loop.run_in_executor(_get_executor(), run_checker_sync, checker, 'put')
            
            status_code = get_status_code(verdict_obj.status.name)
            
            # Atomic update
            await db.execute(
                sql_update(TeamTask)
                .where(
                    (TeamTask.team_id == team_id) & 
                    (TeamTask.task_id == task_id)
                )
                .values(
                    put_status=status_code,
                    put_message=verdict_obj.public_message[:500],
                    put_private=verdict_obj.private_message[:2000],
                    put_attempts=TeamTask.put_attempts + 1,
                    status=get_status_update_expression(),
                    public_message=get_message_update_expression(),
                )
            )
            await db.commit()
            
            logger.info(f"PUT completed for team {team_id} task {task_id}: {verdict_obj.status.name}")
            
            # Record result
            await record_action_to_monitor(
                action='put',
                team_id=team_id,
                task_id=task_id,
                current_round=current_round,
                status=verdict_obj.status.name,
                status_code=status_code,
                public_message=verdict_obj.public_message,
                private_message=verdict_obj.private_message,
                flag=flag_str,
            )
            
            return {
                "status": verdict_obj.status.name,
                "public": verdict_obj.public_message,
                "private": verdict_obj.private_message,
                "flag": flag_str,
            }
            
        except Exception as e:
            await db.rollback()
            logger.error(f"PUT failed for team {team_id} task {task_id}: {e}", exc_info=True)
            
            try:
                await update_teamtask_error(db, team_id, task_id, 'put', e)
            except Exception as inner_e:
                logger.error(f"Failed to update TeamTask on error: {inner_e}")
            
            # Record failure to monitoring
            await record_action_to_monitor(
                action='put',
                team_id=team_id,
                task_id=task_id,
                current_round=current_round,
                status='CHECK_FAILED',
                status_code=110,
                public_message='PUT action failed',
                private_message=str(e),
                flag=None,
            )
            
            return {
                "status": "CHECK_FAILED",
                "public": "PUT action failed",
                "private": str(e),
                "flag": None,
            }
