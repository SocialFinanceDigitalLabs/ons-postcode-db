import click
from sqlalchemy import create_engine

from .binary_write import write_binary_file
from .binary_read import read_binary_file, find_pc
from .populate_geo import read_file

@click.group()
def cli():
    pass


@cli.command()
@click.argument('filename')
@click.argument('url', )
def database(filename, url):
    engine = create_engine(url)
    read_file(filename, engine)


@cli.command()
@click.argument('filename')
@click.option('--max', type=int, default=None)
def binary(filename, max):
    write_binary_file(filename, max=max)


@cli.command()
def read():
    read_binary_file()


@cli.command()
@click.argument('postcode')
def seek(postcode):
    find_pc(postcode)


cli()
