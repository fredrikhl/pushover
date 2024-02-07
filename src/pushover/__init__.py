""" Pushover tools and script for sending messages. """
import http.client
import json
import logging
import urllib.parse

from . import messages
from . import config

logger = logging.getLogger(__name__)


def _get_preset(args):
    """ Create a PushoverPreset from a set of input argument values. """
    # Read the config given in cli options, or from default locations
    cfg = config.get_config(args.config_file)

    # Fetch the preset given in cli options from the config
    # (or the default preset)
    preset = cfg.get_preset(args.preset)
    logger.debug("using preset %s: %r", args.preset, preset)

    # Apply cli options to preset
    for opt in preset:
        value = getattr(args, opt, None)
        if value is not None:
            logger.debug("using %s=%r from args", opt, value)
            setattr(preset, opt, value)
    preset.validate()
    return preset


_arg_to_message_map = {
    'msg_url': 'url',
    'msg_url_title': 'url_title',
    'msg_title': 'title',
    'msg_priority': 'priority',
}


def _get_message(args):
    """ Create a PushoverMessage from a set of input argument values. """
    content = " ".join(args.message or ())
    if not content:
        raise ValueError("empty message")
    message = messages.PushoverMessage(content)

    for arg_dest in _arg_to_message_map:
        value = getattr(args, arg_dest, None)
        if value is not None:
            setattr(message, _arg_to_message_map[arg_dest], value)
    return message


def _send(preset, message):
    request_data = message.prepare(preset)
    logger.debug('sending: %r', request_data)
    url_data = urllib.parse.urlparse(preset.api_url)

    connection_cls = {
        'http': http.client.HTTPConnection,
        'https': http.client.HTTPSConnection,
    }[url_data.scheme]

    conn = connection_cls(url_data.netloc)
    conn.request("POST", url_data.path, urllib.parse.urlencode(request_data))
    res = conn.getresponse()

    # TODO: Catch and log json errors
    data = json.loads(res.read())
    conn.close()

    return data


def send_message(args):
    """ Send a message according to the config and cli options. """
    return _send(_get_preset(args), _get_message(args))
