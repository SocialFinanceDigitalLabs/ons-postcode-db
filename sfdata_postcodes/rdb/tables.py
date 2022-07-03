from sqlalchemy import Table, MetaData, Column, Integer, String, DateTime, ForeignKey, Boolean, BigInteger, \
    SmallInteger, Numeric

metadata_obj = MetaData()


def CodeTable(table_name, _metadata_obj, *extra_cols):
    return Table(
        table_name, _metadata_obj,
        Column('id', Integer, primary_key=True),
        Column('code', String(10), nullable=False, unique=True),
        Column('name', String(100), nullable=False),
        *extra_cols
    )


county = CodeTable('county', metadata_obj)

country = CodeTable('country', metadata_obj)

electoral_division = CodeTable('electoral_division', metadata_obj)

local_authority_district = CodeTable('local_authority_district', metadata_obj)

urban_rural_classification = CodeTable(
    'urban_rural_classification', metadata_obj,
    Column('urban', Boolean, default=False),
)

outcode = Table(
    'outcode', metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('code', String(4), unique=True),
)

incode = Table(
    'incode', metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('code', String(3), unique=True),
)

postcode = Table(
    'postcode', metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('outcode', Integer, ForeignKey("outcode.id")),
    Column('incode', Integer, ForeignKey("incode.id")),

    Column('county', Integer, ForeignKey("county.id")),
    Column('country', Integer, ForeignKey("country.id"), nullable=False),
    Column('electoral_division', Integer, ForeignKey("electoral_division.id")),
    Column('local_authority_district', Integer, ForeignKey("local_authority_district.id")),
    Column('osgrid_east', Integer),
    Column('osgrid_north', Integer),
    Column('osgrid_quality', SmallInteger),
    Column('urban_rural_classification', Integer, ForeignKey("urban_rural_classification.id")),
    Column('latitude', Numeric(asdecimal=True)),
    Column('longitude', Numeric(asdecimal=True)),
    Column('imd', Integer),
)
