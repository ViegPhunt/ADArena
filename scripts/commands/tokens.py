"""Print team authentication tokens."""
import click

from scripts.config_utils import run_command
from scripts.config_constants import FULL_COMPOSE_PATH, BASE_DIR


@click.command('tokens', help='Print team tokens')
def tokens():
    """Execute print_tokens.py script inside ticker container."""
    command = [
        'docker', 'compose',
        '-f', FULL_COMPOSE_PATH,
        'exec', '-T', 'ticker',
        'python3', '/app/scripts/print_tokens.py',
    ]
    run_command(command, cwd=BASE_DIR)