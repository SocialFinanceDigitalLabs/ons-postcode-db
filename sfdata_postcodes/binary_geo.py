import csv
import io
from dataclasses import dataclass, field

from io import TextIOWrapper

from zipfile import ZipFile

from tqdm import tqdm

from sfdata_postcodes import spec
from sfdata_postcodes.encoder import  encode_outcode, encode_incode, decode_outcode, \
    decode_incode

GEO_START = (49, -8.5)
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

    @property
    def outcode(self):
        return self.pcd.split(" ", 1)[0]

    @property
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
            latitude=row[42],
            longitude=row[43],
            imd=row[47],
        )

    @property
    def spatial_key(self):
        return SpatialKey(self.country, self.county, self.electoral_division, self.local_authority_district)


@dataclass(frozen=True)
class SpatialKey:
    country: str
    county: str
    electoral_division: str
    local_authority_district: str


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

    @property
    def mean(self):
        if self._lat and self._lon:
            return sum(self._lat) / len(self._lat), sum(self._lon) / len(self._lon)
        else:
            return None, None

    @property
    def var(self):
        if self._lat and self._lon:
            return (
                (max(self._lat) - min(self._lat))/2,
                (max(self._lon) - min(self._lon))/2,
            )
        else:
            return None, None


def read_zip_file(filename):
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

    return dict(postcodes=postcodes, locations=locations)


def write_binary_file(zipfilename, outfilename="test.bin"):
    data = read_zip_file(zipfilename)
    postcodes = data["postcodes"]
    locations = data["locations"]

    outcodes = [(outcode, encode_outcode(outcode)) for outcode in postcodes.keys()]
    outcodes.sort(key=lambda x: x[1])

    with open("test.bin", 'wb') as f:
        for outcode in tqdm(outcodes):
            bytes = bytearray(outcode[1].to_bytes(3, ENDIAN))
            bytes[0] = bytes[0] | 0b10000000  # Marker for outcode
            f.write(bytes)
            for postcode in postcodes[outcode[0]]:
                value = (
                    encode_incode(postcode.incode)
                    .push(locations[postcode.spatial_key].index, 11)
                )

                f.write(value.to_bytes(3, ENDIAN))

