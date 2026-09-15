from datetime import timedelta

DOMAIN = "ps5_remoteplay"

CONF_CREDENTIALS = "credentials"
CONF_PASSCODE = "passcode"

SCAN_INTERVAL = timedelta(seconds=10)
STATUS_TIMEOUT = 3.0
# How long the switch keeps showing the requested state while the console catches up
PENDING_STATE_SECONDS = 60
