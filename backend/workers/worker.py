"""Arq worker process for executing CHECK/PUT/GET actions.

Processes jobs from Redis queue submitted by job_submitter.
"""

import logging
import os
from arq import create_pool, run_worker
from arq.connections import RedisSettings

from lib import config
from workers.actions import (
    put_action,
    check_action,
    get_action,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



async def startup(ctx: dict):
    """Initialize worker resources on startup.
    
    Creates Redis connection pool for worker context.
    """
    logger.info("Starting Arq worker...")
    
    redis_config = config.get_redis_config()
    ctx['redis'] = await create_pool(
        RedisSettings(
            host=redis_config.host,
            port=redis_config.port,
            password=redis_config.password,
        )
    )
    
    logger.info("Arq worker started successfully")


async def shutdown(ctx: dict):
    """Cleanup worker resources on shutdown."""
    logger.info("Shutting down Arq worker...")
    
    if 'redis' in ctx:
        await ctx['redis'].close()
    
    logger.info("Arq worker shut down successfully")



class WorkerSettings:
    """Arq worker configuration.
    
    Reads from environment variables:
    - JOBS: Max concurrent jobs per worker
    """
    
    functions = [
        put_action,
        check_action,
        get_action,
    ]
    
    redis_settings = RedisSettings(
        host=config.get_redis_config().host,
        port=config.get_redis_config().port,
        password=config.get_redis_config().password,
    )
    
    max_jobs = int(os.getenv('JOBS'))
    job_timeout = 300
    keep_result = 3600
    
    on_startup = startup
    on_shutdown = shutdown
    
    health_check_interval = 60


if __name__ == '__main__':
    run_worker(WorkerSettings)