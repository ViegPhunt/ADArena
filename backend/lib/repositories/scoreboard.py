from typing import Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.models import Team as TeamModel, Task as TaskModel, TeamTask
from lib.repositories.game_state import get_real_round_from_db, get_round_start
from lib.repositories.config import get_current_game_config


async def construct_scoreboard(db: AsyncSession) -> Dict:
    """
    Build complete scoreboard with rankings and statistics.
    
    For each team, calculates:
    - Total score: Sum of all task scores
    - Average SLA: Mean of (checks_passed / checks) across all tasks
    - Attack count: Total successful flag captures (stolen)
    - Defense losses: Total flags lost to other teams
    
    Teams are ranked by total score (descending).
    """
    teams_result = await db.execute(
        select(TeamModel).where(TeamModel.active)
    )
    teams = teams_result.scalars().all()
    
    tasks_result = await db.execute(
        select(TaskModel).where(TaskModel.active)
    )
    tasks = tasks_result.scalars().all()
    
    teamtasks_result = await db.execute(select(TeamTask))
    teamtasks = teamtasks_result.scalars().all()
    
    # Build lookup map for O(1) access: (team_id, task_id) -> TeamTask
    teamtask_map = {
        (tt.team_id, tt.task_id): tt
        for tt in teamtasks
    }
    
    team_scores = []
    for team in teams:
        total_score = 0.0
        sla_scores = []
        attack_scores = []
        defense_scores = []
        
        for task in tasks:
            tt = teamtask_map.get((team.id, task.id))
            if tt:
                total_score += tt.score
                
                sla = (tt.checks_passed / tt.checks) if tt.checks > 0 else 0
                sla_scores.append(sla)
                
                attack_scores.append(tt.stolen)
                defense_scores.append(tt.lost)
        
        avg_sla = sum(sla_scores) / len(sla_scores) if sla_scores else 0
        total_attacks = sum(attack_scores)
        total_defense_losses = sum(defense_scores)
        
        team_scores.append({
            "team_id": team.id,
            "team_name": team.name,
            "score": round(total_score, 2),
            "sla": round(avg_sla, 3),
            "attack": total_attacks,
            "defense": total_defense_losses,
        })
    
    team_scores.sort(key=lambda x: x["score"], reverse=True)
    
    for idx, team_data in enumerate(team_scores, start=1):
        team_data["rank"] = idx
    
    # Get current round and round start time
    current_round = await get_real_round_from_db(db)
    round_start = await get_round_start(current_round)
    
    # Get game config
    config = await get_current_game_config(db)
    if hasattr(config, '__dict__'):
        config_dict = {k: v for k, v in config.__dict__.items() if not k.startswith('_')}
    else:
        config_dict = {}
    
    team_tasks_data = [
        {
            "team_id": tt.team_id,
            "task_id": tt.task_id,
            "status": tt.status,
            "stolen": tt.stolen,
            "lost": tt.lost,
            "score": tt.score,
            "checks": tt.checks,
            "checks_passed": tt.checks_passed,
            "message": tt.public_message or "",
        }
        for tt in teamtasks
    ]
    
    return {
        "state": {
            "round": current_round,
            "round_start": round_start,
            "team_tasks": team_tasks_data,
        },
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "ip": t.ip,
                "active": t.active
            } for t in teams],
        "tasks": [
            {
                "id": t.id,
                "name": t.name
            } for t in tasks],
        "config": config_dict,
    }