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
    for oc in metadata['outcodes']:
        outcodes.add(oc['outcode'], oc['incode_count'])

    metadata['outcodes'] = outcodes

    loc_len = len(metadata['locations'])
    print(f"{loc_len} locations, requiring an index size of {loc_len.bit_length()} bits")

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


def read_binary_file():

    with open("test.bin", 'rb') as f:
        metadata = read_metadata(f)
        outcodes = metadata['outcodes']
        locations = metadata['locations']

        index = -1
        while bytes := bytearray(f.read(INCODE_BLOCK_SIZE)):
            index = index+1
            ctr = IntContainer(int.from_bytes(bytes, ENDIAN))

            incode, loc_ix, lat, lon = ctr.parts(16, 9, 9)
            incode = decode_incode(incode)
            loc = locations[loc_ix.value]

            outcode = outcodes.find_outcode(index)
            print(f"{outcode.outcode} {incode}, {loc_ix}, {lat}, {lon}")



def seek_incode(f, start, end):
    pos = INCODE_BLOCK_SIZE * int((end - start) / (2 * INCODE_BLOCK_SIZE))
    if pos == 0:
        return None
    f.seek(start+pos, io.SEEK_SET)
    while start <= f.tell() <= end:
        bytes = f.read(INCODE_BLOCK_SIZE)
        ctr = IntContainer(int.from_bytes(bytes, ENDIAN))
        return start+pos, *ctr.parts(16, 9, 9)

    return None


def find_pc(pc):
    outcode, incode = pc.split(" ", 1)

    with open("test.bin", 'rb') as f:
        metadata = read_metadata(f)
        locations = metadata['locations']
        outcodes = metadata['outcodes']

        start = f.tell()

        oc = outcodes[outcode]
        print(oc)

        start = start + oc.start * INCODE_BLOCK_SIZE
        end = start + oc.incode_count * INCODE_BLOCK_SIZE

        incode = encode_incode(incode).value
        while result := seek_incode(f, start, end):
            if result[1] < incode:
                start = result[0]
            elif result[1] > incode:
                end = result[0]
            else:
                break

    if result is None:
        print("Value not found")
        return

    incode = decode_incode(result[1])
    location = locations[result[2].value]
    lat, lon = result[3:]
    lat = lat.value / 10000 * 4 + location['lat']
    lon = lon.value / 10000 * 4 + location['lon']

    print("Value found", outcode, incode, location, lat, lon)

