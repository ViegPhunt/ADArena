from types import SimpleNamespace
from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
import json

from lib.models import GameConfig as GameConfigModel
from lib.repositories.utils import get_redis_client
from lib.repositories.keys import CacheKeys


async def get_game_running(db: AsyncSession) -> bool:
    result = await db.execute(
        select(GameConfigModel.game_running).where(GameConfigModel.id == 1)
    )
    return result.scalar_one()


async def set_game_running(db: AsyncSession, running: bool) -> None:
    await db.execute(
        sql_update(GameConfigModel)
        .where(GameConfigModel.id == 1)
        .values(game_running=running)
    )
    await db.commit()


async def get_db_game_config(db: AsyncSession) -> GameConfigModel:
    result = await db.execute(
        select(GameConfigModel).where(GameConfigModel.id == 1)
    )
    return result.scalar_one()


async def get_current_game_config(db: AsyncSession) -> GameConfigModel:
    """
    Get game configuration with Redis caching.
    
    Returns SimpleNamespace from cache (lightweight) or full GameConfigModel
    from database. Both have same attribute access (config.round_time, etc).
    
    Cache TTL is short (60s) to ensure config changes propagate quickly.
    """
    redis = get_redis_client()
    cache_key = CacheKeys.game_config()
    
    cached = await redis.get(cache_key)
    if cached:
        config_data = json.loads(cached)
        # Return SimpleNamespace for attribute access without SQLAlchemy overhead
        return SimpleNamespace(**config_data)
    
    config = await get_db_game_config(db)
    
    config_dict = {
        "id": config.id,
        "game_running": config.game_running,
        "game_hardness": config.game_hardness,
        "max_round": config.max_round,
        "round_time": config.round_time,
        "real_round": config.real_round,
        "flag_prefix": config.flag_prefix,
        "flag_lifetime": config.flag_lifetime,
        "inflation": config.inflation,
        "volga_attacks_mode": config.volga_attacks_mode,
        "timezone": config.timezone,
        "start_time": config.start_time.isoformat() if config.start_time else None,
    }
    await redis.set(cache_key, json.dumps(config_dict), ex=60)
    
    return config


async def flush_game_config_cache() -> None:
    redis = get_redis_client()
    await redis.delete(CacheKeys.game_config())