import redis.asyncio as aioredis

from lib.config import getters



_redis_client = None


def get_redis_client() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        redis_config = getters.get_redis_config()
        _redis_client = aioredis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            password=redis_config.password if redis_config.password else None,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None