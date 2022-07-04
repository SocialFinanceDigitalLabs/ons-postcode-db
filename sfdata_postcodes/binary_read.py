import bz2
import io
import json
from dataclasses import dataclass
from struct import unpack, calcsize

from sfdata_postcodes.binary_geo import ENDIAN
from sfdata_postcodes.encoder import decode_outcode, decode_incode, encode_incode, IntContainer

INCODE_BLOCK_SIZE = 6


def read_metadata(f):
    metadata_length = unpack("I", f.read(calcsize("I")))[0]
    metadata = bz2.decompress(f.read(metadata_length))
    metadata = json.loads(metadata)

    outcodes = OutcodeContainer()
    for oc in metadata['outcodes'].values():
        outcodes.add(oc['outcode'], oc['incode_count'])
    metadata['outcodes'] = outcodes

    metadata['incodes'] = {int(k): v for k, v in metadata['incodes'].items()}
    metadata['locations'] = {int(k): v for k, v in metadata['locations'].items()}
    metadata['country'] = {int(k): v for k, v in metadata['country'].items()}
    metadata['county'] = {int(k): v for k, v in metadata['county'].items()}
    metadata['electoral_division'] = {int(k): v for k, v in metadata['electoral_division'].items()}
    metadata['local_authority_district'] = {int(k): v for k, v in metadata['local_authority_district'].items()}
    metadata['urban_rural_classification'] = {int(k): v for k, v in metadata['urban_rural_classification'].items()}

    return metadata


@dataclass
class Outcode:
    outcode: str
    incode_count: int
    start: int
    end: int


class OutcodeContainer:

    def __init__(self):
        self._outcodes = []
        self._index = {}

    def add(self, outcode, incode_count):
        if self._outcodes:
            start = self._outcodes[-1].end + 1
        else:
            start = 0

        oc = Outcode(outcode, incode_count, start, start + incode_count - 1)
        self._outcodes.append(oc)
        self._index[outcode] = oc

    def find_outcode(self, oc_ix):
        for oc in self._outcodes:
            if oc.start <= oc_ix <= oc.end:
                return oc
        return None

    def __getitem__(self, item):
        return self._index[item]


def read_outcodes(f):
    outcodes_length = int.from_bytes(f.read(2), ENDIAN)
    outcodes = OutcodeContainer()
    for ix in range(outcodes_length):
        outcodes.add(
            decode_outcode(int.from_bytes(f.read(3), ENDIAN)),
            int.from_bytes(f.read(2), ENDIAN),
        )

    return outcodes


def read_binary_file(infile):

    with open(infile, 'rb') as f:
        metadata = read_metadata(f)
        outcodes = metadata['outcodes']
        incodes = metadata['incodes']
        locations = metadata['locations']

        index = -1
        while bytes := bytearray(f.read(INCODE_BLOCK_SIZE)):
            index = index+1
            ctr = IntContainer(int.from_bytes(bytes, ENDIAN))

            incode_ix, loc_ix, lat, lon, urb = ctr.parts(16, 8, 8, 4)

            incode = incodes[str(incode_ix)]
            loc = locations[str(loc_ix.value)]

            outcode = outcodes.find_outcode(index)
            print(f"{outcode.outcode} {incode['code']}, {loc}, {lat}, {lon}")


def seek_incode(f, start, end):
    pos = INCODE_BLOCK_SIZE * int((end - start) / (2 * INCODE_BLOCK_SIZE))
    if pos == 0:
        return None
    f.seek(start+pos, io.SEEK_SET)
    while start <= f.tell() <= end:
        bytes = f.read(INCODE_BLOCK_SIZE)
        ctr = IntContainer(int.from_bytes(bytes, ENDIAN))
        return start+pos, *ctr.parts(16, 8, 8, 4)

    return None


def find_pc(infile, outcode, incode):

    with open(infile, 'rb') as f:
        metadata = read_metadata(f)
        locations = metadata['locations']
        outcodes = metadata['outcodes']
        incodes = metadata['incodes']
        incodes_rev = {ic['code']: k for k, ic in incodes.items()}

        start = f.tell()

        oc = outcodes[outcode]

        start = start + oc.start * INCODE_BLOCK_SIZE
        end = start + oc.incode_count * INCODE_BLOCK_SIZE

        incode_ix = incodes_rev[incode]
        while result := seek_incode(f, start, end):
            if result[1] < incode_ix:
                start = result[0]
            elif result[1] > incode_ix:
                end = result[0]
            else:
                break

    if result is None:
        print("Value not found")
        return

    incode = incodes[result[1]]
    location = locations[result[2].value]

    lat, lon = result[3:5]
    lat = lat.value * location['lat_scale'] / 255 + location['lat']
    lon = lon.value * location['lon_scale'] / 255 + location['lon']

    urban_rural = location['urban_rural'][result[5].value]

    print("Found postcode: ", outcode, incode['code'])

    ctry = metadata['country']
    cty = metadata['county']
    ed = metadata['electoral_division']
    lad = metadata['local_authority_district']
    urc = metadata['urban_rural_classification']

    print("  Country: ", ctry[location['country']])
    print("  County: ", cty[location['county']])
    print("  Electoral Division: ", ed[location['electoral_division']])
    print("  LA: ", lad[location['local_authority_district']])
    print("  IMD: ", location['imd'])
    print("  Urban/Rural: ", urc[urban_rural])

    print(f"  GEO: {lat:0.5f} {lon:0.5f}")
    print(f"  https://www.google.com/maps/search/{lat:0.5f},{lon:0.5f}/")

    # print("Value found", outcode, incode['code'], location, lat, lon)

