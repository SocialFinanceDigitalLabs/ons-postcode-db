import inspect
import logging


def caller_name():
    return inspect.stack()[2][3]


def safe(type_, value, default=None, log=False, catch=(Exception, )):
    try:
        return type_(value)
    except catch:
        if log:
            logging.getLogger(caller_name()).exception("Failed to convert '%s' to %s", value, type_)
        return default
