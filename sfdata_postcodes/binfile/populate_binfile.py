import bz2
import json
from dataclasses import asdict
from struct import pack
from zipfile import ZipFile

from tqdm import tqdm

from sfdata_postcodes.data import read_all, read_postcodes, CodeContainer
from sfdata_postcodes.data.bindata import BinarySpec, BinaryField
from sfdata_postcodes.data.spatial import SpatialKey, SpatialContainer
from sfdata_postcodes.encoder import IntContainer
from sfdata_postcodes.util import no_none, PCEncoder

ENDIAN = 'big'

DATA_SPEC = BinarySpec(
    byte_length=6,
    fields=[
        BinaryField(name='incode_key', bit_length=12),
        BinaryField(name='spatial_key', bit_length=16),
        BinaryField(name='latitude', bit_length=8),
        BinaryField(name='longitude', bit_length=8),
        BinaryField(name='urban_rural', bit_length=4),
    ]
)
assert sum([f.bit_length for f in DATA_SPEC.fields]) <= DATA_SPEC.byte_length * 8


def create_binfile(infilename, outfilename, max_postcodes=None):
    with ZipFile(infilename, 'r') as zipfile:
        all_codes = read_all(zipfile)
        postcodes = list(read_postcodes(zipfile, max_postcodes=max_postcodes))

    # Sorted unique values
    all_incodes = sorted(set([p.incode for p in postcodes]))
    all_outcodes = sorted(set([p.outcode for p in postcodes]))

    # Index in- and outcodes
    ic_container = CodeContainer(initial_values=[(c,None) for c in all_incodes])
    oc_container = CodeContainer(initial_values=[(c,None) for c in all_outcodes])

    # Index outcodes
    outcodes = {}
    for pc in tqdm(postcodes, desc='Indexing outcodes'):
        outcodes.setdefault(pc.outcode, []).append(pc)

    # Index locations
    locations = {}
    locations_container = CodeContainer()
    for pc in tqdm(postcodes, desc='Indexing locations'):
        spatial_key = SpatialKey.from_row(pc)
        locations_container.add(spatial_key)
        spatial_container = locations.setdefault(spatial_key, SpatialContainer(spatial_key))
        spatial_container.append(pc)

    # Write binfile
    with open(outfilename, 'wb') as f:
        ctry = all_codes['country']
        cty = all_codes['county']
        ed = all_codes['electoral_division']
        lad = all_codes['local_authority_district']
        urc = all_codes['urban_rural_classification']

        metadata = dict(
            data_spec=asdict(DATA_SPEC),
            outcodes={oc.id: {'outcode': oc.code, 'incode_count': len(outcodes[oc.code])} for oc in oc_container},
            incodes=ic_container,
            locations={
                loc.id: no_none({
                    'country': ctry.get_id(loc.code.country),
                    'county': cty.get_id(loc.code.county),
                    'electoral_division': ed.get_id(loc.code.electoral_division),
                    'local_authority_district': lad.get_id(loc.code.local_authority_district),
                    'imd': loc.code.imd,
                    'lat': locations[loc.code].lat_min,
                    'lon': locations[loc.code].lon_min,
                    'lat_scale': locations[loc.code].lat_scale,
                    'lon_scale': locations[loc.code].lon_scale,
                    'urban_rural': [urc.get_id(c) for c in locations[loc.code].urban_rural]
                }) for loc in locations_container
            },
            **all_codes,
        )
        metadata = json.dumps(metadata, cls=PCEncoder)
        print(f"Full metadata size is {len(metadata)} characters")

        metadata = bz2.compress(bytes(metadata, 'ASCII'))
        print(f"Metadata compressed to {len(metadata)} bytes")

        f.write(pack('I', len(metadata)))
        f.write(metadata)

        progress = tqdm(oc_container, desc='Writing postcodes')
        for oc in progress:
            incodes = outcodes[oc.code]
            for ic_row in incodes:
                incode_key = ic_container.get_id(ic_row.incode)
                spatial_key = SpatialKey.from_row(ic_row)
                loc = locations[spatial_key]
                lat = int((ic_row.latitude - loc.lat_min) * 255 / loc.lat_scale) \
                    if ic_row.latitude and loc.lat_min and loc.lat_scale else 0
                lon = int((ic_row.longitude - loc.lon_min) * 255 / loc.lon_scale) \
                    if ic_row.longitude and loc.lon_min and loc.lon_scale else 0

                urban_rural = loc.urban_rural.index(ic_row.urban_rural_classification)
                value = (
                    IntContainer(0)
                    .push(incode_key, DATA_SPEC['incode_key'].bit_length)
                    .push(locations_container.get_id(spatial_key), DATA_SPEC['spatial_key'].bit_length)
                    .push(lat, DATA_SPEC['latitude'].bit_length)
                    .push(lon, DATA_SPEC['longitude'].bit_length)
                    .push(urban_rural, DATA_SPEC['urban_rural'].bit_length)
                )

                f.write(value.to_bytes(DATA_SPEC.byte_length, ENDIAN))

