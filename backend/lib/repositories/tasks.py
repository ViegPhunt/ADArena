import json
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.models import Task as TaskModel
from lib.repositories.utils import get_redis_client
from lib.repositories.keys import CacheKeys


async def get_tasks(db: AsyncSession) -> List[TaskModel]:
    result = await db.execute(
        select(TaskModel).where(TaskModel.active)
    )
    return result.scalars().all()


async def get_all_tasks(db: AsyncSession) -> List[TaskModel]:
    result = await db.execute(select(TaskModel))
    return result.scalars().all()


async def get_task_by_id(db: AsyncSession, task_id: int) -> Optional[TaskModel]:
    result = await db.execute(
        select(TaskModel).where(TaskModel.id == task_id)
    )
    return result.scalar_one_or_none()


async def create_task(db: AsyncSession, task_data: dict) -> TaskModel:
    task = TaskModel(**task_data)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    await flush_tasks_cache()
    
    return task


async def update_task(db: AsyncSession, task_id: int, task_data: dict) -> Optional[TaskModel]:
    task = await get_task_by_id(db, task_id)
    if not task:
        return None
    
    for key, value in task_data.items():
        setattr(task, key, value)
    
    await db.commit()
    await db.refresh(task)
    
    await flush_tasks_cache()
    
    return task


async def delete_task(db: AsyncSession, task_id: int) -> bool:
    task = await get_task_by_id(db, task_id)
    if not task:
        return False
    
    task.active = False
    await db.commit()
    
    await flush_tasks_cache()
    
    return True


async def flush_tasks_cache() -> None:
    redis = get_redis_client()
    cache_key = CacheKeys.tasks()
    await redis.delete(cache_key)