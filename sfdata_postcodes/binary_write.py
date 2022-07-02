
import csv
from dataclasses import dataclass, field
from functools import cached_property

from io import TextIOWrapper

from zipfile import ZipFile

from tqdm import tqdm

from sfdata_postcodes import spec
from sfdata_postcodes.encoder import  encode_outcode, encode_incode

ENDIAN = 'big'


@dataclass(frozen=True)
class Row:
    pcd: str
    country: str
    county: str
    electoral_division: str
    local_authority_district: str
    urban_rural_classification: str
    imd: int
    osgrid_east: int
    osgrid_north: int
    osgrid_quality: int
    latitude: float
    longitude: float

    @cached_property
    def outcode(self):
        return self.pcd.split(" ", 1)[0]

    @cached_property
    def incode(self):
        return self.pcd.split(" ", 1)[1]

    @classmethod
    def from_row(cls, row):
        return cls(
            pcd=row[2],
            county=row[5],
            electoral_division=row[6],
            local_authority_district=row[7],
            osgrid_east=row[11],
            osgrid_north=row[12],
            osgrid_quality=row[13],
            country=row[16],
            urban_rural_classification=row[40],
            latitude=float(row[42]) if row[42] else None,
            longitude=float(row[43]) if row[43] else None,
            imd=row[47],
        )

    @cached_property
    def spatial_key(self):
        return SpatialKey(self.country, self.county, self.electoral_division,
                          self.local_authority_district, self.imd)


@dataclass(frozen=True)
class SpatialKey:
    country: str
    county: str
    electoral_division: str
    local_authority_district: str
    imd: int


@dataclass(frozen=True)
class SpatialData:
    index: int
    key: SpatialKey
    _lat: [] = field(default_factory=lambda: [])
    _lon: [] = field(default_factory=lambda: [])

    def add_lat_lon(self, lat, lon):
        lat = float(lat)
        lon = float(lon)
        if 0 < lat < 90:
            self._lat.append(lat)
            self._lon.append(lon)

    @cached_property
    def mean(self):
        if self._lat and self._lon:
            return sum(self._lat) / len(self._lat), sum(self._lon) / len(self._lon)
        else:
            return None, None

    @cached_property
    def min(self):
        if self._lat and self._lon:
            return min(self._lat), min(self._lon)
        else:
            return None, None

    @cached_property
    def var(self):
        if self._lat and self._lon:
            return (
                (max(self._lat) - min(self._lat))/2,
                (max(self._lon) - min(self._lon))/2,
            )
        else:
            return None, None


def read_zip_file(filename, max_postcodes=None):
    postcodes = {}
    locations = {}
    with ZipFile(filename, 'r') as zipfile:
        zip_info = zipfile.getinfo(spec.POSTCODE_FILE)
        last_pos = 0

        with zipfile.open(spec.POSTCODE_FILE, 'r') as file:
            pc_reader = csv.reader(TextIOWrapper(file))
            next(pc_reader)  # skip header

            progress = tqdm(total=zip_info.file_size)
            for ix, row in enumerate(pc_reader):
                progress.update(file.tell() - last_pos)
                last_pos = file.tell()

                data = Row.from_row(row)
                postcodes.setdefault(data.outcode, []).append(data)
                loc = locations.setdefault(data.spatial_key, SpatialData(len(locations), data.spatial_key))
                loc.add_lat_lon(data.latitude, data.longitude)

                if max_postcodes and ix >= max_postcodes:
                    break

    return dict(postcodes=postcodes, locations=locations)


def _write_string(f, s):
    if s:
        f.write(s.encode('ASCII'))
    f.write(b'\0')


def write_binary_file(zipfilename, outfilename="test.bin", max=None):
    data = read_zip_file(zipfilename, max_postcodes=max)
    postcodes = data["postcodes"]
    locations = data["locations"]

    outcodes = [(outcode, encode_outcode(outcode)) for outcode in postcodes.keys()]
    outcodes.sort(key=lambda x: x[1])

    with open(outfilename, 'wb') as f:

        sorted_locations = sorted(locations.values(), key=lambda x: x.index)
        f.write(len(locations).to_bytes(2, ENDIAN))
        for location in sorted_locations:
            key = location.key
            _write_string(f, key.country)
            _write_string(f, key.county)
            _write_string(f, key.electoral_division)
            _write_string(f, key.local_authority_district)

            min = location.min
            if min[0]:
                lat, lon = int(min[0]*10000), int(min[1]*10000)
            else:
                lat = lon = 0
            f.write(lat.to_bytes(3, ENDIAN, signed=True))
            f.write(lon.to_bytes(3, ENDIAN, signed=True))

        f.write(len(outcodes).to_bytes(2, ENDIAN))
        for outcode, outcode_enc in outcodes:
            f.write(outcode_enc.to_bytes(3, ENDIAN))
            f.write(len(postcodes[outcode]).to_bytes(2, ENDIAN))

        for outcode, outcode_enc in tqdm(outcodes):
            for postcode in postcodes[outcode]:
                loc = locations[postcode.spatial_key]
                lat_min, lon_min = loc.min

                lat = int((postcode.latitude - lat_min) * 10000) if postcode.latitude and lat_min else 0
                lon = int((postcode.longitude - lon_min) * 10000) if postcode.longitude and lon_min else 0

                value = (
                    encode_incode(postcode.incode)
                    .push(loc.index, 11)
                    .push(lat, 16)
                    .push(lon, 16)
                )

                f.write(value.to_bytes(8, ENDIAN))

