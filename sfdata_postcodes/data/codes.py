from dataclasses import dataclass

from sfdata_postcodes.util import no_none


@dataclass(frozen=True)
class CodeRow:
    id: int
    code: str
    name: str


class CodeContainer:

    def __init__(self, initial_values=None):
        self._codes = []
        self._index = {}

        if initial_values:
            for code, name in initial_values:
                self.add(code, name)

    def add(self, code, name=None):
        if code in self._index:
            return self._index[code]

        if self._codes:
            start = self._codes[-1].id + 1
        else:
            start = 0

        cr = CodeRow(id=start, code=code, name=name)
        self._codes.append(cr)
        self._index[code] = cr

        return cr

    def get_code(self, item):
        try:
            return self[item].code
        except (KeyError, AttributeError):
            return None

    def get_id(self, item):
        try:
            return self[item].id
        except (KeyError, AttributeError):
            return None

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._codes[item]
        else:
            return self._index[item]

    def __len__(self):
        return len(self._codes)

    def __iter__(self):
        return iter(self._codes)

    def __json__(self):
        return {c.id: no_none(code=c.code, name=c.name) for c in sorted(self._codes, key=lambda c: c.id)}
