#! /usr/bin/env python
#   -*- coding: utf8 -*-
#   coding=utf8
""" Pushover tools and script for sending messages. """

from __future__ import with_statement

import httplib
import urllib

try:
    import json
except ImportError:
    import simplejson as json


class PushoverError(Exception):

    """ Generic pushover related error. """

    pass


class PushoverConfigError(PushoverError):

    """ Config-related error. """

    pass


class PushoverConfig(object):

    """ Config class for pushover.

    This class is used to keep API url, key, and other relevant data. It can
    also be initialized from a file.

    It is a glorified dict.

    """

    # Default mandatory settings
    settings = {
        'proto': 'https',
        'host': 'api.pushover.net',
        'resource': '/1/messages.json',
        'token': None,
        'user': None, }

    # Optional settings
    options = {'device': None, }

    def __init__(self, **kwargs):
        """ Initialize the setting structure.

        Settings can be initialized through kwargs.

        """
        # Set kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __setattr__(self, key, value):
        """ Set the value, or raise exception if not defined. """

        if key in self.settings.keys():
            if not value:
                raise PushoverConfigError("Setting '%s' requires a value" % key)
            self.settings[key] = value
        elif key in self.options.keys():
            self.options[key] = value
        else:
            raise PushoverConfigError("Invalid setting '%s'" % key)

    def __getattr__(self, key):
        """ Get the value, or raise exception if not defined. """

        if key in self.settings:
            return self.settings.get(key)
        elif key in self.options:
            return self.options.get(key)
        raise PushoverConfigError("Invalid setting '%s'" % key)

    def read(self, filename):
        """ Read config from file.

        The config format is very simple:
          - One assignment per line (key = value)
          - Legal settings are defined by self.settings and self.options

        """
        with open(filename, 'r') as fd:
            lineno = 0
            for line in fd.readlines():
                lineno += 1
                try:
                    key, val = line.split('=')
                except ValueError:
                    raise PushoverConfigError(
                        "Error in config '%s', line %d: %s" % (
                        filename, lineno, repr(line.strip())))
                key, val = key.strip(), val.strip()
                try:
                    setattr(self, key, val)
                except PushoverConfigError, e:
                    raise PushoverConfigError(
                        "Error in config '%s', line %d: %s" % (filename, lineno,
                                                               str(e)))

    def url(self):
        """ Get the url to the service, based on current settings. """

        return '%(proto)s://%(host)s%(resource)s' % {'proto': self.proto,
                                                     'host': self.host,
                                                     'resource': self.resource}

    def validate(self):
        """ Check that we have all the neccessary stuff. 
        
        The intention here is to check that the mandatory settings without a
        default value has been set.

        """
        missing = []
        for key, value in self.settings.items():
            if not value:
                missing.append(key)
        if missing:
            raise PushoverConfigError("Validate failed, missing settings: %s" %
                                      ','.join(missing))

    #def prepareMessage(self, message):
        #""" Return urlencoded message. """

        #params = dict(message.toDict().items() + {'token': self.token,
                                                  #'user': self.user})
        #if self.device:
            #params.update({'device': self.device})

        #return urllib.urlencode(params)

    def __repr__(self):
        """ Get a simple representation of the settings. """

        return "PushoverConfig(%s)" % ", ".join(["%s=%s" % (
            key, getattr(self, key) or '<not set>') for key in
            (self.settings.keys() + self.options.keys())])


class PushoverMessage:

    """ Container structure for the Pushover message parameters. """

    pri_high = 1
    pri_default = 0
    pri_low = -1

    def __init__(self, message, title='', url='', url_title=None):
        """ Initialize message with a string, and optional args. """
        self.setTitle(title)
        self.setUrl(url, title=url_title)
        self.setMessage(message)

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
        self.url = url
        self.url_title = title

    def toDict(self, display=False):
        """ Build message dict (for urlencode or display). """
        # Mandatory message parameters
        p = {'message': self.message}

        # Optional message parameters:
        for attr in ('title', 'url', 'url_title', 'priority', 'timestamp'):
            if getattr(self, attr):
                p[attr] = getattr(self, attr)
            elif display:
                p[attr] = '<no %s>' % attr
        return p

    def prepare(self, config):
        """ Return urlencoded message. """

        params = dict(self.toDict().items() + [('token', config.token),
                                              ('user', config.user)])
        if config.device:
            params.update({'device': config.device})

        return urllib.urlencode(params)
        
    def __repr__(self):
        """ String representation. """

        fmt = ("PushoverMessage: %(title)s\n"
               "            url: %(url_title)s, %(url)s\n"
               "        message: %(message)s")
        return fmt % self.toDict(display=True)


class PushoverSender:

    """ Send a pushover message, and process the return value.

    Sends a PushoverMessage object using the settings from a PushoverConfig
    object.

    """

    def __init__(self, settings):
        """ Initialize using a PushoverConfig object. """

        if not isinstance(settings, PushoverConfig):
            raise TypeError(
                "PushoverSender must be set up with a PushoverConfig object.")
        self.settings = settings

    def sendMessage(self, message):
        """ Send a PushoverMessage using the settings from this object. """
        # Prepare
        body = message.prepare(self.settings)

        # Connect and send
        # TODO: Fix unsecure SSL socket (ecrtificate + hostname validation).
        #       Should I bother?
        conn = httplib.HTTPSConnection(self.settings.host)
        conn.request("POST", self.settings.url(), body)
        res = conn.getresponse()

        # TODO: Catch and log json errors
        data = json.loads(res.read())
        conn.close()

        if (not data.get('status')) or data.get('status') != 1:
            for e in data.get('errors', ['no errors', ]):
                print ("Error: %(e)s", {"e": str(e)})
            return False
        return True

# TODO: Usage string. Should we use a proper library (argparse, optparse)?


def main(args):
    """ Script invoke. """
    import os.path
    from getopt import getopt, GetoptError

    rcfile = os.path.join(os.path.expanduser('~'), '.pushoverrc')

    try:
        opts, args = getopt(args, 'c:t:u:T:',
                            ('config=', 'title=', 'url=', 'urltitle='))
    except GetoptError, e:
        raise SystemExit("Usage error: %s" % str(e))

    message = PushoverMessage(' '.join(args))

    for option, value in opts:
        if option in ('-c', '--config'):
            rcfile = value
        elif option in ('-t', '--title'):
            message.setTitle(value.strip())
        elif option in ('-u', '--url'):
            message.setUrl(value.strip())
        elif option in ('-T', '--urltitle'):
            if not message.url:
                raise SystemExit("Cannot provide urltitle with no --url")
            message.setUrl(message.url, title=value.strip())

    config = PushoverConfig()
    try:
        config.read(rcfile)
        config.validate()
    except (PushoverConfigError, IOError), e:
        raise SystemExit("Unable to configure: %s" % str(e))

    sender = PushoverSender(config)
    if sender.sendMessage(message):
        print "Message sent"
    else:
        raise SystemExit("Message failed")

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
