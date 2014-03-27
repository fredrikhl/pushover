# Pushover

This is a simple python script to send push notifications using the service
[Pushover](https://pushover.net/).


## Configuration

For now, configuration is done by using a simple file, containing "key = value"
pairs. This file should at least contain:

    token = <your pushover api token>
    user  = <your pushover user key>

This file can be stored as `${HOME}/.pushoverrc` or given as a command line
option.


