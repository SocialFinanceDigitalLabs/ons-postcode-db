from dataclasses import asdict
from zipfile import ZipFile

from sfdata_postcodes.data import read_all, CodeContainer
from sfdata_postcodes.data.postcode import PostcodeRow
from sfdata_postcodes.rdb import tables

from sfdata_postcodes import spec
from sfdata_postcodes.zipfile import read_csv_with_progress


def read_file(filename, engine, max_postcodes=None):
    tables.metadata_obj.create_all(engine)
    with engine.connect() as conn:

        with ZipFile(filename, 'r') as zipfile:
            all_codes = read_all(zipfile)

            populate_table(conn, tables.country, all_codes['country'])
            populate_table(conn, tables.county, all_codes['county'])
            populate_table(conn, tables.electoral_division, all_codes['electoral_division'])
            populate_table(conn, tables.local_authority_district, all_codes['local_authority_district'])
            populate_table(conn, tables.urban_rural_classification, all_codes['urban_rural_classification'])

            populate_postcodes(zipfile, conn, all_codes, max_postcodes=max_postcodes)


def populate_table(conn, table, dataset):
    data_list = [asdict(c) for c in dataset]
    conn.execute(table.insert().prefix_with('OR REPLACE'), data_list)


def populate_postcodes(zipfile, conn, all_codes, max_postcodes=None):
    incodes = CodeContainer()
    outcodes = CodeContainer()
    ctry = all_codes['country']
    cty = all_codes['county']
    ed = all_codes['electoral_division']
    lad = all_codes['local_authority_district']
    urc = all_codes['urban_rural_classification']

    pc_list = []

    postcodes = read_csv_with_progress(zipfile, spec.POSTCODE_FILE)

    for ix, row in enumerate(postcodes):
        if max_postcodes and ix >= max_postcodes:
            break

        data = PostcodeRow.from_row(row)

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
