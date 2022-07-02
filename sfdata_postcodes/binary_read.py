import io
from dataclasses import dataclass

from sfdata_postcodes.binary_geo import ENDIAN
from sfdata_postcodes.encoder import decode_outcode, decode_incode, encode_outcode, encode_incode, IntContainer


def read_locations(f):
    location_length = int.from_bytes(f.read(2), ENDIAN)
    locations = {}
    for ix in range(location_length):
        locations[ix] = {
            "country": _read_string(f),
            "county": _read_string(f),
            "ed":_read_string(f),
            "lad": _read_string(f),
            "lat": int.from_bytes(f.read(3), ENDIAN, signed=True),
            "lon": int.from_bytes(f.read(3), ENDIAN, signed=True),
        }
    return locations


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
        locations = read_locations(f)
        outcodes = read_outcodes(f)

        index = -1
        while bytes := bytearray(f.read(8)):
            index = index+1
            ctr = IntContainer(int.from_bytes(bytes, ENDIAN))
            incode, loc_ix, lat, lon = ctr.parts(11, 16, 16)
            incode = decode_incode(incode)
            # location = locations[loc_ix.value]
            outcode = outcodes.find_outcode(index)

            print(f"{outcode.outcode} {incode}")


def seek_outcode(f, start, end):
    pos = 3 * int((end - start) / 6)
    if pos == start:
        return None
    f.seek(start+pos, io.SEEK_SET)
    while start <= f.tell() <= end:
        bytes = bytearray(f.read(3))
        if bytes[0] >> 7 == 1:
            bytes[0] = bytes[0] & 0b01111111
            return int.from_bytes(bytes, ENDIAN), start+pos
        f.seek(-6, io.SEEK_CUR)
    return None

INCODE_BLOCK_SIZE = 8


def seek_incode(f, start, end):
    pos = INCODE_BLOCK_SIZE * int((end - start) / (2 * INCODE_BLOCK_SIZE))
    if pos == 0:
        return None
    f.seek(start+pos, io.SEEK_SET)
    while start <= f.tell() <= end:
        bytes = f.read(INCODE_BLOCK_SIZE)
        ctr = IntContainer(int.from_bytes(bytes, ENDIAN))
        return start+pos, *ctr.parts(11, 16, 16)

    return None


def _read_string(f):
    s = b''
    while b := f.read(1):
        if b == b'\0':
            break
        s += b
    return s.decode('ASCII')


def find_pc(pc):
    outcode, incode = pc.split(" ", 1)

    with open("test.bin", 'rb') as f:
        locations = read_locations(f)
        outcodes = read_outcodes(f)

        start = f.tell()

        oc = outcodes[outcode]
        print(oc)

        start = start + oc.start*8
        end = start + oc.incode_count*8

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
    lat = (lat.value + location['lat']) / 10000
    lon = (lon.value + location['lon']) / 10000

    print("Value found", outcode, incode, location, lat, lon)

