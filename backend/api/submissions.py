import logging
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.models import get_db_session, Team
from lib.repositories.utils import close_redis, get_redis_client
from lib.models import close_db
from lib.repositories import attacks, game_state
from lib.utils.notifier import get_notifier



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== Lifespan Events ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting HTTP Receiver service...")
    try:
        redis = get_redis_client()
        await redis.ping()
        logger.info("HTTP Receiver service started successfully")
    except Exception as e:
        logger.error(f"Failed to start HTTP Receiver: {e}")
        raise
    
    yield
    
    logger.info("Shutting down HTTP Receiver service...")
    try:
        await close_redis()
        await close_db()
        logger.info("HTTP Receiver service shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title="ADArena HTTP Receiver",
    description="Flag submission endpoint with async processing",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/api/http-receiver/metrics")


# ==================== Models ====================

class FlagSubmissionRequest(BaseModel):
    flags: List[str]


class FlagSubmissionResponse(BaseModel):
    msg: str
    flag: str


# ==================== Helper Functions ====================

async def get_team_by_token(token: str, db: AsyncSession) -> Optional[Team]:
    result = await db.execute(
        select(Team).where(Team.token == token).where(Team.active == True)
    )
    return result.scalar_one_or_none()


async def process_flag_submission(
    team_id: int,
    flag: str,
    db: AsyncSession,
    current_round: int,
) -> dict:
    result = await attacks.handle_attack(
        db=db,
        attacker_id=team_id,
        flag_str=flag,
        current_round=current_round,
    )
    return result

@app.put("/flags/")
async def submit_flags(
    request: Request,
    payload: FlagSubmissionRequest,
    x_team_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session)
) -> List[FlagSubmissionResponse]:
    """Accept flag submissions from teams.
    
    Rate limiting: Max 100 flags per request to prevent abuse.
    Authentication: Via X-Team-Token header (validated against team.token).
    
    Each flag is processed synchronously to ensure proper scoring order
    and prevent race conditions in the stored procedure.
    """
    if not x_team_token:
        raise HTTPException(status_code=400, detail="Missing X-Team-Token header")
    
    team = await get_team_by_token(x_team_token, db)
    if not team:
        logger.debug(f"[{request.client.host}] Invalid token: {x_team_token}")
        raise HTTPException(status_code=400, detail="Invalid team token")
    
    current_round = await game_state.get_real_round()
    if current_round == -1:
        raise HTTPException(status_code=400, detail="Game not started")
    
    flags = payload.flags

    # Rate limit: 1-100 flags per request
    if not flags or len(flags) > 100:
        logger.debug(f"[{request.client.host}] Invalid format: {len(flags) if flags else 0} flags")
        raise HTTPException(
            status_code=400,
            detail="Must provide a list with 1-100 flags"
        )
    
    responses = []
    for flag in flags:
        result = await process_flag_submission(team.id, flag, db, current_round)
        
        logger.info(
            f"[{request.client.host}] team={team.name} flag={flag} "
            f"status={'OK' if result['submit_ok'] else 'BAD'} "
            f"msg={result['message']}"
        )
        
        if result['submit_ok']:
            try:
                from lib.models import Task
                from sqlalchemy import select
                
                victim_result = await db.execute(
                    select(Team).where(Team.id == result['victim_id'])
                )
                victim_team = victim_result.scalar_one_or_none()
                
                task_result = await db.execute(
                    select(Task).where(Task.id == result['task_id'])
                )
                task = task_result.scalar_one_or_none()
                
                if victim_team and task:
                    notifier = get_notifier()
                    await notifier.notify(
                        attacker_id=team.id,
                        attacker_name=team.name,
                        victim_id=victim_team.id,
                        victim_name=victim_team.name,
                        task_id=task.id,
                        task_name=task.name,
                        points=result['attacker_delta'],
                    )
            except Exception as e:
                logger.error(f"Error sending attack notification: {e}")
        
        responses.append(
            FlagSubmissionResponse(
                msg=f"[{flag}] {result['message']}",
                flag=flag
            )
        )
    
    return responses


@app.get("/flags/health/")
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