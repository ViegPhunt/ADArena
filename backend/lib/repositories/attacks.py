from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from lib.repositories import flags, game, teamtasks
from lib.utils.exceptions import FlagSubmitException, FlagExceptionEnum
from lib.models.types import TaskStatus


async def handle_attack(
    db: AsyncSession,
    attacker_id: int,
    flag_str: str,
    current_round: int,
) -> Dict[str, Any]:
    """
    Process flag submission and calculate score changes.
    
    This is the main flag attack handler that:
    1. Validates flag (lifetime, ownership, duplicates)
    2. Checks Volga mode restrictions (can only attack if your service is UP)
    3. Calls stored procedure to calculate scores and insert StolenFlag record
    4. Returns score deltas for both attacker and victim
    
    Args:
        db: Database session
        attacker_id: ID of team submitting the flag
        flag_str: Flag string to validate
        current_round: Current game round number
    
    Returns:
        Dictionary with submit_ok status, message, and score deltas
    """
    result = {
        "submit_ok": False,
        "message": "",
        "attacker_id": attacker_id,
        "victim_id": None,
        "task_id": None,
        "attacker_delta": 0.0,
        "victim_delta": 0.0,
    }
    
    try:
        if current_round == -1:
            raise FlagExceptionEnum.GAME_NOT_AVAILABLE

        game_config = await game.get_current_game_config(db)

        max_round = game_config.max_round
        if max_round and current_round > max_round:
            raise FlagExceptionEnum.GAME_FINISHED

        # Look up flag from cache (populated by checker's put_action)
        flag_data = await flags.get_flag_by_str(flag_str)
        if not flag_data:
            raise FlagExceptionEnum.FLAG_INVALID

        flag_id = flag_data["id"]
        flag_team_id = flag_data["team_id"]
        flag_task_id = flag_data["task_id"]
        flag_round = flag_data["round"]

        if flag_team_id == attacker_id:
            raise FlagExceptionEnum.FLAG_YOUR_OWN

        # Check if flag expired based on configured lifetime (rounds)
        flag_lifetime = game_config.flag_lifetime
        if current_round - flag_round > flag_lifetime:
            raise FlagExceptionEnum.FLAG_TOO_OLD

        # Volga mode: Can only submit flags if your own service is UP
        # This prevents teams from scoring when their service is down
        volga_mode = game_config.volga_attacks_mode
        if volga_mode:
            team_task = await teamtasks.get_teamtask(db, attacker_id, flag_task_id)
            if not team_task or team_task.status != TaskStatus.UP.value:
                raise FlagExceptionEnum.SERVICE_IS_DOWN

        from sqlalchemy import select, func
        from lib.models import StolenFlag

        # Check for duplicate submission (same flag, same attacker)
        check_result = await db.execute(
            select(func.count(StolenFlag.id))
            .where(StolenFlag.flag_id == flag_id)
            .where(StolenFlag.attacker_id == attacker_id)
        )
        already_stolen = check_result.scalar() > 0

        if already_stolen:
            raise FlagExceptionEnum.FLAG_ALREADY_STOLEN

        from sqlalchemy import text

        # Call PostgreSQL stored procedure to:
        # 1. Calculate dynamic score based on team rankings and service health
        # 2. Update TeamTask scores (attacker +, victim -)
        # 3. Update stolen/lost counters
        # 4. Insert StolenFlag record
        # All done atomically in database for consistency
        sql = text("""
            SELECT attacker_delta, victim_delta 
            FROM recalculate_rating(:attacker_id, :victim_id, :task_id, :flag_id)
        """)

        score_result = await db.execute(
            sql,
            {
                "attacker_id": attacker_id,
                "victim_id": flag_team_id,
                "task_id": flag_task_id,
                "flag_id": flag_id,
            }
        )

        row = score_result.fetchone()
        if not row:
            raise Exception("Stored procedure returned no result")

        attacker_delta = float(row[0])
        victim_delta = float(row[1])

        await db.commit()

        result["submit_ok"] = True
        result["victim_id"] = flag_team_id
        result["task_id"] = flag_task_id
        result["attacker_delta"] = attacker_delta
        result["victim_delta"] = victim_delta
        result["message"] = f"Flag accepted! Earned {attacker_delta:.2f} flag points!"

    except FlagSubmitException as e:
        result["submit_ok"] = False
        result["message"] = str(e)
        await db.rollback()
    except Exception as e:
        result["submit_ok"] = False
        result["message"] = f"Internal error: {str(e)}"
        await db.rollback()

    return result