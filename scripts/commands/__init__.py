import click

from .build import build
from .clean import clean
from .pause import pause
from .reset import reset
from .resume import resume
from .scale import scale
from .setup import setup
from .start import start
from .tokens import tokens
from .validate import validate


def register(cli: click.Group):
    cli.add_command(build)
    cli.add_command(clean)
    cli.add_command(pause)
    cli.add_command(reset)
    cli.add_command(resume)
    cli.add_command(scale)
    cli.add_command(setup)
    cli.add_command(start)
    cli.add_command(tokens)
    cli.add_command(validate)


__all__ = ('register',)