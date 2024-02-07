""" Pushover tools and script for sending messages. """
import http.client as httplib
import json
import logging
import urllib.parse as urlparse

from . import messages
from . import config

logger = logging.getLogger(__name__)


def _get_preset(args):
    cfg = config.get_config(args.config_file)
    preset = cfg.get_preset(args.preset)
    logger.debug("using preset %s: %r", args.preset, preset)
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
    content = ' '.join(args.message or [])
    if not content:
        raise ValueError("no message to send")
    message = messages.PushoverMessage(content)

    for opt in _arg_to_message_map:
        value = getattr(args, opt, None)
        if value is not None:
            setattr(message, _arg_to_message_map[opt], value)
    return message


def _send(preset, message):
    request_data = message.prepare(preset)
    logger.debug('sending: %r', request_data)
    url_data = urlparse.urlparse(preset.api_url)

    connection_cls = {
        'http': httplib.HTTPConnection,
        'https': httplib.HTTPSConnection,
    }[url_data.scheme]

    # Connect and send
    # TODO: Fix unsecure SSL socket (ecrtificate + hostname validation).
    #       Should I bother?
    conn = connection_cls(url_data.netloc)
    conn.request("POST", url_data.path, urlparse.urlencode(request_data))
    res = conn.getresponse()

    # TODO: Catch and log json errors
    data = json.loads(res.read())
    conn.close()

    return data


def send_message(args):
    preset = _get_preset(args)
    message = _get_message(args)

    result = _send(preset, message)

    return result
