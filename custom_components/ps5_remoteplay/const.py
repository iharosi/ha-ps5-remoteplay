from datetime import timedelta

DOMAIN = "ps5_remoteplay"

CONF_CREDENTIALS = "credentials"
CONF_PASSCODE = "passcode"

SCAN_INTERVAL = timedelta(seconds=10)
STATUS_TIMEOUT = 3.0
# The console stops answering status queries for several seconds while it changes
# power state; only report it unavailable after it has been silent this long.
UNAVAILABLE_AFTER = timedelta(seconds=60)
# How long the switch keeps showing the requested state while the console catches up
PENDING_STATE_SECONDS = 60
