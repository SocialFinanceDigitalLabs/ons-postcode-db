from sfdata_postcodes.encoder import *
from sfdata_postcodes.encoder import _encode_char, _decode_char


def test_int_container():
    assert IntContainer(1) == 1
    assert IntContainer(10) == 10

    assert IntContainer(1).push(0, 1) == 2
    assert IntContainer(1).push(0, 5) == 32

    assert IntContainer(1).push(0, 3).push(0, 3) == 64
    assert IntContainer(1).push(0, 3).push(3, 3) == 67

    assert IntContainer(67).pop(6) == (1, 3)

    assert IntContainer(67).parts(3, 3) == (1, 0, 3)
    assert IntContainer(67).parts(6) == (1, 3)


def test_encode_char():
    assert _encode_char('A') == 1
    assert _encode_char('B') == 2
    assert _encode_char('C') == 3
    assert _encode_char('Z') == 26
    assert _encode_char('0') == 27
    assert _encode_char('9') == 36
    assert _encode_char(None) == 0
    assert _encode_char('') == 0


def test_decode_char():
    assert _decode_char(1) == 'A'
    assert _decode_char(2) == 'B'
    assert _decode_char(3) == 'C'
    assert _decode_char(26) == 'Z'
    assert _decode_char(36) == '9'
    assert _decode_char(0) == ''


def assert_roundrip(value, *functions):
    new_val = value
    for f in functions:
        new_val = f(new_val)
    assert new_val == value


def test_roundtrip_outcode():
    funcs = [encode_outcode, decode_outcode]

    assert_roundrip('A1', *funcs)
    assert_roundrip('AA1', *funcs)
    assert_roundrip('AA1A', *funcs)

    assert_roundrip('WC1E', *funcs)
    assert_roundrip('N1', *funcs)
    assert_roundrip('N19', *funcs)
    assert_roundrip('SE17', *funcs)

    assert_roundrip('Z9', *funcs)
    assert_roundrip('Z9Z', *funcs)
    assert_roundrip('ZZ9Z', *funcs)


def test_encode_incode():
    assert encode_incode('0AA') == 33
    assert encode_incode('8AA') == 8225


def test_decode_incode():
    assert decode_incode(33) == '0AA'
    assert decode_incode(34) == '0AB'
    assert decode_incode(65) == '0BA'
    assert decode_incode(8225) == '8AA'
    assert decode_incode(10074) == '9ZZ'

    assert decode_incode(0) == '0'  # Not strictly correct, but follows encoding convention


def test_roundtrip_incode():
    funcs = [encode_incode, decode_incode]

    assert_roundrip('0AA', *funcs)
    assert_roundrip('8AA', *funcs)


def test_roundtrip_postcode():
    funcs = [encode_postcode, decode_postcode]
    assert_roundrip('AB1 0AA', *funcs)
    assert_roundrip('AB1 8AA', *funcs)
    assert_roundrip('N19 3SL', *funcs)
    assert_roundrip('SE1 7RU', *funcs)
    assert_roundrip('WC1A 6BT', *funcs)


def test_roundtrip_with_bytes():
    byte_length = 5
    endianness = 'big'
    funcs = [
        encode_postcode,
        lambda x: x.to_bytes(byte_length, endianness),
        lambda x: int.from_bytes(x, endianness),
        decode_postcode
    ]
    assert_roundrip('AB1 0AA', *funcs)
    assert_roundrip('AB1 8AA', *funcs)
    assert_roundrip('N19 3SL', *funcs)
    assert_roundrip('SE1 7RU', *funcs)
    assert_roundrip('WC1A 6BT', *funcs)