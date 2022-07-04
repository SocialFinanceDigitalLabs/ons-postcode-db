from dataclasses import dataclass
from functools import cached_property


@dataclass(frozen=True)
class SpatialKey:
    country: str
    county: str
    electoral_division: str
    local_authority_district: str
    imd: int
    x: int
    y: int

    @classmethod
    def from_row(cls, row):
        return cls(
            row.country,
            row.county,
            row.electoral_division,
            row.local_authority_district,
            row.imd,
            int(row.latitude * 10),
            int(row.longitude * 10)
        )


class SpatialContainer:

    def __init__(self, key):
        self._key = key
        self._postcodes = []

    def append(self, postcode):
        self._postcodes.append(postcode)

    def agg(self, func, selector):
        return func(selector(p) for p in self._postcodes)

    @cached_property
    def lat_min(self):
        return self.agg(min, lambda x: x.latitude)

    @cached_property
    def lat_scale(self):
        return self.agg(max, lambda x: x.latitude - self.lat_min)

    @cached_property
    def lon_min(self):
        return self.agg(min, lambda x: x.longitude)

    @cached_property
    def lon_scale(self):
        return self.agg(max, lambda x: x.longitude - self.lon_min)

    @cached_property
    def urban_rural(self):
        values = self.agg(set, lambda x: x.urban_rural_classification)
        return list(sorted(values))
