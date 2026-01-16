from typing import Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, case as sql_case
from sqlalchemy.ext.asyncio import AsyncSession

from lib.models import TeamTask, TeamTaskLog


def compute_overall_status(check_status: int, put_status: int, get_status: int) -> Tuple[int, str]:
    # CHECK failed or error
    if check_status == 110:
        return 110, "Service check failed"
    elif check_status == 104:
        return 104, "Service is down"
    
    # CHECK not yet run
    if check_status == -1:
        return -1, "Not checked yet"
    
    # CHECK passed (101), check other actions
    if put_status == 110:
        return 102, "Service corrupted (PUT failed)"
    elif put_status == 104:
        return 102, "Service corrupted (PUT unreachable)"
    
    if get_status == 110:
        return 103, "Service mumble (GET failed)"
    elif get_status == 104:
        return 103, "Service mumble (GET unreachable)"
    
    # All passed or not yet run
    return 101, "Service operational"


def get_status_update_expression():
    return sql_case(
        # If CHECK failed or down
        (TeamTask.check_status == 110, 110),
        (TeamTask.check_status == 104, 104),
        # If CHECK not run
        (TeamTask.check_status == -1, -1),
        # CHECK passed, check PUT
        (TeamTask.put_status == 110, 102),
        (TeamTask.put_status == 104, 102),
        # CHECK+PUT passed, check GET
        (TeamTask.get_status == 110, 103),
        (TeamTask.get_status == 104, 103),
        # All OK or not run
        else_=101
    )


def get_message_update_expression():
    return sql_case(
        (TeamTask.check_status == 110, "Service check failed"),
        (TeamTask.check_status == 104, "Service is down"),
        (TeamTask.check_status == -1, "Not checked yet"),
        (TeamTask.put_status == 110, "Service corrupted (PUT failed)"),
        (TeamTask.put_status == 104, "Service corrupted (PUT unreachable)"),
        (TeamTask.get_status == 110, "Service mumble (GET failed)"),
        (TeamTask.get_status == 104, "Service mumble (GET unreachable)"),
        else_="Service operational"
    )


async def get_teamtask(
    db: AsyncSession,
    team_id: int,
    task_id: int
) -> Optional[TeamTask]:
    result = await db.execute(
        select(TeamTask).where(
            TeamTask.team_id == team_id,
            TeamTask.task_id == task_id
        )
    )
    return result.scalar_one_or_none()


async def log_teamtask_to_history(
    db: AsyncSession,
    team_id: int,
    task_id: int,
    current_round: int,
) -> None:
    team_task = await get_teamtask(db, team_id, task_id)
    
    if not team_task:
        return
    
    log_entry = TeamTaskLog(
        round=current_round,
        team_id=team_id,
        task_id=task_id,
        status=team_task.status,
        stolen=team_task.stolen,
        lost=team_task.lost,
        score=team_task.score,
        checks=team_task.checks,
        checks_passed=team_task.checks_passed,
        public_message=team_task.public_message,
        private_message=team_task.private_message,
        command=team_task.command,
        ts=datetime.now(timezone.utc),
    )
    
    db.add(log_entry)
    await db.commit()