import logging

import ps5_remoteplay

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import PS5ConfigEntry, PS5Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: PS5ConfigEntry) -> bool:
    _LOGGER.debug(
        "Using ps5-remoteplay %s from %s",
        getattr(ps5_remoteplay, "__version__", "unknown"),
        ps5_remoteplay.__file__,
    )
    coordinator = PS5Coordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PS5ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
