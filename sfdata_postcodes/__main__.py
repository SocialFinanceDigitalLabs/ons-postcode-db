import click
from sqlalchemy import create_engine

from .binary_read import read_binary_file, find_pc
from sfdata_postcodes.rdb.populate_rdb import create_database


@click.group()
def cli():
    pass


@cli.command()
@click.argument('filename')
@click.argument('url', )
@click.option('--max', type=int, default=None)
def database(filename, url, max):
    engine = create_engine(url)
    create_database(filename, engine, max_postcodes=max)


@cli.command()
@click.argument('datafile')
@click.option('--output', '-o', type=click.Path(exists=False), default='postcodes.bin')
@click.option('--max', type=int, default=None)
def create_binfile(datafile, output, max):
    from sfdata_postcodes.binfile.populate_binfile import create_binfile
    create_binfile(datafile, output, max_postcodes=max)


@cli.command()
@click.option('--infile', '-i', type=click.Path(exists=True), default='postcodes.bin')
def read(infile):
    read_binary_file(infile)


@cli.command()
@click.argument('outcode')
@click.argument('incode')
@click.option('--infile', '-i', type=click.Path(exists=True), default='postcodes.bin')
def seek(infile, outcode, incode):
    find_pc(infile, outcode, incode)


cli()
