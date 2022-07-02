import csv
from io import TextIOWrapper
from zipfile import ZipFile
import tablib
from tqdm import tqdm
from .tables import metadata_obj, country, county, electoral_division, local_authority_district, \
    urban_rural_classification, postcode
from . import spec


def read_file(filename, engine):
    metadata_obj.create_all(engine)
    with engine.connect() as conn:

        with ZipFile(filename, 'r') as zipfile:
            populate_countries(conn)
            populate_counties(zipfile, conn)
            populate_electoral_division(zipfile, conn)
            populate_la_district(zipfile, conn)
            populate_rural_urban(zipfile, conn)
            populate_postcodes(zipfile, conn)


def populate_countries(conn):
    countries = (
        {'code': 'E92000001', 'name': 'England'},
        {'code': 'W92000004', 'name': 'Wales'},
        {'code': 'S92000003', 'name': 'Scotland'},
        {'code': 'N92000002', 'name': 'Northern Ireland'},
        {'code': 'L93000001', 'name': 'Channel Islands'},
        {'code': 'M83000003', 'name': 'Isle of Man Country'},
    )
    conn.execute(country.insert().prefix_with('OR REPLACE'), countries)


def populate_counties(zipfile, conn):
    with zipfile.open(spec.COUNTY_FILE, 'r') as file:
        counties = tablib.import_set(TextIOWrapper(file))
    counties = [dict(code=c[0], name=c[1]) for c in counties]
    conn.execute(county.insert().prefix_with('OR REPLACE'), counties)


def populate_electoral_division(zipfile, conn):
    with zipfile.open(spec.ELECTORAL_DIVISION, 'r') as file:
        electoral_divisions = tablib.import_set(TextIOWrapper(file))
    electoral_divisions = [dict(code=c[0], name=c[1]) for c in electoral_divisions]

    electoral_divisions += [
        dict(code='E99999999', name='England (pseudo)'),
        dict(code='W99999999', name='Wales (pseudo)'),
        dict(code='S99999999', name='Scotland (pseudo)'),
        dict(code='N99999999', name='Northern Ireland (pseudo)'),
        dict(code='L99999999', name='Channel Islands (pseudo)'),
        dict(code='M99999999', name='Isle of Man (pseudo)'),
    ]
    conn.execute(electoral_division.insert().prefix_with('OR REPLACE'), electoral_divisions)


def populate_la_district(zipfile, conn):
    for filename in [spec.LOCAL_AUTHORITY_U, spec.LOCAL_AUTHORITY_DISTRICTS]:
        with zipfile.open(filename, 'r') as file:
            la_districts = tablib.import_set(TextIOWrapper(file))
        la_districts = [dict(code=c[0], name=c[1]) for c in la_districts]
        conn.execute(local_authority_district.insert().prefix_with('OR REPLACE'), la_districts)


def populate_rural_urban(zipfile, conn):
    with zipfile.open(spec.RURAL_URBAN, 'r') as file:
        classifications = tablib.import_set(TextIOWrapper(file))
    classifications = [dict(code=c[0], name=c[1]) for c in classifications]
    conn.execute(urban_rural_classification.insert().prefix_with('OR REPLACE'), classifications)


def _table_to_dict(conn, table_name):
    return {c['code']: c['id'] for c in conn.execute(f'select code, id from {table_name}')}


def _to_id(value):
    value = value.lower().strip()
    value = value.replace(' ', '')
    return value


class _Wrap:

    def __init__(self, value):
        self.value = value

    def __getitem__(self, item):
        rv = self.value[item]
        if rv is None or rv == '':
            return None
        return rv

def populate_postcodes(zipfile, conn):
    zip_info = zipfile.getinfo(spec.POSTCODE_FILE)
    last_pos = 0
    with zipfile.open(spec.POSTCODE_FILE, 'r') as file:
        pc_list = []
        pc_reader = csv.reader(TextIOWrapper(file))
        next(pc_reader) # skip header

        progress = tqdm(total=zip_info.file_size)

        for row in pc_reader:
            row = _Wrap(row)
            progress.update(file.tell() - last_pos)
            last_pos = file.tell()
            pc_list.append(
                dict(
                    pcd=row[2],
                    county=row[5],
                    electoral_division=row[6],
                    local_authority_district=row[7],

                    osgrid_east=row[11],
                    osgrid_north=row[12],
                    osgrid_quality=row[13],
                    country=row[16],

                    urban_rural_classification=row[40],

                    latitude=row[42],
                    longitude=row[43],

                    imd=row[47],
                )
            )

            if len(pc_list) >= 5000:
                conn.execute(postcode.insert().prefix_with('OR REPLACE'), pc_list)
                pc_list = []

        conn.execute(postcode.insert().prefix_with('OR REPLACE'), pc_list)


