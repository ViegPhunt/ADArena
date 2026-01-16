"""Resume game by setting game_running=True in database."""
import sys
import click

from scripts.config_utils import run_command, print_status
from scripts import config_constants


@click.command(help='Resume game after pause')
def resume():
    """Set game_running=True in database to resume the game.
    
    Ticker will continue advancing rounds.
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
        '        await game.set_game_running(db, True); '
        'asyncio.run(f())'
    ]
    
    try:
        run_command(command, cwd=config_constants.BASE_DIR, quiet=True)
        print_status('SUCCESS', 'Game resumed!')
    except SystemExit:
        print_status('ERROR', 'Failed to resume game.')
        sys.exit(1)