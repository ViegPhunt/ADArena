import logging
import asyncio

from sqlalchemy import update as sql_update, case as sql_case

from lib.models import get_session_factory, TeamTask
from lib.utils.checkers import CheckerRunner
from lib.repositories.teamtasks import get_status_update_expression, get_message_update_expression
from workers.action_coordinator import get_coordinator

from .helpers import (
    logger as base_logger,
    run_checker_sync,
    get_status_code,
    load_team_and_task,
    update_teamtask_error,
    record_action_to_monitor,
    _get_executor,
)

logger = logging.getLogger(__name__)


async def check_action(
    ctx: dict,
    team_id: int,
    task_id: int,
    current_round: int,
) -> dict:
    """
    CHECK action with atomic SQL updates and computed overall status.
    
    - No locking required (atomic SQL operations)
    - Updates check_status, check_message, check_private, check_attempts
    - Automatically computes overall status inline
    - Signals completion to PUT/GET via Redis Pub/Sub
    
    Args:
        ctx: Arq context (contains Redis pool)
        team_id: Team ID
        task_id: Task ID
        current_round: Current round number
        
    Returns:
        Dictionary with status, public_message, private_message
    """
    logger.info(f"Running CHECK for team {team_id} task {task_id}, round {current_round}")
    
    session_factory = get_session_factory()
    async with session_factory() as db:
        try:
            # Load team and task
            team, task = await load_team_and_task(db, team_id, task_id)
            
            # Run checker in thread pool
            checker = CheckerRunner(team=team, task=task, logger=logger)
            loop = asyncio.get_event_loop()
            verdict_obj = await loop.run_in_executor(_get_executor(), run_checker_sync, checker, 'check')
            
            status_code = get_status_code(verdict_obj.status.name)
            
            # Atomic update with computed overall status
            await db.execute(
                sql_update(TeamTask)
                .where(
                    (TeamTask.team_id == team_id) & 
                    (TeamTask.task_id == task_id)
                )
                .values(
                    # Update CHECK fields atomically
                    check_status=status_code,
                    check_message=verdict_obj.public_message[:500],
                    check_private=verdict_obj.private_message[:2000],
                    check_attempts=TeamTask.check_attempts + 1,
                    
                    # Update counters atomically
                    checks=TeamTask.checks + 1,
                    checks_passed=sql_case(
                        (status_code == 101, TeamTask.checks_passed + 1),
                        else_=TeamTask.checks_passed
                    ),
                    
                    # Compute overall status inline
                    status=get_status_update_expression(),
                    public_message=get_message_update_expression(),
                    private_message=sql_case(
                        (status_code != 101, verdict_obj.private_message[:1000]),
                        else_=TeamTask.private_message
                    ),
                )
            )
            await db.commit()
            
            verdict = {
                "status": verdict_obj.status.name,
                "public": verdict_obj.public_message,
                "private": verdict_obj.private_message,
            }
            
            logger.info(f"CHECK completed for team {team_id} task {task_id}: {verdict['status']}")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"CHECK failed for team {team_id} task {task_id}: {e}", exc_info=True)
            
            try:
                await update_teamtask_error(db, team_id, task_id, 'check', e)
            except Exception as inner_e:
                logger.error(f"Failed to update TeamTask on error: {inner_e}")
            
            verdict = {
                "status": "CHECK_FAILED",
                "public": "CHECK action failed",
                "private": str(e),
            }
            status_code = 110
    
    # Signal and record AFTER DB session closes (prevents race condition)
    # This ensures transaction is committed before PUT/GET are notified
    coordinator = await get_coordinator()
    await coordinator.signal_check_complete(team_id, task_id, current_round, status_code)
    
    await record_action_to_monitor(
        action='check',
        team_id=team_id,
        task_id=task_id,
        current_round=current_round,
        status=verdict['status'],
        status_code=status_code,
        public_message=verdict['public'],
        private_message=verdict['private'],
    )
    
    return verdict
