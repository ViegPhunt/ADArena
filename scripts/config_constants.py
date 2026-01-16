"""Configuration constants and paths for ADArena setup.

Defines base directories and file paths for:
- Docker compose files
- Environment variable files
- Configuration files
"""
from pathlib import Path

ADMIN_USER = 'admin'

BASE_DIR = Path(__file__).absolute().resolve().parents[1]
EXTERNAL_COMPOSE_FILE = 'docker-compose-external.yml'

CONFIG_PATH = BASE_DIR / 'config.yml'
DOCKER_DIR = BASE_DIR / 'docker'
DOCKER_VOLUMES_DIR = BASE_DIR / 'docker_volumes'
FULL_COMPOSE_PATH = BASE_DIR / 'docker-compose.yml'

ADMIN_ENV_PATH = DOCKER_DIR / 'services' / 'admin.env'
POSTGRES_ENV_PATH = DOCKER_DIR / 'postgres_environment.env'
REDIS_ENV_PATH = DOCKER_DIR / 'redis_environment.env'