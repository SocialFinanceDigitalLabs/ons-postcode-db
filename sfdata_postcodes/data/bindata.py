from dataclasses import dataclass
from functools import cached_property


@dataclass(frozen=True)
class BinaryField:
    name: str
    bit_length: int


@dataclass(frozen=True)
class BinarySpec:
    byte_length: int
    fields: list[BinaryField]

    @cached_property
    def field_dict(self):
        return {f.name: f for f in self.fields}

    def __getitem__(self, item):
        return self.field_dict[item]


