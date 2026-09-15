import logging

from ps5_remoteplay import DeviceInfo as PS5Device
from ps5_remoteplay import PS5Error, get_device

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL, STATUS_TIMEOUT

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

    async def _async_update_data(self) -> PS5Device:
        try:
            return await get_device(self.host, timeout=STATUS_TIMEOUT)
        except (PS5Error, OSError) as err:
            raise UpdateFailed(f"PS5 at {self.host} did not respond: {err}") from err
