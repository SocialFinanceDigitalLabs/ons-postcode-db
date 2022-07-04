from dataclasses import dataclass
from decimal import Decimal
from functools import cached_property

from sfdata_postcodes.util import safe


@dataclass(frozen=True)
class PostcodeRow:
    pcd: str
    country: str
    county: str
    electoral_division: str
    local_authority_district: str
    urban_rural_classification: str
    imd: str
    osgrid_east: int
    osgrid_north: int
    osgrid_quality: int
    latitude: float
    longitude: float

    @cached_property
    def pc_parts(self):
        return self.pcd.split(' ')

    @cached_property
    def outcode(self):
        return self.pc_parts[0]

    @cached_property
    def incode(self):
        return self.pc_parts[1]

    @classmethod
    def from_row(cls, row):
        return cls(
            pcd=row[2],
            county=row[5],
            electoral_division=row[6],
            local_authority_district=row[7],
            osgrid_east=safe(int, row[11]),
            osgrid_north=safe(int, row[12]),
            osgrid_quality=safe(int, row[13]),
            country=row[16],
            urban_rural_classification=row[40],
            latitude=safe(float, row[42]),
            longitude=safe(float, row[43]),
            imd=safe(int, row[47]),
        )