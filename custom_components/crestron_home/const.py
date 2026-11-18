"""Constants for the Crestron Home integration."""

DOMAIN = "crestron_home"
MANUFACTURER = "Crestron"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 5  # seconds
MIN_SCAN_INTERVAL = 2

# Fired when a Crestron scene goes from inactive to active (e.g. a keypad button
# or the Crestron app ran it). Use it as an automation trigger.
EVENT_SCENE_ACTIVATED = f"{DOMAIN}_scene_activated"

PLATFORMS = ["light", "lock", "scene"]
