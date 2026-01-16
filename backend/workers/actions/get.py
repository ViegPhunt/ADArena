import logging
import asyncio

from sqlalchemy import select, update as sql_update

from lib.models import get_session_factory, Flag, Team, Task, TeamTask
from lib.utils.checkers import CheckerRunner
from lib.repositories.teamtasks import get_status_update_expression, get_message_update_expression

from .helpers import (
    logger as base_logger,
    run_checker_sync,
    get_status_code,
    wait_for_check_completion,
    update_teamtask_skipped,
    update_teamtask_error,
    record_action_to_monitor,
    _get_executor,
    get_max_retries,
    get_initial_backoff,
)

logger = logging.getLogger(__name__)


async def get_action(
    ctx: dict,
    team_id: int,
    task_id: int,
    current_round: int,
    flag_id: int,
) -> dict:
    """Execute GET action to retrieve a previously planted flag.
    
    Architecture:
    - Waits for CHECK completion via Redis Pub/Sub + DB fallback
    - Polls database for PUT status (PUT doesn't use Pub/Sub due to multiple PUTs)
    - Skips if CHECK or PUT failed (cascading dependency)
    - Loads flag from database with JOIN on Team/Task
    - Runs checker in thread pool
    - Atomic SQL updates with computed overall status
    
    Dependency Chain:
    CHECK (must pass) → PUT (must pass) → GET (can execute)
    
    Args:
        ctx: Arq worker context
        team_id: Target team ID  
        task_id: Target task/service ID
        current_round: Current game round number
        flag_id: Database ID of flag to retrieve
        
    Returns:
        Dictionary with keys:
        - status: Status string (UP, DOWN, MUMBLE, CORRUPT, CHECK_FAILED, SKIPPED)
        - public: Public-facing message
        - private: Admin-only debug message
    """
    logger.info(f"Running GET for team {team_id} task {task_id}, flag {flag_id}, round {current_round}")
    
    # Wait for CHECK to complete
    check_status = await wait_for_check_completion(team_id, task_id, current_round)
    
    # Check PUT status from database with retry logic
    # Note: PUT doesn't signal via Pub/Sub because there can be multiple PUTs per round
    # We poll DB instead to check if at least one PUT succeeded
    put_status = None
    session_factory = get_session_factory()
    
    max_retries = get_max_retries()
    backoff = get_initial_backoff()
    
    for retry in range(1, max_retries + 1):
        async with session_factory() as db:
            result = await db.execute(
                select(TeamTask.check_status, TeamTask.put_status)
                .where(
                    (TeamTask.team_id == team_id) & 
                    (TeamTask.task_id == task_id)
                )
            )
            row = result.one_or_none()
            
            if row and row.check_status != -1:
                if check_status is None:
                    check_status = row.check_status
                put_status = row.put_status
                break
            
            if retry < max_retries:
                await asyncio.sleep(backoff)
    
    async with session_factory() as db:
        try:
            # Skip if CHECK or PUT failed
            if check_status in [110, 104] or put_status in [110, 104]:
                failed_action = "CHECK" if check_status in [110, 104] else "PUT"
                logger.info(f"{failed_action} failed for team {team_id} task {task_id}, skipping GET")
                
                skip_status = check_status if check_status in [110, 104] else put_status
                await update_teamtask_skipped(
                    db, team_id, task_id, 'get',
                    skip_status, f"Skipped: {failed_action} failed"
                )
                
                return {
                    "status": "SKIPPED",
                    "public": "Service issues, GET skipped",
                    "private": f"{failed_action} failed",
                }
            
            # Proceed with GET - load flag with team and task
            result = await db.execute(
                select(Flag, Team, Task)
                .join(Team, Flag.team_id == Team.id)
                .join(Task, Flag.task_id == Task.id)
                .where(Flag.id == flag_id)
            )
            row = result.one_or_none()
            
            if not row:
                logger.warning(f"Flag {flag_id} not found for GET")
                
                await db.execute(
                    sql_update(TeamTask)
                    .where(
                        (TeamTask.team_id == team_id) & 
                        (TeamTask.task_id == task_id)
                    )
                    .values(
                        get_status=103,  # MUMBLE
                        get_message="Flag not found",
                        get_attempts=TeamTask.get_attempts + 1,
                        status=get_status_update_expression(),
                        public_message=get_message_update_expression(),
                    )
                )
                await db.commit()
                
                return {
                    "status": "MUMBLE",
                    "public": "Flag not found",
                    "private": f"Flag ID {flag_id} not in database",
                }
            
            flag, team, task = row
            
            # Run checker
            checker = CheckerRunner(team=team, task=task, logger=logger, flag=flag)
            loop = asyncio.get_event_loop()
            verdict_obj = await loop.run_in_executor(_get_executor(), run_checker_sync, checker, 'get')
            
            status_code = get_status_code(verdict_obj.status.name)
            
            # Atomic update
            await db.execute(
                sql_update(TeamTask)
                .where(
                    (TeamTask.team_id == team_id) & 
                    (TeamTask.task_id == task_id)
                )
                .values(
                    get_status=status_code,
                    get_message=verdict_obj.public_message[:500],
                    get_private=verdict_obj.private_message[:2000],
                    get_attempts=TeamTask.get_attempts + 1,
                    status=get_status_update_expression(),
                    public_message=get_message_update_expression(),
                )
            )
            await db.commit()
            
            logger.info(f"GET completed for flag {flag_id}: {verdict_obj.status.name}")
            
            # Record result
            await record_action_to_monitor(
                action='get',
                team_id=team_id,
                task_id=task_id,
                current_round=current_round,
                status=verdict_obj.status.name,
                status_code=status_code,
                public_message=verdict_obj.public_message,
                private_message=verdict_obj.private_message,
            )
            
            return {
                "status": verdict_obj.status.name,
                "public": verdict_obj.public_message,
                "private": verdict_obj.private_message,
            }
            
        except Exception as e:
            await db.rollback()
            logger.error(f"GET failed for flag {flag_id}: {e}", exc_info=True)
            
            try:
                await update_teamtask_error(db, team_id, task_id, 'get', e)
            except Exception as inner_e:
                logger.error(f"Failed to update TeamTask on error: {inner_e}")
            
            # Record failure to monitoring
            await record_action_to_monitor(
                action='get',
                team_id=team_id,
                task_id=task_id,
                current_round=current_round,
                status='CHECK_FAILED',
                status_code=110,
                public_message='GET action failed',
                private_message=str(e),
            )
            
            return {
                "status": "CHECK_FAILED",
                "public": "GET action failed",
                "private": str(e),
            }
