import json
from typing import Optional, List, Dict
from collections import defaultdict
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from lib.models import Flag as FlagModel, Task as TaskModel
from lib.repositories.utils import get_redis_client
from lib.repositories.keys import CacheKeys


async def cache_flag(flag_id: int, team_id: int, task_id: int, flag_str: str, round_num: int, public_flag_data: Optional[str], flag_lifetime: int, round_time: int) -> None:
    """
    Cache flag data in Redis for fast lookup during flag submissions.
    
    TTL is set to 2x the maximum flag validity period to handle edge cases.
    This prevents memory bloat while ensuring all valid flags are cached.
    
    Args:
        flag_lifetime: Number of rounds a flag remains valid
        round_time: Duration of each round in seconds
    """
    redis = get_redis_client()
    # Set TTL to double the max validity period (lifetime * round_time)
    cache_ttl = flag_lifetime * round_time * 2
    
    flag_data = {
        "id": flag_id,
        "team_id": team_id,
        "task_id": task_id,
        "flag": flag_str,
        "round": round_num,
        "public_flag_data": public_flag_data,
    }
    
    flag_json = json.dumps(flag_data)
    await redis.set(CacheKeys.flag_by_str(flag_str), flag_json, ex=cache_ttl)


async def get_flag_by_str(flag_str: str) -> Optional[Dict]:
    redis = get_redis_client()
    cache_key = CacheKeys.flag_by_str(flag_str)
    
    cached = await redis.get(cache_key)
    if cached:
        flag_data = json.loads(cached)
        return flag_data
    
    return None


async def get_random_round_flag(
    db: AsyncSession,
    team_id: int,
    task_id: int,
    from_round: int = None,
    current_round: int = None,
    round_num: int = None,
) -> Optional[FlagModel]:
    """Get a random flag for a team/task from a range of rounds.
    
    Can be called with either:
    - from_round + current_round: selects random flag from rounds [from_round, current_round]
    - round_num: selects random flag from specific round (legacy)
    """
    query = select(FlagModel).where(
        and_(
            FlagModel.team_id == team_id,
            FlagModel.task_id == task_id,
        )
    )
    
    # Add round filtering
    if from_round is not None and current_round is not None:
        # Range query: from_round to current_round
        query = query.where(
            and_(
                FlagModel.round >= from_round,
                FlagModel.round <= current_round,
            )
        )
    elif round_num is not None:
        # Single round query (legacy)
        query = query.where(FlagModel.round == round_num)
    else:
        # No round filter - should not happen, but handle gracefully
        pass
    
    query = query.order_by(func.random()).limit(1)
    result = await db.execute(query)
    
    return result.scalar_one_or_none()


async def get_attack_data(
    db: AsyncSession,
    current_round: int,
    flag_lifetime: int,
) -> Dict[str, Dict[str, List[str]]]:
    """
    Build attack data structure for participants to download.
    
    Returns a nested dict: team_name -> task_name -> [list of public flag data]
    This gives teams the information needed to attack other teams' services.
    Only includes flags from recent rounds (within flag_lifetime).
    
    Example return:
    {
        "Team1": {"web": ["place1", "place2"], "pwn": ["place1"]},
        "Team2": {"web": ["place1"], "pwn": ["place1", "place2"]}
    }
    """
    from lib.models import Team as TeamModel
    
    tasks_result = await db.execute(
        select(TaskModel).where(TaskModel.active == True)
    )
    tasks = tasks_result.scalars().all()
    
    if not tasks:
        return {}
    
    task_ids = [task.id for task in tasks]
    task_names = {task.id: task.name for task in tasks}
    
    min_round = current_round - flag_lifetime
    flags_result = await db.execute(
        select(
            TeamModel.ip,
            FlagModel.task_id,
            FlagModel.public_flag_data,
        )
        .join(TeamModel, FlagModel.team_id == TeamModel.id)
        .where(
            and_(
                FlagModel.round >= min_round,
                FlagModel.task_id.in_(task_ids),
            )
        )
    )
    flags = flags_result.all()
    
    data: Dict[str, Dict[str, List[str]]] = {
        task_names[task_id]: defaultdict(list) for task_id in task_ids
    }
    
    for ip, task_id, flag_data in flags:
        if flag_data:
            data[task_names[task_id]][ip].append(flag_data)
    
    return data