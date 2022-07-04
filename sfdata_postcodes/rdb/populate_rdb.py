from dataclasses import asdict
from zipfile import ZipFile

from sfdata_postcodes.data import read_all, CodeContainer, read_postcodes
from sfdata_postcodes.rdb import tables


def create_database(filename, engine, max_postcodes=None):
    tables.metadata_obj.create_all(engine)
    with engine.connect() as conn:

        with ZipFile(filename, 'r') as zipfile:
            all_codes = read_all(zipfile)

            _populate_table(conn, tables.country, all_codes['country'])
            _populate_table(conn, tables.county, all_codes['county'])
            _populate_table(conn, tables.electoral_division, all_codes['electoral_division'])
            _populate_table(conn, tables.local_authority_district, all_codes['local_authority_district'])
            _populate_table(conn, tables.urban_rural_classification, all_codes['urban_rural_classification'])

            _populate_postcodes(zipfile, conn, all_codes, max_postcodes=max_postcodes)


def _populate_table(conn, table, dataset):
    data_list = [asdict(c) for c in dataset]
    conn.execute(table.insert().prefix_with('OR REPLACE'), data_list)


def _populate_postcodes(zipfile, conn, all_codes, max_postcodes=None):
    incodes = CodeContainer()
    outcodes = CodeContainer()
    ctry = all_codes['country']
    cty = all_codes['county']
    ed = all_codes['electoral_division']
    lad = all_codes['local_authority_district']
    urc = all_codes['urban_rural_classification']

    pc_list = []

    postcodes = read_postcodes(zipfile, max_postcodes=max_postcodes)
    for data in postcodes:

        oc = outcodes.add(data.outcode)
        ic = incodes.add(data.incode)

        pc_list.append({
            'outcode': oc.id,
            'incode': ic.id,
            'country': ctry.get_id(data.country),
            'county': cty.get_id(data.county),
            'electoral_division': ed.get_id(data.electoral_division),
            'local_authority_district': lad.get_id(data.local_authority_district),
            'urban_rural_classification': urc.get_id(data.urban_rural_classification),
            'latitude': data.latitude,
            'longitude': data.longitude,
            'osgrid_east': data.osgrid_east,
            'osgrid_north': data.osgrid_north,
            'osgrid_quality': data.osgrid_quality,
            'imd': data.imd,
        })

        if len(pc_list) >= 5000:
            conn.execute(tables.postcode.insert().prefix_with('OR REPLACE'), pc_list)
            pc_list = []

    conn.execute(tables.postcode.insert().prefix_with('OR REPLACE'), pc_list)

    conn.execute(tables.outcode.insert().prefix_with('OR REPLACE'), [asdict(c) for c in outcodes])
    conn.execute(tables.incode.insert().prefix_with('OR REPLACE'), [asdict(c) for c in incodes])
