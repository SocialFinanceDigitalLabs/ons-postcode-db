import click
from sqlalchemy import create_engine

from sfdata_postcodes.binfile.reader import PostcodeFile
from sfdata_postcodes.rdb.populate_rdb import create_database
from sfdata_postcodes.util import PropContainer


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
    postcodes = PostcodeFile(infile)
    for pc in postcodes:
        pc = PropContainer(pc)
        print(f"{pc} {pc.country.name} {pc.county.name} {pc.electoral_division.name} "
              f"{pc.local_authority_district.name} {pc.imd} {pc.urban_rural.name} {pc.google}")


@cli.command()
@click.argument('outcode')
@click.argument('incode')
@click.option('--infile', '-i', type=click.Path(exists=True), default='postcodes.bin')
def seek(infile, outcode, incode):
    postcodes = PostcodeFile(infile)

    pc = postcodes.exact(f"{outcode} {incode}")

    print("  Country: ", pc.country.name)
    print("  County: ", pc.county.name)
    print("  Electoral Division: ", pc.electoral_division.name)
    print("  LA: ", pc.local_authority_district.name)
    print("  IMD: ", pc.imd)
    print("  Urban/Rural: ", pc.urban_rural.name)

    print(f"  GEO: {pc.latitude:0.5f} {pc.longitude:0.5f}")
    print(f"  {pc.google}")


cli()
