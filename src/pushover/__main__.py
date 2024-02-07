"""
Main pushover script.
"""
import argparse
import logging

import pushover
import pushover.cli_utils

logger = logging.getLogger(__name__)


def main(inargs=None):
    """ Script invoke. """

    parser = argparse.ArgumentParser(
        description="Send message using pushover.")

    if "__main__" in parser.prog:
        parser.prog = "python -m " + __package__

    pushover.cli_utils.add_version_arg(parser)

    # Arguments for add_option/add_argument
    # TODO: User/token key on command line?
    config_grp = parser.add_argument_group("Configuration")
    config_grp.add_argument(
        "-c", "--config",
        dest="config_file",
        default=None,
        help="read config from %(metavar)s",
        metavar="FILE",
    )
    config_grp.add_argument(
        "-p", "--preset",
        dest="preset",
        default=None,
        help="use the %(metavar)s section from config",
        metavar="PRESET",
    )

    # Add -q, -v, -vv, ...
    log_params = parser.add_argument_group("Logging")
    pushover.cli_utils.add_verbosity_mutex(log_params)

    opt_grp = parser.add_argument_group("API options")
    opt_grp.add_argument(
        "-u", "--url",
        dest="api_url",
        default=None,
        help="Override %(dest)s from config",
        metavar="URL",
    )
    opt_grp.add_argument(
        "-U", "--user",
        dest="api_user",
        default=None,
        help="Override %(dest)s from config",
        metavar="USER",
    )
    opt_grp.add_argument(
        "-T", "--token",
        dest="api_token",
        default=None,
        help="Override %(dest)s from config",
        metavar="TOKEN",
    )
    opt_grp.add_argument(
        "-d", "--device",
        dest="api_device",
        default=None,
        help="Override %(dest)s from config",
        metavar="DEVICE",
    )

    msg_grp = parser.add_argument_group("Message options")
    msg_grp.add_argument(
        "-t", "--msg-title",
        dest="title",
        help="set message title to %(metavar)s",
        metavar="TEXT",
    )
    msg_grp.add_argument(
        "--msg-url",
        dest="msg_url",
        help="include %(metavar)s in message",
        metavar="URL",
    )
    msg_grp.add_argument(
        "--msg-url-title",
        dest="msg_url_title",
        help="set title of the url to %(metavar)s",
        metavar="TEXT",
    )
    msg_grp.add_argument(
        "--msg-priority",
        dest="msg_priority",
        default=str(pushover.messages.DEFAULT_PRIORITY),
        choices=filter(str, pushover.messages.PRIORITIES),
        help="set the message priority, defaults to %(default)s",
    )
    msg_grp.add_argument(
        "message",
        nargs="+",
        metavar="TEXT",
    )

    args = parser.parse_args(inargs)
    pushover.cli_utils.setup_logging(args.verbosity)
    logger.debug("args: %r", args)

    data = pushover.send_message(args)
    logger.debug("response: %r", data)

    if (not data.get("status")) or data.get("status") != 1:
        for e in data.get("errors", ["no errors", ]):
            logger.error("%s", e)
        logger.error("message failed")
        raise SystemExit(1)
    else:
        logger.info("Sent message (%r)", data.get("request"))
        raise SystemExit(0)


if __name__ == "__main__":
    main()
