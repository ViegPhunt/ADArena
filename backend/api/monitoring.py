from fastapi import APIRouter, HTTPException

from workers.round_monitor import get_monitor

router = APIRouter(prefix="/api/admin/monitor", tags=["monitoring"])


@router.get("/health")
async def get_health():
    monitor = await get_monitor()
    return await monitor.get_global_health()


@router.get("/round/{round_num}")
async def get_round_status(round_num: int):
    monitor = await get_monitor()
    return await monitor.get_round_completion_status(round_num)


@router.get("/round/{round_num}/team/{team_id}/task/{task_id}")
async def get_team_task_status(round_num: int, team_id: int, task_id: int):
    monitor = await get_monitor()
    return await monitor.get_team_task_status(team_id, task_id, round_num)


@router.get("/current")
async def get_current_round_status():
    monitor = await get_monitor()
    health = await monitor.get_global_health()
    current_round = health['current_round']
    
    if current_round == 0:
        raise HTTPException(status_code=404, detail="Game not started yet")
    
    return await monitor.get_round_completion_status(current_round)


def register_monitoring_routes(app):
    app.include_router(router)