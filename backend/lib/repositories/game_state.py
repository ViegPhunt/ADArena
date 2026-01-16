from typing import Dict
from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
import json
import time

from lib.models import GameConfig as GameConfigModel, TeamTask
from lib.repositories.utils import get_redis_client
from lib.repositories.keys import CacheKeys


async def get_real_round() -> int:
    """Get current round from Redis cache (fast access for high-frequency calls)."""
    redis = get_redis_client()
    round_str = await redis.get(CacheKeys.current_round())
    return int(round_str) if round_str else -1


async def get_real_round_from_db(db: AsyncSession) -> int:
    """Get current round from database (source of truth)."""
    result = await db.execute(
        select(GameConfigModel.real_round).where(GameConfigModel.id == 1)
    )
    round_num = result.scalar_one()
    return round_num


async def update_real_round_in_db(db: AsyncSession, new_round: int) -> None:
    await db.execute(
        sql_update(GameConfigModel)
        .where(GameConfigModel.id == 1)
        .values(real_round=new_round)
    )
    await db.commit()


async def get_round_start(round_num: int) -> int:
    redis = get_redis_client()
    start_str = await redis.get(CacheKeys.round_start(round_num))
    return int(start_str) if start_str else 0


async def set_round_start(round_num: int) -> None:
    redis = get_redis_client()
    await redis.set(CacheKeys.round_start(round_num), int(time.time()))


async def update_round(db: AsyncSession, finished_round: int) -> None:
    """
    Advance to the next round.
    
    Updates both database (source of truth) and Redis cache (fast access).
    Also invalidates game config cache to force reload with new round number.
    """
    new_round = finished_round + 1
    
    # Record when this round started
    await set_round_start(new_round)
    
    # Update database
    await update_real_round_in_db(db, new_round)
    
    # Update cache and invalidate dependent caches
    redis = get_redis_client()
    await redis.set(CacheKeys.current_round(), new_round)
    await redis.delete(CacheKeys.game_config())


async def update_game_state(db: AsyncSession, current_round: int) -> Dict:
    result = await db.execute(select(TeamTask))
    teamtasks = result.scalars().all()
    
    round_start = await get_round_start(current_round)
    
    state = {
        "round": current_round,
        "round_start": round_start,
        "team_tasks": [
            {
                "team_id": tt.team_id,
                "task_id": tt.task_id,
                # Overall status
                "status": tt.status,
                "message": tt.public_message or "",
                # Per-action status (for detailed display)
                "check_status": tt.check_status,
                "check_message": tt.check_message or "",
                "put_status": tt.put_status,
                "put_message": tt.put_message or "",
                "get_status": tt.get_status,
                "get_message": tt.get_message or "",
                # Counters
                "stolen": tt.stolen,
                "lost": tt.lost,
                "score": float(tt.score),
                "checks": tt.checks,
                "checks_passed": tt.checks_passed,
                # SLA percentage
                "sla": round((tt.checks_passed / tt.checks * 100) if tt.checks > 0 else 0, 2),
            }
            for tt in teamtasks
        ],
    }
    
    redis = get_redis_client()
    await redis.set(CacheKeys.game_state(), json.dumps(state))
    
    return state


async def update_attack_data(db: AsyncSession, current_round: int) -> None:
    from lib.repositories import flags
    
    from lib.repositories.config import get_current_game_config
    config = await get_current_game_config(db)
    flag_lifetime = config.flag_lifetime
    
    attack_data = await flags.get_attack_data(db, current_round, flag_lifetime)

    redis = get_redis_client()
    await redis.set(CacheKeys.attack_data(), json.dumps(attack_data))
