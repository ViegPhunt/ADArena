#!/usr/bin/env python3
"""Database reset and initialization script.

Resets database schema and initializes game from config.yml:
- Drops and recreates all tables
- Loads game config (rounds, timing, scoring)
- Creates teams and tasks
- Initializes TeamTasks matrix
- Flushes Redis cache
- Generates team tokens

Usage: python reset.py
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime
import yaml
import pytz

from lib.models import (
    get_engine, Base, get_session_factory,
    Team, Task, TeamTask, GameConfig
)
from lib.repositories.utils import get_redis_client



async def load_config():
    """Load game configuration from YAML file.
    
    Reads from CONFIG_PATH environment variable (default: /config.yml).
    """
    config_path = os.getenv('CONFIG_PATH', '/config.yml')
    
    if not Path(config_path).exists():
        raise FileNotFoundError(
            f"Config file not found at {config_path}\n"
            f"Set CONFIG_PATH environment variable to config file location"
        )
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


async def reset_schema():
    """Drop all tables and recreate schema.
    
    WARNING: This deletes all existing data!
    """
    engine = get_engine()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def init_game_config(config: dict, session):
    """Initialize game configuration from config dict.
    
    Creates GameConfig with timing, scoring, and flag settings.
    Handles timezone conversion for start_time.
    """
    game_conf = config.get('game', {})
    tz_name = game_conf.get('timezone', 'UTC')
    tz = pytz.timezone(tz_name)
    
    # Parse start time and localize to configured timezone
    start_time_str = game_conf['start_time']
    if isinstance(start_time_str, str):
        start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        start_time = tz.localize(start_time)
    else:
        start_time = start_time_str
        if start_time.tzinfo is None:
            start_time = tz.localize(start_time)
    
    game_config = GameConfig(
        id=1,
        game_running=False,
        game_hardness=float(game_conf.get('game_hardness', 10)),
        max_round=int(game_conf['max_round']),
        round_time=int(game_conf['round_time']),
        real_round=0,
        flag_prefix=game_conf['flag_prefix'],
        flag_lifetime=int(game_conf['flag_lifetime']),
        inflation=bool(game_conf.get('inflation', True)),
        volga_attacks_mode=bool(game_conf.get('volga_attacks_mode', False)),
        timezone=tz_name,
        start_time=start_time,
    )
    
    session.add(game_config)
    await session.flush()
    
    return game_config


async def init_tasks(config: dict, session) -> list[Task]:
    """Create tasks/services from config.
    
    Each task represents a vulnerable service to attack/defend.
    Returns list of created Task objects.
    """
    tasks_conf = config.get('tasks', [])
    game_conf = config.get('game', {})
    
    if not tasks_conf:
        return []
    
    default_env_path = game_conf.get('env_path', '/checkers/bin/')
    default_score = int(game_conf.get('default_score', 2500))
    checkers_path = game_conf.get('checkers_path', '/checkers/')
    
    tasks = []
    for task_conf in tasks_conf:
        # Build absolute checker path
        checker_path = task_conf['checker']
        if not checker_path.startswith('/'):
            checker_path = os.path.join(checkers_path, checker_path)
        
        task = Task(
            name=task_conf['name'],
            checker=checker_path,
            env_path=task_conf.get('env_path', default_env_path),
            gets=int(task_conf['gets']),
            puts=int(task_conf['puts']),
            places=int(task_conf['places']),
            checker_timeout=int(task_conf['checker_timeout']),
            checker_type=task_conf.get('checker_type', 'hackerdom'),
            default_score=int(task_conf.get('default_score', default_score)),
            active=task_conf.get('active', True),
        )
        session.add(task)
        await session.flush()
        tasks.append(task)
    
    return tasks


async def init_teams(config: dict, session) -> list[Team]:
    """Create teams from config.
    
    Generates unique authentication token for each team.
    Returns list of created Team objects.
    """
    teams_conf = config.get('teams', [])
    
    if not teams_conf:
        return []
    
    teams = []
    for team_conf in teams_conf:
        token = Team.generate_token()
        team = Team(
            name=team_conf['name'],
            ip=team_conf['ip'],
            token=token,
            active=team_conf.get('active', True),
        )
        session.add(team)
        await session.flush()
        teams.append(team)
    
    return teams


async def init_teamtasks(teams: list[Team], tasks: list[Task], session):
    """Create TeamTasks matrix (all team-task combinations).
    
    Initializes status=-1 (not checked) and default scores.
    """
    if not teams or not tasks:
        return
    
    count = 0
    for team in teams:
        for task in tasks:
            team_task = TeamTask(
                team_id=team.id,
                task_id=task.id,
                status=-1,
                score=float(task.default_score),
                stolen=0,
                lost=0,
                checks=0,
                checks_passed=0,
                public_message='',
                private_message='',
                command='',
            )
            session.add(team_task)
            count += 1
    
    await session.flush()


async def flush_redis():
    """Clear all Redis cached data."""
    try:
        redis = get_redis_client()
        await redis.flushall()
    except Exception as e:
        pass  # Redis not critical for reset


async def print_team_tokens(teams: list[Team]):
    """Save team tokens to YAML file and print to stdout.
    
    Tokens are needed for teams to submit flags.
    Saves to team_tokens.yml next to config file.
    """
    if not teams:
        return

    config_path = os.getenv('CONFIG_PATH', '/config.yml')
    tokens_file = Path(config_path).parent / 'team_tokens.yml'

    teams_data = {
        "teams": [
            {
                "name": team.name,
                "ip": team.ip,
                "token": team.token
            }
            for team in teams
        ]
    }

    with open(tokens_file, 'w') as f:
        yaml.dump(teams_data, f, default_flow_style=False, allow_unicode=True)
    print(f"\nFull details saved to: {tokens_file}\n")

    print('\n'.join(f"{team.name}:{team.token}" for team in teams))


async def run():
    """Main reset workflow.
    
    Executes in order:
    1. Load config
    2. Reset database schema
    3. Initialize game, tasks, teams
    4. Create TeamTasks matrix
    5. Flush Redis
    6. Print tokens
    """
    config = await load_config()
    
    await reset_schema()
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            await init_game_config(config, session)
            tasks = await init_tasks(config, session)
            teams = await init_teams(config, session)
            await init_teamtasks(teams, tasks, session)
            await session.commit()
            await print_team_tokens(teams)
        except Exception as e:
            await session.rollback()
            raise
    
    await flush_redis()
    engine = get_engine()
    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(run())