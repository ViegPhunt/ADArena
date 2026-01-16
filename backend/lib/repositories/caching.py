import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.models import Team as TeamModel, Task as TaskModel
from lib.repositories.utils import get_redis_client
from lib.repositories.keys import CacheKeys


async def cache_teams(db: AsyncSession) -> None:
    """
    Cache active teams in Redis for fast access.
    
    Creates two cache structures:
    1. Set of team JSON objects (teams key) - for listing all teams
    2. Individual team_by_token:{token} keys - for fast token validation
    
    The token lookup is critical for flag submission performance,
    as every submission requires token validation.
    """
    redis = get_redis_client()
    
    result = await db.execute(
        select(TeamModel).where(TeamModel.active == True)
    )
    teams = result.scalars().all()
    
    teams_key = CacheKeys.teams()
    await redis.delete(teams_key)
    
    if not teams:
        return
    
    cache_ttl = 3600
    
    async with redis.pipeline(transaction=True) as pipe:
        for team in teams:
            team_data = {
                "id": team.id,
                "name": team.name,
                "ip": team.ip,
                "token": team.token,
                "active": team.active,
            }
            team_json = json.dumps(team_data)
            
            # Add to teams set
            pipe.sadd(teams_key, team_json)
            # Create individual token->id mapping for O(1) lookup
            pipe.set(CacheKeys.team_by_token(team.token), team.id, ex=cache_ttl)
        
        pipe.expire(teams_key, cache_ttl)
        
        await pipe.execute()


async def cache_tasks(db: AsyncSession) -> None:
    redis = get_redis_client()
    
    result = await db.execute(
        select(TaskModel).where(TaskModel.active == True)
    )
    tasks = result.scalars().all()
    
    tasks_key = CacheKeys.tasks()
    await redis.delete(tasks_key)
    
    if not tasks:
        return
    
    cache_ttl = 3600
    task_json_list = []
    for task in tasks:
        task_data = {
            "id": task.id,
            "name": task.name,
            "active": task.active,
        }
        task_json_list.append(json.dumps(task_data))
    
    if task_json_list:
        await redis.sadd(tasks_key, *task_json_list)
        await redis.expire(tasks_key, cache_ttl)


async def cache_game_config(db: AsyncSession) -> None:
    from lib.repositories import game
    
    config = await game.get_db_game_config(db)
    
    redis = get_redis_client()
    config_data = {
        "id": config.id,
        "flag_lifetime": config.flag_lifetime,
        "round_time": config.round_time,
        "real_round": config.real_round,
        "game_running": config.game_running,
        "volga_attacks_mode": config.volga_attacks_mode,
        "flag_prefix": config.flag_prefix,
        "max_round": config.max_round,
    }
    
    await redis.set(CacheKeys.game_config(), json.dumps(config_data), ex=60)