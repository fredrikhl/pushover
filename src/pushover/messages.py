""" Pushover message object. """
import datetime
import enum

from .config import PushoverOption, PushoverOptionSet


class PushoverPriority(enum.IntEnum):
    """
    Pushover message priority levels.

    This enum can be used to validate, serialize and deserialize priority
    levels.
    """
    lowest = -2
    low = -1
    normal = 0
    high = 1
    emergency = 2

    @classmethod
    def _missing_(cls, value):
        # support looking up enum by serialized intval
        try:
            intval = int(value)
        except ValueError:
            pass
        else:
            if intval in cls:
                return cls(intval)
            else:
                return None

        # support looking up enum by name
        for member in cls:
            if member.name == value:
                return member
        return None


DEFAULT_PRIORITY = PushoverPriority.normal


def get_timestamp(value):
    if isinstance(value, str) and value.isdigit():
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
        deserialize=PushoverPriority,
        serialize=int,
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

    def prepare(self, preset):
        """
        Return serialized message params using a given preset.

        """
        # Create a message dict with serialized fields from preset
        # (device, etc..)
        params = {
            _config_param_map[k]: v
            for k, v in preset.to_dict().items()
            if k in _config_param_map
        }

        # Update message dict with serialized fields from this object
        params.update(self.to_dict())
        return params
