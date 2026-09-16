import logging
from datetime import datetime

from ps5_remoteplay import DeviceInfo as PS5Device
from ps5_remoteplay import PS5Error, get_device

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SCAN_INTERVAL, STATUS_TIMEOUT, UNAVAILABLE_AFTER

_LOGGER = logging.getLogger(__name__)

type PS5ConfigEntry = ConfigEntry[PS5Coordinator]


class PS5Coordinator(DataUpdateCoordinator[PS5Device]):
    config_entry: PS5ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: PS5ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.host: str = entry.data[CONF_HOST]
        self._last_answer: datetime | None = None

    async def _async_update_data(self) -> PS5Device:
        try:
            device = await get_device(self.host, timeout=STATUS_TIMEOUT)
        except (PS5Error, OSError) as err:
            if (
                self.data is not None
                and self._last_answer is not None
                and dt_util.utcnow() - self._last_answer < UNAVAILABLE_AFTER
            ):
                _LOGGER.debug("PS5 at %s did not answer (%s); keeping last known state", self.host, err)
                return self.data
            raise UpdateFailed(f"PS5 at {self.host} did not respond: {err}") from err
        self._last_answer = dt_util.utcnow()
        return device
