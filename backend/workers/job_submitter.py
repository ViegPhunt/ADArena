import logging
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis

from lib.models import Team, Task
from lib.repositories import flags as flag_repo
from lib import config

logger = logging.getLogger(__name__)

_arq_pool: Optional[ArqRedis] = None


async def get_arq_pool() -> ArqRedis:
    global _arq_pool
    if _arq_pool is None:
        redis_config = config.get_redis_config()
        _arq_pool = await create_pool(
            RedisSettings(
                host=redis_config.host,
                port=redis_config.port,
                password=redis_config.password,
            )
        )
        logger.info("Created Arq pool for job submission")
    return _arq_pool


async def close_arq_pool():
    global _arq_pool
    if _arq_pool is not None:
        await _arq_pool.close()
        _arq_pool = None
        logger.info("Closed Arq pool")


async def get_active_teams_and_tasks(db: AsyncSession) -> Tuple[List[Team], List[Task]]:
    teams_result = await db.execute(
        select(Team).where(Team.active == True)
    )
    teams = teams_result.scalars().all()
    
    tasks_result = await db.execute(
        select(Task).where(Task.active == True)
    )
    tasks = tasks_result.scalars().all()
    
    return list(teams), list(tasks)


async def submit_check_job(team_id: int, task_id: int, current_round: int):
    pool = await get_arq_pool()
    job = await pool.enqueue_job(
        'check_action',
        team_id,
        task_id,
        current_round,
    )
    logger.info(f"Submitted CHECK job: team={team_id}, task={task_id}, round={current_round}, job_id={job.job_id}")
    return job.job_id


async def submit_put_job(team_id: int, task_id: int, current_round: int):
    pool = await get_arq_pool()
    job = await pool.enqueue_job(
        'put_action',
        team_id,
        task_id,
        current_round,
    )
    logger.info(f"Submitted PUT job: team={team_id}, task={task_id}, round={current_round}, job_id={job.job_id}")
    return job.job_id


async def submit_get_job(team_id: int, task_id: int, current_round: int, flag_id: int):
    pool = await get_arq_pool()
    job = await pool.enqueue_job(
        'get_action',
        team_id,
        task_id,
        current_round,
        flag_id,
    )
    logger.info(f"Submitted GET job: team={team_id}, task={task_id}, round={current_round}, flag_id={flag_id}, job_id={job.job_id}")
    return job.job_id


async def submit_round_jobs(db: AsyncSession, current_round: int) -> dict:
    teams, tasks = await get_active_teams_and_tasks(db)
    
    logger.info(f"Submitting round {current_round} jobs for {len(teams)} teams and {len(tasks)} tasks")
    
    from lib.repositories.config import get_current_game_config
    game_config = await get_current_game_config(db)
    flag_lifetime = game_config.flag_lifetime
    
    stats = {
        "round": current_round,
        "teams_count": len(teams),
        "tasks_count": len(tasks),
        "check_jobs": 0,
        "put_jobs": 0,
        "get_jobs": 0,
        "errors": 0,
    }
    
    for team in teams:
        for task in tasks:
            try:
                await submit_check_job(team.id, task.id, current_round)
                stats["check_jobs"] += 1
                
                for _ in range(task.puts):
                    await submit_put_job(team.id, task.id, current_round)
                    stats["put_jobs"] += 1
                
                for _ in range(task.gets):
                    from_round = max(1, current_round - flag_lifetime)
                    flag_data = await flag_repo.get_random_round_flag(
                        db=db,
                        team_id=team.id,
                        task_id=task.id,
                        from_round=from_round,
                        current_round=current_round,
                    )
                    
                    if flag_data:
                        await submit_get_job(team.id, task.id, current_round, flag_data['id'])
                        stats["get_jobs"] += 1
                    else:
                        logger.debug(f"No flag found for GET: team={team.id}, task={task.id}")
                        
            except Exception as e:
                logger.error(f"Error submitting jobs for team={team.id}, task={task.id}: {e}")
                stats["errors"] += 1
    
    logger.info(f"Round {current_round} jobs submitted: {stats}")
    return stats


async def submit_initial_checks(db: AsyncSession) -> dict:
    teams, tasks = await get_active_teams_and_tasks(db)
    
    logger.info(f"Submitting initial checks for {len(teams)} teams and {len(tasks)} tasks")
    
    stats = {
        "round": 0,
        "teams_count": len(teams),
        "tasks_count": len(tasks),
        "check_jobs": 0,
        "errors": 0,
    }
    
    for team in teams:
        for task in tasks:
            try:
                await submit_check_job(team.id, task.id, 0)
                stats["check_jobs"] += 1
            except Exception as e:
                logger.error(f"Error submitting initial check for team={team.id}, task={task.id}: {e}")
                stats["errors"] += 1
    
    logger.info(f"Initial checks submitted: {stats}")
    return stats