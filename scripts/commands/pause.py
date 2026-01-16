"""Pause game by setting game_running=False in database."""
import sys
import click

from scripts.config_utils import run_command, print_status
from scripts import config_constants


@click.command(help='Pause game (stops round progression and flag submission)')
def pause():
    """Set game_running=False in database to pause the game.
    
    Ticker will stop advancing rounds, effectively pausing the game.
    """
    command = [
        'docker', 'compose', '-f', config_constants.FULL_COMPOSE_PATH,
        'exec', '-T', 'ticker',
        'python3', '-c',
        'import asyncio; '
        'from lib.models import get_session_factory; '
        'from lib.repositories import game; '
        'async def f(): '
        '    async with get_session_factory()() as db: '
        '        await game.set_game_running(db, False); '
        'asyncio.run(f())'
    ]
    
    try:
        run_command(command, cwd=config_constants.BASE_DIR, quiet=True)
        print_status('SUCCESS', 'Game paused!')
    except SystemExit:
        print_status('ERROR', 'Failed to pause game.')
        sys.exit(1)