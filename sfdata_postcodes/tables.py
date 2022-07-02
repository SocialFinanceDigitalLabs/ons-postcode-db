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

postcode = Table(
    'postcode', metadata_obj,
    Column('pcd', String(10), primary_key=True),
    Column('county', String(10)),
    Column('country', String(10)),
    Column('electoral_division', String(10)),
    Column('local_authority_district', String(10)),
    Column('osgrid_east', BigInteger),
    Column('osgrid_north', BigInteger),
    Column('osgrid_quality', SmallInteger),
    Column('urban_rural_classification', String(10)),
    Column('latitude', String(20)),
    Column('longitude', String(20)),
    Column('imd', BigInteger),
)
