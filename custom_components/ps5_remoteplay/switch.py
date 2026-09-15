from datetime import datetime, timedelta
from typing import Any

from ps5_remoteplay import (
    Credentials,
    DeviceStatus,
    PasscodeMismatch,
    PasscodeRequired,
    PS5Error,
    RemotePlayHttpError,
    standby,
    wake,
)

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_CREDENTIALS, CONF_PASSCODE, DOMAIN, PENDING_STATE_SECONDS
from .coordinator import PS5ConfigEntry, PS5Coordinator

PARALLEL_UPDATES = 1

# Other refusals, like 80108b10 (already in use), don't mean the pairing is invalid
_REASON_INVALID_ACCOUNT = "80108b02"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PS5ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([PS5PowerSwitch(entry.runtime_data)])


class PS5PowerSwitch(CoordinatorEntity[PS5Coordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: PS5Coordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = entry.unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=coordinator.data.name,
            manufacturer="Sony Interactive Entertainment",
            model="PlayStation 5",
            sw_version=coordinator.data.system_version,
        )
        self._pending_state: bool | None = None
        self._pending_until: datetime | None = None

    @property
    def _console_on(self) -> bool:
        return self.coordinator.data.status == DeviceStatus.AWAKE

    @property
    def is_on(self) -> bool:
        if self._pending_state is not None:
            return self._pending_state
        return self._console_on

    @callback
    def _handle_coordinator_update(self) -> None:
        if self._pending_state is not None and (
            self._pending_state == self._console_on or dt_util.utcnow() > self._pending_until
        ):
            self._pending_state = None
        super()._handle_coordinator_update()

    def _set_pending(self, state: bool) -> None:
        # The console needs 10-30s to report a new status; don't flip the switch back meanwhile.
        self._pending_state = state
        self._pending_until = dt_util.utcnow() + timedelta(seconds=PENDING_STATE_SECONDS)
        self.async_write_ha_state()

    @property
    def _credentials(self) -> Credentials:
        return Credentials.from_dict(self.coordinator.config_entry.data[CONF_CREDENTIALS])

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await wake(self.coordinator.host, self._credentials)
        except (PS5Error, OSError) as err:
            raise HomeAssistantError(f"Could not wake the PS5: {err}") from err
        self._set_pending(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        entry = self.coordinator.config_entry
        try:
            await standby(
                self.coordinator.host,
                self._credentials,
                passcode=entry.options.get(CONF_PASSCODE) or None,
            )
        except PasscodeRequired as err:
            raise HomeAssistantError(
                "The PS5 asked for a passcode; set it in the integration's options"
            ) from err
        except PasscodeMismatch as err:
            raise HomeAssistantError(
                "The PS5 rejected the passcode set in the integration's options"
            ) from err
        except RemotePlayHttpError as err:
            if (err.reason_code or "").lower() == _REASON_INVALID_ACCOUNT:
                entry.async_start_reauth(self.hass)
            raise HomeAssistantError(f"Could not put the PS5 into standby: {err}") from err
        except (PS5Error, OSError) as err:
            raise HomeAssistantError(f"Could not put the PS5 into standby: {err}") from err
        self._set_pending(False)
        await self.coordinator.async_request_refresh()
