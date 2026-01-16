"""Reset game and remove all data volumes."""
import click

from scripts import config_constants, config_utils


@click.command(help='Reset the game & wipes all data volumes')
def reset():
    """Stop all containers and remove volumes to reset the game state."""
    command = [
        'docker', 'compose', '-f',
        config_constants.FULL_COMPOSE_PATH,
        'down', '-v', '--remove-orphans',
    ]
    config_utils.run_command(command, cwd=config_constants.BASE_DIR)
    config_utils.print_status('SUCCESS', 'Reset complete!')