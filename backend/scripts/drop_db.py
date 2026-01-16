#!/usr/bin/env python3
"""Wipe all database tables and Redis cache.

This script is called by control.py reset before docker compose down.
It drops all tables and flushes Redis to ensure clean reset.
"""
import time
import asyncio
from sqlalchemy import text

from lib.models import get_session_factory
from lib.repositories.utils import get_redis_client



async def wipe_database():
    """Drop all database tables."""
    factory = get_session_factory()
    async with factory() as db:
        drop_queries = [
            "DROP TABLE IF EXISTS schedule_history CASCADE;",
            "DROP TABLE IF EXISTS team_tasks_log CASCADE;",
            "DROP TABLE IF EXISTS team_tasks CASCADE;",
            "DROP TABLE IF EXISTS stolen_flags CASCADE;",
            "DROP TABLE IF EXISTS flags CASCADE;",
            "DROP TABLE IF EXISTS tasks CASCADE;",
            "DROP TABLE IF EXISTS teams CASCADE;",
            "DROP TABLE IF EXISTS game_config CASCADE;",
            "DROP FUNCTION IF EXISTS recalculate_rating(INTEGER, INTEGER, INTEGER, INTEGER);",
            "DROP FUNCTION IF EXISTS get_first_bloods();",
            "DROP FUNCTION IF EXISTS fix_teamtasks();",
        ]
        
        try:
            for query in drop_queries:
                await db.execute(text(query))
            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"[!] Error dropping tables: {e}")
            raise


async def wipe_redis():
    """Flush all Redis data."""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            redis = get_redis_client()
            await redis.flushall()
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[!] Redis flush attempt {attempt + 1} failed: {e}")
                time.sleep(2)
            else:
                print(f"[!] Failed to flush Redis after {max_retries} attempts: {e}")
                raise


async def main():
    """Main entry point."""
    await wipe_database()
    await wipe_redis()


if __name__ == '__main__':
    asyncio.run(main())