"""Build Docker images without starting services."""
import click

from scripts.config_utils import run_docker


@click.command(help="Only build the images")
def build():
    """Build all Docker images defined in docker-compose.yml."""
    run_docker(['build'])