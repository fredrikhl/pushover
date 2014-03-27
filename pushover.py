#! /usr/bin/env python
#   -*- coding: utf8 -*-
#   coding=utf8
""" Pushover tools and script for sending messages. """

from __future__ import with_statement

import httplib
import urllib
import logging

try:
    import json
except ImportError:
    import simplejson as json


class PushoverConfig:

    """ Config class for pushover.

    This class is used to keep API url, key, and other relevant data. It can
    also be initialized from a file.

    """

    defaults = {
        'proto': 'https', 'host': 'api.pushover.net',
        'token': '', 'user': '', 'device': '', }

    def __init__(self, **kwargs):
        """ Initialize the setting structure.

        Settings can be initialized through kwargs.

        """
        self.logger = None

        for key, value in self.defaults.items():
            setattr(self, key, value)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def read(self, filename):
        """ Read config from file.

        The config format is very simple:
          - One assignment per line (key = value)
          - Legal keys are defined by self.defaults.keys()
          - Each value is a single word string

        """
        with open(filename, 'r') as fd:
            lineno = 0
            for line in fd.readlines():
                lineno += 1
                try:
                    key, val = line.split('=')
                except ValueError:
                    if self.logger:
                        self.logger.warning(
                            "Error in config '%s', line %d: %s",
                            filename, lineno, repr(line))
                    continue
                key, val = key.strip(), val.strip()
                try:
                    setattr(self, key, val)
                    if self.logger:
                        self.logger.debug("Read config: <%s>=<%s>",
                                          str(key), str(val))
                except AttributeError:
                    if self.logger:
                        self.logger.error("Unable to set: <%s>=<%s>",
                                          str(key), str(val))
                    continue

    def url(self):
        """ Get the url to the service, based on current settings. """

        return '%(proto)s://%(host)s/1/messages.json' % {
            'proto': self.proto,
            'host': self.host, }

    def validate(self):
        """ Check that we have all the neccessary stuff. """
        valid = True
        # This is mostly to check that we have a token and device key.
        for attr in self.defaults.keys():
            if not getattr(self, attr) or attr == 'device':
                valid = False
                if self.logger:
                    self.logger.warning("No setting for %s", attr)
        return valid

    def __repr__(self):
        """ Get a simple representation of the settings. """
        return "PushoverConfig(%s)" % ", ".join(["%s=%s" % (
            key, getattr(self, key, '<not set>')) for key in
            self.defaults.keys()])


class PushoverMessage:

    """ Container structure for the Pushover message parameters. """

    pri_high = 1
    pri_default = 0
    pri_low = -1

    def __init__(self, message, title='', url='', url_title=''):
        """ Initialize message with a string, and optional args. """
        self.message   = message
        self.title     = title
        self.url       = url
        self.url_title = url_title
        self.priority  = self.pri_default
        self.timestamp = None

    def setTitle(self, title):
        """ Set the message title. """
        self.title = title

    def setMessage(self, message):
        """ Set the message contents. """
        self.message = message

    def setUrl(self, url, title=None):
        """ Set the message link (and optional link title). """
        # TODO: Validate url?
        self.url = url
        if title:
            self.url_title = title

    def toDict(self):
        """ Build message dict (for urlencode). """
        # Mandatory message parameters
        p = {'message': self.message}

        # Optional message parameters:
        if self.title:
            p.update({'title': self.title})
        if self.url:
            p.update({'url': self.url})
        if self.url_title:
            p.update({'url_title': self.url_title})
        if self.priority:
            p.update({'priority': self.priority})
        if self.timestamp:
            p.update({'timestamp': self.timestamp})

        return p

    def encode(self):
        """ Return urlencoded message. """
        # TODO: Move the token++ settings into the message, and let the
        # toDict+encode methods do the encoding.
        # The encode method is useless if we don't have all the parameters.
        return urllib.urlencode(self.toDict())

    def __repr__(self):
        """ String representation. """
        obj = "PushoverMessage, "
        title = self.title or "<no title>"
        if self.url:
            title += ' (%s%s)' % (
                self.url_title+': ' if self.url_title else '',
                self.url, )
        return "%s%s\n%s%s" % (obj, title, ' ' * len(obj),
                               self.message or "<no message>")


class PushoverSender:

    """ Send a pushover message, and process the return value.

    Sends a PushoverMessage object using the settings from a PushoverConfig
    object.

    """

    def __init__(self, settings, logger=None):
        """ Initialize using a PushoverConfig object. """

        if not isinstance(settings, PushoverConfig):
            raise TypeError(
                "PushoverSender must be set up with a PushoverConfig object.")
        self.settings = settings
        self.logger = logger

    def sendMessage(self, message):
        """ Send a PushoverMessage using the settings from this object. """
        # Prepare
        params = message.toDict()
        params.update({'token':  self.settings.token})
        params.update({'user':   self.settings.user})
        if self.settings.device:
            params.update({'device': self.settings.device})

        body = urllib.urlencode(params)
        if self.logger:
            self.logger.debug("Request body: %(body)s", {"body": body})

        # Connect and send
        # TODO: Fix unsecure SSL socket (ecrtificate + hostname validation).
        #       Should I bother?
        # Also: Catch and log connection related exceptions.
        conn = httplib.HTTPSConnection(self.settings.host)
        conn.request("POST", self.settings.url(), body)
        res = conn.getresponse()
        if self.logger:
            self.logger.debug("HTTP reply: %(status)d %(reason)s",
                              {"status": res.status, "reason": res.reason})

        # TODO: Catch and log json errors
        data = json.loads(res.read())
        conn.close()

        if (not data.get('status')) or data.get('status') != 1:
            if self.logger:
                for e in data.get('errors', ['no errors', ]):
                    self.logger.warning("Error: %(e)s", {"e": str(e)})
            return False
        return True

# TODO: Usage string. Should we use a proper library (argparse, optparse)?


def main(args):
    """ Script invoke. """
    import os.path
    from getopt import getopt, GetoptError

    rcfile = os.path.join(os.path.expanduser('~'), '.pushoverrc')
    logger = logging
    loglevel = logging.INFO

    def _exit(message):
        """ Error exit helper. Use: return _exit("message") """
        if logger:
            logger.error(message)
            return 1
        raise SystemExit(message)

    try:
        opts, args = getopt(args, 'c:dqt:u:l:',
                            ('config=', 'debug', 'quiet', 'title=', 'url=',
                             'linkname='))
    except GetoptError, e:
        return _exit("Usage error: %s" % str(e))

    message = PushoverMessage(' '.join(args))

    for option, value in opts:
        if option in ('-c', '--config'):
            rcfile = value
        elif option in ('-d', '--debug'):
            loglevel = logging.DEBUG
        elif option in ('-q', '--quiet'):
            logger = None
        elif option in ('-t', '--title'):
            message.setTitle(value.strip())
        elif option in ('-u', '--url'):
            message.setUrl(value.strip())
        elif option in ('-l', '--linkname'):
            if not message.url:
                raise SystemExit("Cannot provide linkname with no --url")
            message.setUrl(message.url, title=value.strip())

    logging.basicConfig(format='%(levelname)s - %(message)s', level=loglevel)

    config = PushoverConfig(logger=logger)
    try:
        config.read(rcfile)
    except IOError, e:
        return _exit("Unable to read config: %s" % str(e))

    if not config.validate():
        return _exit("Invalid config")

    sender = PushoverSender(config, logger=logger)
    if sender.sendMessage(message):
        if logger:
            logger.info("Message sent")
    else:
        return _exit("Message failed")

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
