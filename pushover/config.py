"""
Pushover client options.

TODO: This is way too over-engineered and stupid.  Maybe just replace the whole
thing with attrs and a simple json/yaml parser?
"""
import argparse
import collections
import configparser
import io
import logging
import os
import sys

from . import cli_utils

logger = logging.getLogger(__name__)


_XDG_DATA_DIRS = (
    os.environ.get("XDG_CONFIG_DIRS")
    or "/usr/local/share:/usr/share"
).split(":")

_XDG_CONFIG_DIRS = (
    os.environ.get("XDG_CONFIG_DIRS")
    or "/etc/xdg/pushover"
).split(":")

_XDG_CONFIG_HOME = (
    os.environ.get("XDG_CONFIG_HOME")
    or os.path.expanduser("~/.config")
)


# Config file basename
CONFIG_FILENAME = "pushover.conf"

# Any item will overwrite values from the previous
CONFIG_DIRS = (
    tuple(os.path.join(d, "pushover") for d in reversed(_XDG_DATA_DIRS))
    + tuple(os.path.join(d, "pushover") for d in reversed(_XDG_CONFIG_DIRS))
    + (os.path.join(_XDG_CONFIG_HOME, "pushover"),)
)


def get_priority(filename=None, reverse=False, filter_missing=False):
    """ Get an ordered list of config file locations.  """
    dirs = reversed(CONFIG_DIRS) if reverse else CONFIG_DIRS
    for d in dirs:
        path = os.path.join(d, filename) if filename else d
        if not filter_missing or os.path.exists(path):
            yield path


def find_config(filename):
    """
    Find all available configuration files.

    :param filename: An optional user supplied file to throw into the mix
    """
    for filename in get_priority(filename=filename, filter_missing=True):
        logger.debug("found config %r", filename)
        yield filename


class PushoverOption(object):
    """
    A single config option for pushover.

    Example:
    ::

        foo_str = PushoverOption(
            default="value",
            required=False,
            serialize=str,
            deserialize=(lambda x: str(x or "").strip()),
        )
    """

    def __init__(self,
                 default=None,
                 required=True,
                 serialize=str,
                 deserialize=None):
        """
        :param default: A default value for the option
        :param bool required: Whether the value must be set
        :param callable transform:
        """
        self._default = default
        self.required = required
        self.serialize = serialize
        self.deserialize = deserialize

    def __repr__(self):
        return (
            "{cls.__name__}("
            "default={obj.default!r}, "
            "required={obj.required!r}, "
            "serialize={obj.serialize!r}, "
            "deserialize={obj.deserialize!r})"
        ).format(cls=type(self), obj=self)

    @property
    def default(self):
        if callable(self._default):
            return self._default()
        else:
            return self._default

    @property
    def attr(self):
        """ attribute for storing the option value in the owner object.  """
        return "_{cls.__name__}__{id:02x}".format(cls=type(self),
                                                  id=id(self))

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        else:
            return getattr(obj, self.attr, self.default)

    def __set__(self, obj, raw_value):
        if callable(self.deserialize):
            value = self.deserialize(raw_value)
        else:
            value = raw_value
        setattr(obj, self.attr, value)

    def __delete__(self, obj):
        if hasattr(obj, self.attr):
            delattr(obj, self.attr)


DEFAULT_URL = "https://api.pushover.net/1/messages.json"


class PushoverOptionSet(object):
    """
    Container class for pushover options.

    Example:
    ::

        class MyConfigSectino(PushoverOptionSet):
            foo = PushoverOption()
            bar = PushoverOption()
    """

    # rename url -> api_url, etc?
    # add app_default_preset?
    # add msg_default_* for message settings?

    def __init__(self, **kwargs):
        for k in kwargs:
            if k in self:
                setattr(self, k, kwargs[k])
            else:
                raise TypeError(
                    "{cls} got an unexpected keyword argument {arg}"
                    .format(cls=type(self), arg=repr(k)))

    def __repr__(self):
        args = ", ".join("{k}={v}".format(k=k, v=repr(getattr(self, k)))
                         for k in self if self.is_set(k))
        return ("{cls.__name__}({args})").format(cls=type(self), args=args)

    def __iter__(self):
        return iter(self.list_options())

    @classmethod
    def list_options(cls):
        return tuple(
            k for k in cls.__dict__
            if isinstance(cls.__dict__[k], PushoverOption))

    @classmethod
    def _get_option(cls, option):
        return getattr(cls, option)

    @classmethod
    def get_defaults(cls):
        return tuple(
            (k, cls._get_option(k).default)
            for k in cls.list_options())

    def is_set(self, option):
        return hasattr(self, self._get_option(option).attr)

    def is_required(self, option):
        return self._get_option(option).required

    def validate(self):
        for name in self:
            if self.is_required(name) and not getattr(self, name):
                raise ValueError("Empty required value %r" % (name, ))

    @classmethod
    def from_dict(cls, data):
        args = {}
        options = dict((opt, cls._get_option(opt))
                       for opt in cls.list_options())
        transforms = dict((opt, options[opt].deserialize)
                          for opt in options
                          if options[opt].deserialize)
        for k in data:
            if k in transforms:
                args[k] = transforms[k](data[k])
            else:
                args[k] = data[k]
        return cls(**args)

    def to_dict(self):
        data = {}
        options = dict((opt, self._get_option(opt))
                       for opt in self.list_options())
        transforms = dict((opt, options[opt].serialize)
                          for opt in options
                          if options[opt].serialize)
        for k in options:
            value = getattr(self, k)
            if value is None:
                continue
            if k in transforms:
                data[k] = transforms[k](value)
            else:
                data[k] = value
        return data


class PushoverPreset(PushoverOptionSet):

    api_url = PushoverOption(default=DEFAULT_URL)
    api_user = PushoverOption()
    api_token = PushoverOption()
    api_device = PushoverOption(required=False)

    @classmethod
    def list_options(cls):
        # We want explicit ordering
        return tuple(("api_url", "api_user", "api_token", "api_device"))


EXAMPLE_CONFIG = PushoverPreset(
    api_user="example-user",
    api_token="example-token",
    api_device="example-device",
)


class PushoverConfig(object):
    """
    The pushover config object.
    """

    dict_type = collections.OrderedDict
    preset_cls = PushoverPreset

    def __init__(self, config=None):
        defaults = self.dict_type(self.preset_cls.get_defaults())
        self._cp = configparser.RawConfigParser(defaults, self.dict_type, True)

    @property
    def defaults(self):
        """ direct access to the defaults, for modifying. """
        return self._cp.defaults()

    def list_presets(self):
        """ list presets (sections). """
        return tuple(self._cp.sections())

    def get_preset(self, name=None):
        if name is None:
            data = dict(self.defaults)
        elif self._cp.has_section(name):
            data = dict(
                (option, self._cp.get(name, option))
                for option in self._cp.options(name))
        else:
            raise ValueError("No preset %r" % (name,))
        return self.preset_cls.from_dict(data)

    def set_preset(self, name, config):
        if self._cp.has_section(name):
            self._cp.remove_section(name)
        self._cp.add_section(name)
        for option in config:
            if config.is_set(option):
                self._cp.set(name, option, getattr(config, option))

    def load(self, fd):
        logger.debug("load(%r)", fd)
        try:
            filename = fd.name
        except AttributeError:
            filename = None
        result = self._cp.readfp(fd, filename)
        logger.debug("load -> %r", result)
        return

    def dump(self, fd):
        logger.debug("dump(%r)", fd)
        self._cp.write(fd)

    def loads(self, data):
        with io.StringIO(data) as fileobj:
            self.load(fileobj)

    def dumps(self):
        with io.StringIO() as fileobj:
            self.dump(fileobj)
            return fileobj.getvalue()


def get_config(filename=None):
    config = PushoverConfig()
    filenames = list(find_config(CONFIG_FILENAME))
    if filename:
        filenames.append(filename)
    for filename in filenames:
        logger.debug("loading config %r", filename)
        with io.open(filename, mode="r", encoding="utf-8") as fd:
            config.load(fd)
    return config


def validate_config(config):
    for preset in config.list_presets():
        preset = config.get_preset(preset)
        preset.validate()


#
# python -m pushover.config
#

def main(inargs=None):

    class Actions(object):
        """ subparser to function map. """
        def __init__(self):
            self.funcmap = dict()

        def __getitem__(self, key):
            return self.funcmap[key]

        def __call__(self, subparser):
            def wrapper(func):
                key = subparser.prog.split(" ")[-1]
                self.funcmap[key] = func
                return func
            return wrapper

    parser = argparse.ArgumentParser(description="pushover config utilities")
    cli_utils.add_version_arg(parser)

    log_params = parser.add_argument_group("Logging")
    cli_utils.add_verbosity_mutex(log_params)

    commands = parser.add_subparsers(title="commands", dest="command")
    actions = Actions()

    #
    # defaults [filename]
    #
    defaults_cmd = commands.add_parser(
        "defaults",
        help="dump the default configuration")
    defaults_cmd.add_argument(
        "output",
        type=argparse.FileType("w"),
        nargs="?",
        default="-",
        metavar="FILE",
        help="write config to %(metavar)s (default: stdout)")

    @actions(defaults_cmd)
    def write_default_config(args):
        # [DEFAULT]
        config = PushoverConfig()
        config.dump(args.output)

        # [example] (commented out)
        config.defaults.clear()
        config.set_preset("example", EXAMPLE_CONFIG)
        for line in config.dumps().splitlines(True):
            args.output.write("# " + line)

        args.output.flush()
        if args.output not in (sys.stdout, sys.stderr):
            args.output.close()

    #
    # locations
    #
    locations_cmd = commands.add_parser(
        "list-files",
        help="show configuration file locations",
    )
    locations_cmd.add_argument(
        "--only-existing",
        action="store_true",
        default=False,
        help="only list configuration files that are present")

    @actions(locations_cmd)
    def show_config_locations(args):
        if args.only_existing:
            locations = find_config(filename=CONFIG_FILENAME)
        else:
            locations = get_priority(filename=CONFIG_FILENAME)
        for filename in locations:
            print(filename)

    #
    # show
    #
    dump_cmd = commands.add_parser(
        "dump-config",
        help="show the effective configuration")
    dump_cmd.add_argument(
        "-c", "--config",
        default=None,
        metavar="FILE",
        help="Use config from %(metavar)s")
    dump_cmd.add_argument(
        "-v", "--validate",
        action="store_true",
        default=False,
        help="validate config")

    @actions(dump_cmd)
    def show_config(args):
        config = get_config(args.config)
        if args.validate:
            validate_config(config)
        config.dump(sys.stdout)
        sys.stdout.flush()

    #
    # list-presets
    #
    list_presets_cmd = commands.add_parser(
        "list-presets",
        help="show presets in the effective configuration")
    list_presets_cmd.add_argument(
        "-c", "--config",
        default=None,
        metavar="FILE",
        help="Use config from %(metavar)s")

    @actions(list_presets_cmd)
    def list_presets(args):
        config = get_config(args.config)
        for preset in config.list_presets():
            print(preset)

    #
    # show-preset
    #
    show_preset_cmd = commands.add_parser(
        "show-preset",
        help="show presets in the effective configuration")
    show_preset_cmd.add_argument(
        "-c", "--config",
        default=None,
        metavar="FILE",
        help="Use config from %(metavar)s")
    show_preset_cmd.add_argument(
        "preset",
        nargs="?",
        default=None,
        metavar="PRESET")

    @actions(show_preset_cmd)
    def show_preset(args):
        config = get_config(args.config)
        preset = config.get_preset(args.preset)
        for key in preset:
            value = getattr(preset, key)
            print("{key} = {value}".format(key=key, value=value))

    args = parser.parse_args()
    cli_utils.setup_logging(args.verbosity)
    actions[args.command](args)


if __name__ == "__main__":
    main()
