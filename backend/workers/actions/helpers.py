"""Common utilities for CHECK/PUT/GET actions.

Provides shared functionality used across all action types:
- Checker execution in thread pool (blocking I/O isolation)
- Status code mapping from TaskStatus enum to integers
- CHECK completion waiting with Pub/Sub + DB fallback
- Database entity loading helpers
- Atomic TeamTask update functions
- Action result recording to monitoring coordinator

Constants:
    MAX_RETRIES: Maximum retry attempts for DB fallback (3)
    INITIAL_BACKOFF: Initial backoff delay in seconds (1.0)
    CHECK_WAIT_TIMEOUT: Maximum wait time for CHECK completion (60.0s)
"""
import os
import logging
import asyncio
from typing import Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from lib.models import get_session_factory, Team, Task, TeamTask
from lib.utils.checkers import CheckerRunner
from lib.repositories.teamtasks import get_status_update_expression, get_message_update_expression
from workers.action_coordinator import get_coordinator, ActionResult

logger = logging.getLogger(__name__)

_executor: Optional[ThreadPoolExecutor] = None

def _get_executor() -> ThreadPoolExecutor:
    """Get or create thread pool executor."""
    global _executor
    if _executor is None:
        threads = int(os.getenv('CHECKERS'))
        _executor = ThreadPoolExecutor(max_workers=threads)
        logger.info(f"Initialized checker thread pool with {threads} threads")
    return _executor

# Configuration constants - loaded once from DB and cached
_round_time: Optional[int] = None

def _load_round_time() -> int:
    """Load round_time from database once and cache it."""
    global _round_time
    
    if _round_time is not None:
        return _round_time
    
    from lib.repositories import game
    
    loop = asyncio.get_event_loop()
    session_factory = get_session_factory()
    
    async def _fetch():
        async with session_factory() as db:
            config = await game.get_current_game_config(db)
            return config.round_time
    
    _round_time = loop.run_until_complete(_fetch())
    return _round_time

def get_max_retries() -> int:
    """Get maximum retry attempts for DB fallback.
    
    Scales with round_time:
    - round_time <= 60s: 2 retries
    - round_time <= 120s: 3 retries
    - round_time <= 300s: 5 retries
    - round_time > 300s: 7 retries
    
    Can override with MAX_RETRIES env var.
    """
    env_retries = os.getenv('MAX_RETRIES')
    if env_retries:
        return int(env_retries)
    
    round_time = _load_round_time()
    
    if round_time <= 60:
        return 2
    elif round_time <= 120:
        return 3
    elif round_time <= 300:
        return 5
    else:
        return 7

def get_initial_backoff() -> float:
    """Get initial backoff delay for DB fallback retries.
    
    Defaults to 1.5% of round_time, clamped between 0.5s and 5.0s.
    Can override with INITIAL_BACKOFF env var.
    """
    env_backoff = os.getenv('INITIAL_BACKOFF')
    if env_backoff:
        return float(env_backoff)
    
    round_time = _load_round_time()
    # 1.5% of round_time, clamped between 0.5s and 5.0s
    return max(0.5, min(5.0, round_time * 0.015))

def get_check_wait_timeout() -> float:
    """Get CHECK wait timeout based on game config.
    
    Defaults to 60% of round_time to ensure PUT/GET have time to execute.
    Can override with CHECK_WAIT_TIMEOUT env var.
    """
    env_timeout = os.getenv('CHECK_WAIT_TIMEOUT')
    if env_timeout:
        return float(env_timeout)
    
    round_time = _load_round_time()
    return round_time * 0.6


def run_checker_sync(checker: CheckerRunner, action: str) -> Any:
    """Execute checker action synchronously in thread pool.
    
    Isolates blocking checker execution from async event loop.
    Called via loop.run_in_executor() from async actions.
    
    Args:
        checker: Configured CheckerRunner instance
        action: Action type ('check', 'put', or 'get')
        
    Returns:
        CheckerVerdict object with status and messages
        
    Raises:
        ValueError: If action type is invalid
    """
    if action == 'check':
        return checker.check()
    elif action == 'put':
        return checker.put()
    elif action == 'get':
        return checker.get()
    else:
        raise ValueError(f"Unknown action: {action}")


def get_status_code(status_name: str) -> int:
    """Convert TaskStatus string to numeric status code.
    
    Status codes:
        101: OK/UP - Service healthy
        102: CORRUPT - Service returned invalid data
        103: MUMBLE - Service returned unexpected response
        104: DOWN - Service unreachable
        110: CHECK_FAILED - Action exception occurred
        
    Args:
        status_name: Status string from TaskStatus enum
        
    Returns:
        Integer status code (defaults to 110 if unknown)
    """
    status_map = {
        "OK": 101,
        "UP": 101,
        "CORRUPT": 102,
        "MUMBLE": 103,
        "DOWN": 104,
        "CHECK_FAILED": 110,
    }
    return status_map.get(status_name, 110)


async def wait_for_check_completion(
    team_id: int, 
    task_id: int, 
    current_round: int
) -> Optional[int]:
    """Wait for CHECK action to complete before running PUT/GET.
    
    Uses two-tier strategy:
    1. Redis Pub/Sub for real-time notifications (primary)
    2. Database polling with exponential backoff (fallback)
    
    Args:
        team_id: Team ID
        task_id: Task ID
        current_round: Current round number
        
    Returns:
        CHECK status code (101-110), or None if timeout
    """
    timeout = get_check_wait_timeout()
    coordinator = await get_coordinator()
    check_status = await coordinator.wait_for_check(
        team_id, task_id, current_round, timeout
    )
    
    # Fallback to DB polling if Pub/Sub timeout
    if check_status is None:
        logger.warning(f"CHECK pub/sub timeout for team {team_id} task {task_id}, trying DB fallback")
        
        max_retries = get_max_retries()
        backoff = get_initial_backoff()
        
        session_factory = get_session_factory()
        for retry in range(1, max_retries + 1):
            async with session_factory() as db:
                result = await db.execute(
                    select(TeamTask.check_status)
                    .where(
                        (TeamTask.team_id == team_id) & 
                        (TeamTask.task_id == task_id)
                    )
                )
                row = result.one_or_none()
                
                if row and row.check_status != -1:
                    check_status = row.check_status
                    break
                
                if retry < max_retries:
                    await asyncio.sleep(backoff)
    
    return check_status


async def load_team_and_task(
    db: AsyncSession, 
    team_id: int, 
    task_id: int
) -> Tuple[Team, Task]:
    """Load Team and Task entities from database.
    
    Args:
        db: Async database session
        team_id: Team ID to load
        task_id: Task ID to load
        
    Returns:
        Tuple of (Team, Task) ORM objects
        
    Raises:
        NoResultFound: If team or task doesn't exist
    """
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one()
    
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one()
    
    return team, task


async def update_teamtask_skipped(
    db: AsyncSession,
    team_id: int,
    task_id: int,
    action: str,
    status_code: int,
    message: str
):
    """Update TeamTask when action is skipped due to dependency failure.
    
    Used when PUT/GET skips execution because CHECK failed.
    Atomically updates action-specific fields and recomputes overall status.
    
    Args:
        db: Async database session
        team_id: Team ID
        task_id: Task ID  
        action: Action type ('put' or 'get')
        status_code: Inherited status code from CHECK
        message: Skip reason message
    """
    field_prefix = action
    
    await db.execute(
        sql_update(TeamTask)
        .where(
            (TeamTask.team_id == team_id) & 
            (TeamTask.task_id == task_id)
        )
        .values(**{
            f"{field_prefix}_status": status_code,
            f"{field_prefix}_message": message,
            f"{field_prefix}_attempts": getattr(TeamTask, f"{field_prefix}_attempts") + 1,
            "status": get_status_update_expression(),
            "public_message": get_message_update_expression(),
        })
    )
    await db.commit()


async def update_teamtask_error(
    db: AsyncSession,
    team_id: int,
    task_id: int,
    action: str,
    error: Exception
):
    """Update TeamTask when action raises an exception.
    
    Sets status to CHECK_FAILED (110) and records error details.
    Increments check counter if action is CHECK.
    
    Args:
        db: Async database session
        team_id: Team ID
        task_id: Task ID
        action: Action type ('check', 'put', or 'get')
        error: Exception that was raised
    """
    field_prefix = action
    
    values = {
        f"{field_prefix}_status": 110,  # CHECK_FAILED
        f"{field_prefix}_message": f"{action.upper()} action failed",
        f"{field_prefix}_private": str(error)[:2000],
        f"{field_prefix}_attempts": getattr(TeamTask, f"{field_prefix}_attempts") + 1,
        "status": get_status_update_expression(),
        "public_message": get_message_update_expression(),
    }
    
    if action == 'check':
        values["checks"] = TeamTask.checks + 1
    
    await db.execute(
        sql_update(TeamTask)
        .where(
            (TeamTask.team_id == team_id) & 
            (TeamTask.task_id == task_id)
        )
        .values(**values)
    )
    await db.commit()


async def record_action_to_monitor(
    action: str,
    team_id: int,
    task_id: int,
    current_round: int,
    status: str,
    status_code: int,
    public_message: str,
    private_message: str,
    flag: Optional[str] = None
):
    """Record action result to monitoring coordinator.
    
    Stores result in Redis for round monitoring and health checks.
    Results expire after 10 minutes (600s).
    
    Args:
        action: Action type ('check', 'put', or 'get')
        team_id: Team ID
        task_id: Task ID
        current_round: Current round number
        status: Status string (UP, DOWN, etc.)
        status_code: Numeric status code (101-110)
        public_message: Public-facing message (truncated to 500 chars)
        private_message: Admin-only message (truncated to 2000 chars)
        flag: Optional flag string (for PUT actions)
    """
    coordinator = await get_coordinator()
    await coordinator.record_action_result(ActionResult(
        action=action,
        team_id=team_id,
        task_id=task_id,
        round=current_round,
        status=status,
        status_code=status_code,
        public_message=public_message[:500],
        private_message=private_message[:2000],
        timestamp=asyncio.get_event_loop().time(),
        flag=flag,
    ))