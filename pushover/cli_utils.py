"""
CLI utils.

These utils makes the various executable modules and scripts in this package
behave similar.
"""
import logging

from . import metadata

logger = logging.getLogger(__name__)


LOG_FORMAT = "%(levelname)s - %(name)s - %(message)s"
LOG_VERBOSITY = (
    logging.ERROR,
    logging.WARNING,
    logging.INFO,
    logging.DEBUG,
)


def get_log_level(verbosity):
    """ Map veribosity to a log level. """
    verbosity_idx = max(0, min(len(LOG_VERBOSITY) - 1, verbosity))
    return LOG_VERBOSITY[verbosity_idx]


def setup_logging(verbosity):
    """
    configure logging from verbosity

    :param int verbosity:
        The verbosity level from cli arguments.
    """
    root = logging.getLogger()
    if root.handlers:
        # logging already configured
        return

    if verbosity < 0:
        root.addHandler(logging.NullHandler())
    else:
        level = get_log_level(int(verbosity))
        logging.basicConfig(format=LOG_FORMAT, level=level)


def add_verbosity_mutex(arg_parser, dest="verbosity"):
    """
    add verbosity arguments (-v, -q)

    :param arg_parser: parser or argument group
    :param str dest: name of the argument
    """
    # verbosity: -v, -vv, -vvv, -q
    log_args = arg_parser.add_mutually_exclusive_group()
    log_args.add_argument(
        "-v",
        action="count",
        dest=dest,
        help="increase verbosity (debug output/logging)",
    )
    log_args.add_argument(
        "-q",
        action="store_const",
        const=-1,
        dest=dest,
        help="silent mode - disables logging/debug output",
    )
    log_args.set_defaults(**{dest: 0})
    return log_args


def add_version_arg(arg_parser):
    """
    add a version argument (--version)

    :param arg_parser: parser or argument group
    """
    return arg_parser.add_argument(
        '--version',
        action='version',
        version='%s %s' % (metadata.package, metadata.version),
    )
