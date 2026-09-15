import logging
from importlib.metadata import PackageNotFoundError, version

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import PS5ConfigEntry, PS5Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: PS5ConfigEntry) -> bool:
    try:
        _LOGGER.debug("Using ps5-remoteplay %s", version("ps5-remoteplay"))
    except PackageNotFoundError:
        _LOGGER.debug("ps5-remoteplay version is unknown")
    coordinator = PS5Coordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PS5ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
