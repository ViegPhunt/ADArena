"""Clean up environment configuration files and data volumes."""
import click

from scripts import config_constants, config_utils


@click.command(help='Cleans up environment artifacts and data')
def clean():
    """Remove all generated config files and docker volumes."""
    targets = [
        config_constants.ADMIN_ENV_PATH,
        config_constants.POSTGRES_ENV_PATH,
        config_constants.REDIS_ENV_PATH,
        config_constants.BASE_DIR / config_constants.EXTERNAL_COMPOSE_FILE,
        config_constants.DOCKER_VOLUMES_DIR,
    ]

    for path in targets:
        if path.exists():
            config_utils.force_delete(path)

    config_utils.print_status('SUCCESS', 'Cleanup successful!')