"""Pydantic models for ADArena configuration validation.

Defines data models for:
- Admin credentials
- Storage backends (Database, Redis)
- Game settings and timing
- Tasks and teams configuration
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class AdminConfig(BaseModel):
    username: str
    password: str


class DatabaseConfig(BaseModel):
    user: str
    password: str
    host: str = 'database'
    port: int = 5432
    dbname: str = 'adarena'


class RedisConfig(BaseModel):
    password: str
    host: str = 'cache'
    port: int = 6379
    db: int = 0


class StoragesConfig(BaseModel):
    database: DatabaseConfig
    cache: RedisConfig


class GameConfig(BaseModel):
    max_round: Optional[int] = None
    round_time: int

    flag_prefix: str = 'FLAG'
    flag_lifetime: int

    timezone: str = 'UTC'
    start_time: datetime

    default_score: float = 2500
    game_hardness: float = 10
    inflation: bool = True
    volga_attacks_mode: bool = False

    checkers_path: str = '/checkers/'
    env_path: str = ''


class Task(BaseModel):
    name: str
    checker: str
    checker_timeout: int = 10
    checker_type: str = 'hackerdom'
    gets: int = 1
    puts: int = 1
    places: int = 1
    env_path: Optional[str] = None
    default_score: Optional[float] = None


class Team(BaseModel):
    ip: str
    name: str


class BasicConfig(BaseModel):
    admin: Optional[AdminConfig] = None
    game: GameConfig
    tasks: List[Task]
    teams: List[Team]


class Config(BasicConfig):
    admin: AdminConfig
    storages: StoragesConfig