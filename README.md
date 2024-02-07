# Pushover

This is a simple python script to send push notifications using the
[Pushover](https://pushover.net/) service.


## Configuration

The pushover config uses the Python `ConfigParser` format, and reads
the first configuration file found from:

1. `${XDG_CONFIG_HOME}/pushover/pushover.conf`
2. `${XDG_CONFIG_DIRS}/pushover/pushover.conf`


The configuration file can be structured into different sections.  The *DEFAULT*
section contains default settings, while all other sections are named *presets*
that can override the defaults.

In the following example, a single *pushover.net* client application is
configured in the *DEFAULT* section, while the *my-device* section limits the
recipient to a single, named device.

```conf
[DEFAULT]
api_url = https://api.pushover.net/1/messages.json
api_user = example-user
api_token = example-token
api_device

[my-device]
api_device = example-device
```

All configuration options can be overridden with command line options.
