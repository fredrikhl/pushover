""" Pushover message object. """
import datetime

from .config import PushoverOption, PushoverOptionSet


class PushoverPriority(object):

    def __init__(self, strval, intval):
        self.strval = strval
        self.intval = intval

    def __int__(self):
        return self.intval

    def __str__(self):
        return self.strval

    def __eq__(self, other):
        if all(hasattr(other, attr) for attr in ('__int__', '__str__')):
            return int(self) == int(other) and str(self) == str(other)
        return NotImplemented


PRIORITY_EMERGENCY = PushoverPriority('emergency', 2)
PRIORITY_HIGH = PushoverPriority('high', 1)
PRIORITY_NORMAL = PushoverPriority('normal', 0)
PRIORITY_LOW = PushoverPriority('low', -1)
PRIORITY_LOWEST = PushoverPriority('lowest', -2)

PRIORITIES = tuple((
    PRIORITY_EMERGENCY,
    PRIORITY_HIGH,
    PRIORITY_NORMAL,
    PRIORITY_LOW,
    PRIORITY_LOWEST,
))

_int_to_priority_map = dict(
    (int(p), p) for p in PRIORITIES)

_str_to_priority_map = dict(
    (str(p), p) for p in PRIORITIES)

DEFAULT_PRIORITY = PRIORITY_NORMAL


def get_priority(value):
    if value in PRIORITIES:
        return value

    try:
        return _str_to_priority_map[str(value)]
    except (ValueError, KeyError):
        pass

    try:
        return _int_to_priority_map[int(value)]
    except (TypeError, ValueError, KeyError):
        pass
    raise ValueError("invalid priority %r" % (value, ))


def get_timestamp(value):
    if isinstance(value, basestring) and value.isdigit():
        value = int(value)

    if isinstance(value, datetime.datetime):
        value = value
    elif isinstance(value, (int, long)):
        value = datetime.datetime.utcfromtimestamp(value)
    else:
        raise ValueError("invalid datetime %r" % (value, ))
    return value.strftime('%s')


_config_param_map = {
    'api_device': 'device',
    'api_user': 'user',
    'api_token': 'token',
}


class PushoverMessage(PushoverOptionSet):
    """ Container structure for the Pushover message parameters. """
    priority = PushoverOption(
        default=DEFAULT_PRIORITY,
        deserialize=get_priority,
        serialize=lambda p: int(p),
    )
    message = PushoverOption(
        default=None,
        required=True,
    )
    title = PushoverOption(
        default=None,
        required=False,
    )
    url = PushoverOption(
        default=None,
        required=False,
    )
    url_title = PushoverOption(
        default=None,
        required=False,
    )
    timestamp = PushoverOption(
        default=None,
        required=False,
        deserialize=get_timestamp,
        serialize=lambda k: k.strftime('%s') if k else None,
    )

    def __init__(self, message, **kwargs):
        """ Initialize message with a string, and optional args. """
        self.message = message
        super(PushoverMessage, self).__init__(**kwargs)

    def prepare(self, config):
        """ Return urlencoded message. """
        params = dict(self.to_dict())

        params.update(
            (_config_param_map[k], v)
            for k, v in config.to_dict().items()
            if k != 'api_url'
        )

        # if config.api_device:
        #     params.update({'device': config.device})

        return params
