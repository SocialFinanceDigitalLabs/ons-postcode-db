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
