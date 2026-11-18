"""Constants for the Crestron Home integration."""

DOMAIN = "crestron_home"
MANUFACTURER = "Crestron"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 5  # seconds
MIN_SCAN_INTERVAL = 2

# How the processor expects media room volume to be *set*. Crestron's docs say
# percent (0-100), but some processors (e.g. MC4-R fw 2.8000) take 0-65535,
# the same scale they report. Configurable in the integration's options.
CONF_VOLUME_SCALE = "volume_scale"
VOLUME_SCALE_RAW = "raw"
VOLUME_SCALE_PERCENT = "percent"
DEFAULT_VOLUME_SCALE = VOLUME_SCALE_RAW

# Fired when a Crestron scene goes from inactive to active (e.g. a keypad button
# or the Crestron app ran it). Use it as an automation trigger.
EVENT_SCENE_ACTIVATED = f"{DOMAIN}_scene_activated"

PLATFORMS = ["light", "lock", "media_player", "scene"]
