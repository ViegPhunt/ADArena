from datetime import datetime
from typing import Optional
from sqlalchemy import select

from lib.models import ScheduleHistory, get_session_factory


async def get_last_run(schedule_id: str) -> Optional[datetime]:
    """
    Get the last execution time for a scheduled task.
    
    Used by ticker to implement idempotent operations:
    - 'start_game': Ensures game starts only once
    - 'rounds': Tracks when last round was processed
    
    This prevents duplicate execution if ticker restarts.
    """
    session_factory = get_session_factory()
    async with session_factory() as db:
        result = await db.execute(
            select(ScheduleHistory.last_run).where(ScheduleHistory.id == schedule_id)
        )
        last_run = result.scalar_one_or_none()
        return last_run


async def save_last_run(schedule_id: str, run_time: datetime) -> None:
    """
    Record execution time for a scheduled task.
    
    Uses PostgreSQL UPSERT (INSERT ... ON CONFLICT DO UPDATE)
    to handle both initial insert and subsequent updates.
    """
    from sqlalchemy.dialects.postgresql import insert
    
    session_factory = get_session_factory()
    async with session_factory() as db:
        stmt = insert(ScheduleHistory).values(
            id=schedule_id,
            last_run=run_time
        ).on_conflict_do_update(
            index_elements=['id'],
            set_={'last_run': run_time}
        )
        
        await db.execute(stmt)
        await db.commit()