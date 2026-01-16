import logging
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.models import get_db_session, Team, Task, GameConfig, TeamTask, close_db
from lib.repositories.utils import get_redis_client, close_redis
from lib.repositories.keys import CacheKeys



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== Lifespan Events ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting API service...")
    try:
        redis = get_redis_client()
        await redis.ping()
        logger.info("API service started successfully")
    except Exception as e:
        logger.error(f"Failed to start API service: {e}")
        raise
    
    yield
    
    logger.info("Shutting down API service...")
    try:
        await close_redis()
        await close_db()
        logger.info("API service shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title="ADArena API Service",
    description="Modern async API for Attack-Defense CTF",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/api/client/metrics")


# ==================== Async Endpoints ====================

@app.get("/api/client/teams/")
async def get_teams(db: AsyncSession = Depends(get_db_session)):
    try:
        result = await db.execute(
            select(Team).where(Team.active == True)
        )
        teams = result.scalars().all()
        
        if not teams:
            return []
        
        return [
            {
                "id": team.id,
                "name": team.name,
                "ip": team.ip,
            }
            for team in teams
        ]
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        raise


@app.get("/api/client/tasks/")
async def get_tasks(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(
        select(Task).where(Task.active == True)
    )
    tasks = result.scalars().all()
    
    return [
        {
            "id": task.id,
            "name": task.name,
            "checker": task.checker,
            "gets": task.gets,
            "puts": task.puts,
            "default_score": task.default_score,
        }
        for task in tasks
    ]


@app.get("/api/client/config/")
async def get_game_config(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(GameConfig).where(GameConfig.id == 1))
    config = result.scalar_one_or_none()
    
    if not config:
        return JSONResponse(status_code=404, content={"error": "Config not found"})
    
    return {
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


@app.get("/api/client/attack_data/")
async def serve_attack_data():
    try:
        redis = get_redis_client()
        attack_data = await redis.get(CacheKeys.attack_data())

        if not attack_data:
            return {}

        try:
            parsed = json.loads(attack_data)
        except Exception:
            parsed = {}

        return parsed
    except Exception as e:
        logger.error(f"Error serving attack data: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": "Service temporarily unavailable"}
        )


@app.get("/api/client/teams/{team_id}/")
async def get_team_history(team_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(
        select(TeamTask)
        .where(TeamTask.team_id == team_id)
        .where(TeamTask.status >= 0)
    )
    team_tasks = result.scalars().all()
    
    return [
        {
            "team_id": tt.team_id,
            "task_id": tt.task_id,
            "status": tt.status,
            "stolen": tt.stolen,
            "lost": tt.lost,
            "score": tt.score,
            "checks": tt.checks,
            "checks_passed": tt.checks_passed,
            "public_message": tt.public_message,
        }
        for tt in team_tasks
    ]


@app.get("/api/client/health/")
async def health_check():
    return {"status": "ok"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info",
        access_log=True,
    )