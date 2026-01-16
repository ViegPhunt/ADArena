from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.models import Team as TeamModel
from lib.repositories.utils import get_redis_client
from lib.repositories.keys import CacheKeys


async def get_teams(db: AsyncSession) -> List[TeamModel]:
    result = await db.execute(
        select(TeamModel).where(TeamModel.active == True)
    )
    return result.scalars().all()


async def get_all_teams(db: AsyncSession) -> List[TeamModel]:
    result = await db.execute(select(TeamModel))
    return result.scalars().all()


async def get_team_by_id(db: AsyncSession, team_id: int) -> Optional[TeamModel]:
    result = await db.execute(
        select(TeamModel).where(TeamModel.id == team_id)
    )
    return result.scalar_one_or_none()


async def create_team(db: AsyncSession, team_data: dict) -> TeamModel:
    """
    Create new team and initialize TeamTask records.
    
    For each active task, creates a TeamTask record with:
    - score = task's default_score
    - status = -1 (not checked yet)
    - stolen/lost/checks = 0 (no activity)
    
    This ensures every team has a complete matrix of TeamTask records
    for scoreboard calculations.
    """
    from lib.models import Task as TaskModel, TeamTask
    
    team = TeamModel(**team_data)
    db.add(team)
    await db.flush()
    
    # Get all active tasks and create TeamTask for each
    result = await db.execute(
        select(TaskModel).where(TaskModel.active == True)
    )
    tasks = result.scalars().all()
    
    for task in tasks:
        team_task = TeamTask(
            team_id=team.id,
            task_id=task.id,
            score=task.default_score,
            status=-1,
            stolen=0,
            lost=0,
            checks=0,
            checks_passed=0,
        )
        db.add(team_task)
    
    await db.commit()
    await db.refresh(team)
    
    await flush_teams_cache()
    
    return team


async def update_team(db: AsyncSession, team_id: int, team_data: dict) -> Optional[TeamModel]:
    result = await db.execute(
        select(TeamModel).where(TeamModel.id == team_id)
    )
    team = result.scalar_one_or_none()
    
    if not team:
        return None
    
    for key, value in team_data.items():
        if hasattr(team, key):
            setattr(team, key, value)
    
    await db.commit()
    await db.refresh(team)
    
    await flush_teams_cache()
    
    return team


async def delete_team(db: AsyncSession, team_id: int) -> bool:
    result = await db.execute(
        select(TeamModel).where(TeamModel.id == team_id)
    )
    team = result.scalar_one_or_none()
    
    if not team:
        return False
    
    team.active = False
    await db.commit()
    
    await flush_teams_cache()
    
    return True


async def flush_teams_cache() -> None:
    redis = get_redis_client()
    cache_key = CacheKeys.teams()
    await redis.delete(cache_key)
    
    pattern = "team_by_token:*"
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor, match=pattern, count=100)
        if keys:
            await redis.delete(*keys)
        if cursor == 0:
            break