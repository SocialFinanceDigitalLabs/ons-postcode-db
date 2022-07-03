import bz2
import csv
import json
from dataclasses import dataclass, field, asdict
from functools import cached_property

from io import TextIOWrapper
from struct import pack

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
                          self.local_authority_district, self.imd, int(self.latitude*10), int(self.longitude*10))


@dataclass(frozen=True)
class SpatialKey:
    country: str
    county: str
    electoral_division: str
    local_authority_district: str
    imd: int
    x: int
    y: int



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


def write_binary_file(zipfilename, outfilename="test.bin", max_postcodes=None):
    data = read_zip_file(zipfilename, max_postcodes=max_postcodes)
    postcodes = data["postcodes"]

    outcodes = sorted(postcodes.keys())

    locations = data["locations"]
    sorted_locations = sorted(locations.values(), key=lambda x: x.index)

    loc_length = len(locations)
    print(f" {loc_length} location Indexes requiring {loc_length.bit_length()} bits")
    assert loc_length.bit_length() <= 16, "Location index must be 16 bits"

    with open(outfilename, 'wb') as f:
        metadata = dict(
            outcodes=[dict(outcode=oc, incode_count=len(postcodes[oc])) for oc in outcodes],
            locations=[{"lat": loc.min[0], "lon": loc.min[1], **asdict(loc.key)} for loc in sorted_locations],
        )
        metadata = bz2.compress(bytes(json.dumps(metadata), 'ASCII'))
        f.write(pack('I', len(metadata)))
        f.write(metadata)

        for outcode in tqdm(outcodes):
            for postcode in postcodes[outcode]:
                loc = locations[postcode.spatial_key]
                lat_min, lon_min = loc.min

                lat = int((postcode.latitude - lat_min) * 10000 / 4) if postcode.latitude and lat_min else 0
                lon = int((postcode.longitude - lon_min) * 10000 / 4) if postcode.longitude and lon_min else 0

                assert max(lat, lon).bit_length() <= 9, f"Latitude ({lat}) and longitude ({lon}) must be 9 bits. " \
                                                        f"This value requires {max(lat, lon).bit_length()} bits"

                value = (
                    encode_incode(postcode.incode)  # 14 bits
                    .push(loc.index, 16)  # 30
                    .push(lat, 9)  # 39
                    .push(lon, 9)  # 48
                )

                f.write(value.to_bytes(6, ENDIAN))  # Max capacity 48 bits

