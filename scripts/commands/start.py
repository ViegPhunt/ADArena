import os
import click

from scripts.config_utils import run_docker, print_status


@click.command(help='Start ADArena, building if necessary')
@click.option(
    '-w', '--workers',
    type=int,
    metavar='N',
    default=1,
    help='Number of Arq worker instances',
)
@click.option(
    '-c', '--checkers',
    type=int,
    metavar='N',
    default=1,
    help='Number of checker threads per worker (default: 1)',
)
@click.option(
    '-j', '--jobs',
    type=int,
    metavar='N',
    default=1,
    help='Max concurrent jobs per worker (default: 10)',
)
def start(workers, checkers, jobs):
    env = os.environ.copy()
    
    env['CHECKERS'] = str(checkers)
    env['JOBS'] = str(jobs)
    
    msg = f'Start ADArena with {workers} worker(s), {checkers} checker thread(s), max {jobs} jobs'
    
    print_status('SUCCESS', msg)
    
    # Build base image first
    run_docker(['build', 'base'], env=env)
    run_docker(['up', '-d', '--build', '--scale', f'worker={workers}'], env=env)