import bz2
import io
import json
from dataclasses import dataclass
from functools import cached_property, lru_cache
from math import floor
from struct import unpack, calcsize
from typing import Iterator

from sfdata_postcodes.binfile.populate_binfile import ENDIAN
from sfdata_postcodes.data.bindata import BinaryField, BinarySpec
from sfdata_postcodes.encoder import IntContainer


class PostcodeFile:

    def __init__(self, source):
        self._file_obj = open(source, 'rb')

        self._metadata = self._read_metadata()
        self._incode_block_size = self._metadata['data_spec'].byte_length

        self._incode_start = self._file_obj.tell()
        self._file_obj.seek(0, io.SEEK_END)
        self._incode_end = self._file_obj.tell()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __len__(self):
        return int((self._incode_end - self._incode_start) / self._incode_block_size)

    def __iter__(self):
        return PostcodeIterator(self)

    def close(self):
        self._file_obj.close()
        self._file_obj = None

    def unpack(self, bytes):
        value = int.from_bytes(bytes, ENDIAN)
        value_parts = IntContainer(value).parts(*self.field_sizes)
        return IncodePtr(**{
            n: value_parts[ix+1].value
            for ix, n in enumerate(self.field_names)
        })

    @cached_property
    def fields(self):
        return tuple(self._metadata['data_spec'].fields)

    @cached_property
    def field_sizes(self):
        return tuple([f.bit_length for f in self.fields])

    @cached_property
    def field_names(self):
        return tuple([f.name for f in self.fields])

    @lru_cache(maxsize=1000)
    def read_postcode(self, pos):
        """
        Finds the postcode occupying that position in the file. The pos is in incode blocks,
        not bytes, so read_incode(0) will return the first incode, and read_incode(100) will
        return the 101st incode.
        :param pos:
        :return:
        """
        # pos = self._incode_block_size * int((end - start) / (2 * self._incode_block_size))
        # if pos == 0:
        #     return None

        file_pos = self._incode_start + pos * self._incode_block_size

        self._file_obj.seek(file_pos, io.SEEK_SET)
        data = self._file_obj.read(self._incode_block_size)
        return Postcode(self._metadata, pos, self.unpack(data))

    @cached_property
    def incode_index(self):
        return {v['code']: k for k, v in self._metadata['incodes'].items()}

    @cached_property
    def outcode_index(self):
        return self._metadata['outcodes']

    @lru_cache(maxsize=1000)
    def exact(self, postcode):
        outcode, incode = postcode.split(" ", 1)
        incode_key = self.incode_index[incode]
        fractional_pos = len(self.incode_index) / incode_key  # We're starting skewed based on the distribution

        outcode_data = self.outcode_index[outcode]
        start = outcode_data.start
        end = outcode_data.end

        pos = floor(start + (end - start) / fractional_pos)
        while True:
            postcode = self.read_postcode(pos)
            if postcode.incode_ptr.incode_key == incode_key:
                return postcode
            elif postcode.incode_ptr.incode_key > incode_key:
                end = pos
            else:
                start = pos

            offset = incode_key - postcode.incode_ptr.incode_key
            if pos + offset < start:
                offset = (end-start) // -2
            elif pos + offset > end:
                offset = (end-start) // 2

            new_pos = pos + offset

            if start == end or pos == new_pos:
                raise KeyError("Postcode not found")

            pos = new_pos

    def _read_metadata(self):
        if self._file_obj is None:
            raise Exception("File is closed")

        metadata_length = unpack("I", self._file_obj.read(calcsize("I")))[0]
        metadata = bz2.decompress(self._file_obj.read(metadata_length))
        metadata = json.loads(metadata)

        data_spec = metadata['data_spec']
        data_spec['fields'] = [BinaryField(**f) for f in data_spec['fields']]
        metadata['data_spec'] = BinarySpec(**data_spec)

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


@dataclass
class IncodePtr:
    incode_key: int
    spatial_key: int
    latitude: int
    longitude: int
    urban_rural: int


class Postcode:

    def __init__(self, metadata, pos, incode_ptr):
        self._metadata = metadata
        self._pos = pos
        self._incode_ptr = incode_ptr

    @property
    def pos(self):
        return self._pos

    @property
    def incode_ptr(self):
        return self._incode_ptr

    @cached_property
    def outcode(self):
        return self._metadata['outcodes'].find_outcode(self._pos)

    @cached_property
    def incode(self):
        return self._metadata['incodes'][self._incode_ptr.incode_key]

    @cached_property
    def pcd(self):
        return f'{self.outcode.outcode} {self.incode["code"]}'

    @cached_property
    def location(self):
        return self._metadata['locations'][self._incode_ptr.spatial_key]

    @cached_property
    def imd(self):
        return self.location['imd']

    @cached_property
    def country(self):
        return self.__locdata('country')

    @cached_property
    def county(self):
        return self.__locdata('county')

    @cached_property
    def electoral_division(self):
        return self.__locdata('electoral_division')

    @cached_property
    def local_authority_district(self):
        return self.__locdata('local_authority_district')

    @cached_property
    def urban_rural(self):
        try:
            return self._metadata['urban_rural_classification'][self.location['urban_rural'][self._incode_ptr.urban_rural]]
        except KeyError:
            return None

    @cached_property
    def latitude(self):
        return self._incode_ptr.latitude * self.location['lat_scale'] / 255 + self.location['lat']

    @cached_property
    def longitude(self):
        return self._incode_ptr.longitude * self.location['lon_scale'] / 255 + self.location['lon']

    @cached_property
    def google(self):
        return f"https://www.google.com/maps/search/{self.latitude:0.5f},{self.longitude:0.5f}/"

    def __locdata(self, prop):
        try:
            return self._metadata[prop][self.location[prop]]
        except KeyError:
            return None

    def __repr__(self):
        return f"Postcode({self._pos}): {self.pcd}"


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


class PostcodeIterator(Iterator[Postcode]):
    def __init__(self, reader, start=-1, end=-1):
        self._pos = start
        self._reader = reader
        if end == -1:
            self._end = len(reader)
        else:
            self._end = end

    def __next__(self) -> Postcode:
        self._pos += 1
        if self._pos >= self._end:
            raise StopIteration()
        return self._reader.read_postcode(self._pos)

    def __len__(self):
        return self._end - self._pos
