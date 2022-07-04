import inspect
import logging
from decimal import Decimal
from json import JSONEncoder


def caller_name():
    return inspect.stack()[2][3]


def safe(type_, value, default=None, log=False, catch=(Exception, )):
    try:
        return type_(value)
    except catch:
        if log:
            logging.getLogger(caller_name()).exception("Failed to convert '%s' to %s", value, type_)
        return default


def no_none(value=None, **kwargs):
    if not value:
        value = kwargs
    return {k: v for k, v in value.items() if v is not None}


class PCEncoder(JSONEncoder):
    def default(self, o):
        if hasattr(o, '__json__'):
            return o.__json__()
        elif isinstance(o, Decimal):
            return float(o)
        return JSONEncoder.default(self, o)


class PropContainer:

    def __init__(self, value):
        self._value = value

    def __getattr__(self, name):
        if self._value is None:
            return PropContainer(None)

        try:
            return PropContainer(self._value[name])
        except (KeyError, TypeError):
            pass

        if hasattr(self._value, name):
            return PropContainer(getattr(self._value, name))

        return PropContainer(None)

    def __format__(self, format_spec):
        if self._value is None:
            return ''
        return format(self._value, format_spec)

    def __str__(self):
        return str(self._value)
