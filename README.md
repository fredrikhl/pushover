# Pushover

This is a simple python script to send push notifications using the
[Pushover](https://pushover.net/) service.


## Configuration

The pushover config uses the Python `ConfigParser` format, and reads
configuration files in order from:

1. `${XDG_DATA_DIRS}/pushover/pushover.conf`
2. `${XDG_CONFIG_DIRS}/pushover/pushover.conf`
3. `${XDG_CONFIG_HOME}/pushover/pushover.conf`

... which means that anything set in the latter configuration files will
override settings from previous ones.

In addition, the configuration files operates with 'presets', so that multiple
accounts or multiple devices can be used in parallell. Given the following
configuration:

```conf
[DEFAULT]
api_url = https://api.pushover.net/1/messages.json
api_user = example-user
api_token = example-token
api_device

[my-device]
api_device = example-device
```

pushover will send to all devices by default, but if the preset `"my-device"` is
selected, it will only send to the device `"example-device"`.

All configuration options can be replaced with command line options.
