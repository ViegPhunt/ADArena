from fastapi import FastAPI, HTTPException, Depends, status, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from lib.models import Team, get_db_session
from lib.repositories import teams, tasks, game
from lib.utils.auth import (
    login, logout, check_auth_status, check_admin_auth,
    LoginRequest, LoginResponse
)



app = FastAPI(title="ADArena Admin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# TEAM MODELS
class TeamCreate(BaseModel):
    name: str
    ip: str
    active: bool = True


class TeamUpdate(BaseModel):
    name: str | None = None
    ip: str | None = None
    active: bool | None = None


class TeamResponse(BaseModel):
    id: int
    name: str
    ip: str
    token: str
    active: bool
    
    class Config:
        from_attributes = True


# TASK MODELS
class TaskCreate(BaseModel):
    name: str
    checker: str
    env_path: str
    gets: int = 0
    puts: int = 0
    places: int = 1
    checker_timeout: int = 1
    checker_type: str = "hackerdom"
    default_score: int = 2500
    active: bool = True


class TaskUpdate(BaseModel):
    name: str | None = None
    checker: str | None = None
    env_path: str | None = None
    gets: int | None = None
    puts: int | None = None
    places: int | None = None
    checker_timeout: int | None = None
    checker_type: str | None = None
    default_score: int | None = None
    active: bool | None = None


class TaskResponse(BaseModel):
    id: int
    name: str
    checker: str
    env_path: str
    gets: int
    puts: int
    places: int
    checker_timeout: int
    checker_type: str
    default_score: int
    active: bool
    
    class Config:
        from_attributes = True



# ==================== Authentication Endpoints ====================

@app.post("/api/admin/auth/login", response_model=LoginResponse)
async def admin_login(credentials: LoginRequest, response: Response):
    return await login(credentials, response)


@app.post("/api/admin/auth/logout")
async def admin_logout(response: Response, session: Optional[str] = Cookie(None)):
    return await logout(response, session)


@app.get("/api/admin/auth/status")
async def admin_auth_status(session: Optional[str] = Cookie(None)):
    return await check_auth_status(session)



# ==================== Team Endpoints ====================

@app.get("/api/admin/teams", response_model=List[TeamResponse])
async def list_teams(
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    teams = await teams.get_all_teams(db)
    return teams


@app.get("/api/admin/teams/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    team = await teams.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@app.post("/api/admin/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    token = Team.generate_token()
    team = await teams.create_team(
        db=db,
        team_data={
            "name": team_data.name,
            "ip": team_data.ip,
            "token": token,
            "active": team_data.active,
        }
    )
    return team


@app.put("/api/admin/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_data: TeamUpdate,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    update_data = team_data.model_dump(exclude_unset=True)
    team = await teams.update_team(db, team_id, update_data)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@app.delete("/api/admin/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    success = await teams.delete_team(db, team_id)
    if not success:
        raise HTTPException(status_code=404, detail="Team not found")



# ==================== Task Endpoints ====================

@app.get("/api/admin/tasks", response_model=List[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    tasks_list = await tasks.get_all_tasks(db)
    return tasks_list


@app.get("/api/admin/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    task = await tasks.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/api/admin/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    task = await tasks.create_task(db, task_data.model_dump())
    return task


@app.put("/api/admin/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    update_data = task_data.model_dump(exclude_unset=True)
    task = await tasks.update_task(db, task_id, update_data)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@app.delete("/api/admin/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    deleted = await tasks.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")



# ==================== Game Config Endpoints ====================

@app.get("/api/admin/config")
async def get_config(
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    config = await game.get_db_game_config(db)
    return config.to_dict()


@app.put("/api/admin/config")
async def update_config(
    config_data: dict,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    config = await game.get_db_game_config(db)
    
    for key in ['round_time', 'flag_lifetime', 'max_round', 'volga_attacks_mode']:
        if key in config_data:
            setattr(config, key, config_data[key])
    
    await db.commit()
    await game.flush_game_config_cache()

    return config.to_dict()


@app.post("/api/admin/game/pause")
async def pause_game(
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    await game.set_game_running(db, False)
    return {"status": "paused"}


@app.post("/api/admin/game/resume")
async def resume_game(
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(check_admin_auth)
):
    await game.set_game_running(db, True)
    return {"status": "resumed"}



# ==================== Health Check ====================

@app.get("/api/admin/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)