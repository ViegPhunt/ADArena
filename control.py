#!/usr/bin/env python3

import click

from scripts import commands

@click.group()
def cli():
    pass

commands.register(cli)

if __name__ == '__main__':
    cli()