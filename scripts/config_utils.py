"""Utility functions for ADArena configuration management.

Provides functions for:
- Loading and validating config.yml
- Generating environment files
- Running docker-compose commands
- Parsing configuration values
"""
import sys
import time
import yaml
import click
import shutil
import secrets
import subprocess
from typing import List, Optional, Tuple
from pathlib import Path
from pydantic import ValidationError

from . import config_constants, config_models


def print_status(type: str, message: str):
    """Print colored status message to stderr."""
    colors = {
        'SUCCESS': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'INFO': None
    }
    click.secho(message, fg=colors.get(type), err=True)


def load_config(basic: bool = False):
    """Load and validate configuration from config.yml.
    
    Args:
        basic: If True, load BasicConfig (without storages). If False, load full Config.
    
    Returns:
        Validated config model instance.
    """
    path = config_constants.CONFIG_PATH
    ModelConfig = config_models.BasicConfig if basic else config_models.Config

    try:
        yml = yaml.safe_load(path.read_text(encoding='utf-8'))
        return ModelConfig.model_validate(yml, strict=True)
    except FileNotFoundError:
        print_status('ERROR', f'Config file missing at {path}')
    except (ValidationError, yaml.YAMLError) as e:
        print_status('ERROR', f'Invalid configuration file: {e}')

    sys.exit(1)


def backup_config():
    """Create timestamped backup of config.yml."""
    backup_path = config_constants.BASE_DIR / f'config_backup_{int(time.time())}.yml'
    print_status('INFO', f'Creating config backup at {backup_path}')
    shutil.copy2(config_constants.CONFIG_PATH, backup_path)


def dump_config(config: config_models.Config):
    """Write config to config.yml file."""
    print_status('INFO', f'Writing new configuration to {config_constants.CONFIG_PATH}')
    with config_constants.CONFIG_PATH.open(mode='w') as f:
        yaml.safe_dump(config.model_dump(by_alias=True, exclude_none=True), f)


def override_config(
    config: config_models.Config, *,
    database: Optional[str] = None,
    redis: Optional[str] = None
):
    """Override storage backend addresses with external hosts."""
    overrides = [
        (config.storages.db, database, 5432),
        (config.storages.redis, redis, 6379),
    ]

    for storage_conf, value, default_port in overrides:
        if value:
            storage_conf.host, storage_conf.port = parse_host_port(value, default_port)


def build_full_config(config: config_models.BasicConfig) -> config_models.Config:
    """Generate full config with storages from basic config.
    
    Creates admin credentials if not provided and generates storage configs.
    """
    if not config.admin:
        new_username = config_constants.ADMIN_USER
        new_password = secrets.token_hex(10)
        config.admin = config_models.AdminConfig(
            username=new_username,
            password=new_password,
        )
        print_status('INFO', f'Created new admin credentials: {new_username}:{new_password}')

    username = config.admin.username
    password = config.admin.password

    storages = config_models.StoragesConfig(
        db=config_models.DatabaseConfig(user=username, password=password),
        redis=config_models.RedisConfig(password=password),
    )

    return config_models.Config(
        admin=config.admin,
        game=config.game,
        storages=storages,
        tasks=config.tasks,
        teams=config.teams,
    )


def parse_host_port(value: str, default_port: int) -> Tuple[str, int]:
    """Parse host:port string, using default port if not specified."""
    if ':' in value:
        host, port = value.split(':', 1)
        port = int(port)
        return host, port
    return value, default_port


def run_command(command: list[str], cwd=None, env=None, 
        quiet: bool = False, ignore_errors: bool = False):
    """Run shell command with error handling."""
    if not quiet:
        print_status('INFO', f'Running: {command}')
    stdout_dest = subprocess.DEVNULL if quiet else None
    
    try:
        subprocess.run(command, cwd=cwd, env=env, stdout=stdout_dest, check=True)
    except subprocess.CalledProcessError:
        if ignore_errors:
            if not quiet: 
                print_status('WARNING', f'Command failed but ignored: {command}')
        else:
            print_status('ERROR', f'Command failed: {command}')
            sys.exit(1)


def run_docker(args: List[str], env: Optional[dict] = None):
    """Run docker-compose command with ADArena compose file."""
    base = ['docker', 'compose', '-f', 'docker-compose.yml']
    run_command(base + args, cwd=config_constants.BASE_DIR, env=env)


def force_delete(path: Path):
    """Recursively delete file or directory."""
    if not path.exists(): return

    print_status('INFO', f'Deleting: {path}')
    try:
        shutil.rmtree(path) if path.is_dir() else path.unlink()
    except OSError as e:
        print_status('ERROR', f'Failed to delete {path}: {e}')