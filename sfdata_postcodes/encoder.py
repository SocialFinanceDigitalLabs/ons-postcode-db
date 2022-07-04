_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'


def _encode_char(c):
    if c is None or c == '':
        return 0
    return _ALPHABET.index(c) + 1


def _decode_char(i):
    if i == 0:
        return ''
    return _ALPHABET[i - 1]


class IntContainer:
    def __init__(self, value):
        self.value = value
        if isinstance(value, IntContainer):
            self.value = value.value

    def push(self, value, bits):
        if isinstance(value, IntContainer):
            value = value.value
        assert value.bit_length() <= bits, 'Value {} is too large to fit in {} bits'.format(value, bits)
        value &= 2 ** bits - 1
        value = (self.value << bits) | value
        return IntContainer(value)

    def pop(self, bits):
        return IntContainer(self.value >> bits), self.mask(bits)

    def mask(self, bits):
        return IntContainer(self.value & (2 ** bits - 1))

    def parts(self, *bits):
        values = []
        ctr = self
        for b in bits[::-1]:
            ctr, v = ctr.pop(b)
            values.append(v)
        values.append(ctr.value)
        return tuple(values[::-1])

    def to_bytes(self, length, endian):
        return self.value.to_bytes(length, endian)

    def __eq__(self, other):
        if isinstance(other, IntContainer):
            return self.value == other.value
        return self.value == other

    def __repr__(self):
        return str(self.value)

    def __sub__(self, other):
        if isinstance(other, IntContainer):
            return self.value - other.value
        return self.value - other

    def __lt__(self, other):
        if isinstance(other, IntContainer):
            return self.value < other.value
        return self.value < other

    def __gt__(self, other):
        if isinstance(other, IntContainer):
            return self.value > other.value
        return self.value > other


def encode_outcode(incode):
    v = [_encode_char(c) for c in incode]
    v += [0] * (4 - len(v))
    return IntContainer(v[0]).push(v[1], 6).push(v[2], 6).push(v[3], 6)


def decode_outcode(outcode):
    value = IntContainer(outcode)
    value, c3 = value.pop(6)
    value, c2 = value.pop(6)
    value, c1 = value.pop(6)
    value, c0 = value.pop(6)

    return _decode_char(c0) + _decode_char(c1) + _decode_char(c2) + _decode_char(c3)


def encode_incode(value):
    return IntContainer(int(value[0])).push(_encode_char(value[1]), 5).push(_encode_char(value[2]), 5)


def decode_incode(value):
    d, c1, c2 = IntContainer(value).parts(5, 5)
    return str(d) + _decode_char(c1) + _decode_char(c2)


def encode_postcode(value):
    outcode, incode = value.split(' ', 1)
    return encode_outcode(outcode).push(encode_incode(incode), 14)


def decode_postcode(value):
    outcode, incode = IntContainer(value).parts(14)
    return decode_outcode(outcode) + " " + decode_incode(incode)
