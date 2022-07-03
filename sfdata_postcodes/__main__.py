import click
from sqlalchemy import create_engine

from .binary_write import write_binary_file
from .binary_read import read_binary_file, find_pc
from sfdata_postcodes.rdb.populate_rdb import read_file


@click.group()
def cli():
    pass


@cli.command()
@click.argument('filename')
@click.argument('url', )
@click.option('--max', type=int, default=None)
def database(filename, url, max):
    engine = create_engine(url)
    read_file(filename, engine, max_postcodes=max)


@cli.command()
@click.argument('filename')
@click.option('--max', type=int, default=None)
def binary(filename, max):
    write_binary_file(filename, max_postcodes=max)


@cli.command()
def read():
    read_binary_file()


@cli.command()
@click.argument('postcode')
def seek(postcode):
    find_pc(postcode)


cli()
