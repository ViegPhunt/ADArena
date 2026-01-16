"""Scale specific services up or down."""
import os
import click

from scripts.config_utils import run_docker, print_status


@click.command(help='Scale services and configure worker settings')
@click.option(
    '-s', '--service',
    type=(str, int),
    metavar='SERVICE INSTANCES',
    help='Service name & instance count. Can be specified multiple times.',
    multiple=True,
    required=True,
)
@click.option(
    '-c', '--checkers',
    type=int,
    metavar='N',
    default=None,
    help='Number of checker threads per worker',
)
@click.option(
    '-j', '--jobs',
    type=int,
    metavar='N',
    default=None,
    help='Max concurrent jobs per worker',
)
def scale(service, checkers, jobs):
    """Scale services and optionally reconfigure checker threads and max jobs."""
    env = os.environ.copy()
    
    if checkers is not None:
        env['CHECKERS'] = str(checkers)
    if jobs is not None:
        env['JOBS'] = str(jobs)
    
    command = ['up', '-d', '--no-recreate']
    services = []
    for name, instances in service:
        command.append('--scale')
        command.append(f'{name}={instances}')
        services.append(name)
    command += services
    
    msg = f'Scaling {", ".join([f"{n}={i}" for n, i in service])}'
    if checkers is not None:
        msg += f', checkers={checkers}'
    if jobs is not None:
        msg += f', jobs={jobs}'
    print_status('SUCCESS', msg)
    
    run_docker(command, env=env)