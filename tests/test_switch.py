from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from ps5_remoteplay import DeviceNotFound, DeviceStatus, PasscodeRequired, RemotePlayHttpError

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.ps5_remoteplay.const import CONF_PASSCODE, DOMAIN

from .conftest import CREDENTIALS, HOST, make_device, make_entry

ENTITY_ID = "switch.ps5_497"
COORDINATOR = "custom_components.ps5_remoteplay.coordinator.get_device"
SWITCH = "custom_components.ps5_remoteplay.switch"


async def _setup(hass: HomeAssistant, status: DeviceStatus, options=None):
    entry = make_entry(options)
    entry.add_to_hass(hass)
    get_device = AsyncMock(return_value=make_device(status))
    patcher = patch(COORDINATOR, get_device)
    patcher.start()
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, get_device, patcher


@pytest.fixture
def stop_patches():
    patchers = []
    yield patchers
    for p in patchers:
        p.stop()


async def test_state_follows_console(hass: HomeAssistant, stop_patches) -> None:
    entry, get_device, patcher = await _setup(hass, DeviceStatus.STANDBY)
    stop_patches.append(patcher)
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(ENTITY_ID).state == STATE_OFF

    get_device.return_value = make_device(DeviceStatus.AWAKE)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=11))
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == STATE_ON

    get_device.side_effect = DeviceNotFound("gone")
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=22))
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == STATE_UNAVAILABLE


async def test_turn_on_wakes_and_stays_on_while_booting(hass: HomeAssistant, stop_patches, freezer) -> None:
    _, get_device, patcher = await _setup(hass, DeviceStatus.STANDBY)
    stop_patches.append(patcher)

    with patch(f"{SWITCH}.wake", AsyncMock()) as wake:
        await hass.services.async_call("switch", "turn_on", {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True)
    assert wake.await_args.args == (HOST, CREDENTIALS)
    # console still reports standby, but the switch should not flip back yet
    freezer.tick(timedelta(seconds=11))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == STATE_ON

    # after the grace period, the real status wins
    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == STATE_OFF


async def test_turn_off_uses_passcode(hass: HomeAssistant, stop_patches) -> None:
    _, _, patcher = await _setup(hass, DeviceStatus.AWAKE, options={CONF_PASSCODE: "1234"})
    stop_patches.append(patcher)

    with patch(f"{SWITCH}.standby", AsyncMock(return_value=True)) as standby:
        await hass.services.async_call("switch", "turn_off", {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True)
    standby.assert_awaited_once_with(HOST, CREDENTIALS, passcode="1234")
    assert hass.states.get(ENTITY_ID).state == STATE_OFF


async def test_turn_off_errors(hass: HomeAssistant, stop_patches) -> None:
    _, _, patcher = await _setup(hass, DeviceStatus.AWAKE)
    stop_patches.append(patcher)

    with patch(f"{SWITCH}.standby", AsyncMock(side_effect=PasscodeRequired("x"))):
        with pytest.raises(HomeAssistantError, match="passcode"):
            await hass.services.async_call("switch", "turn_off", {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True)
    assert hass.states.get(ENTITY_ID).state == STATE_ON

    with patch(f"{SWITCH}.standby", AsyncMock(side_effect=RemotePlayHttpError(403, "80108b10"))):
        with pytest.raises(HomeAssistantError, match="already in use"):
            await hass.services.async_call("switch", "turn_off", {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True)
    await hass.async_block_till_done()
    assert hass.config_entries.flow.async_progress_by_handler(DOMAIN) == []

    with patch(f"{SWITCH}.standby", AsyncMock(side_effect=RemotePlayHttpError(403, "80108B02"))):
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call("switch", "turn_off", {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True)
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [f["context"]["source"] for f in flows] == [SOURCE_REAUTH]


async def test_setup_retries_when_console_unreachable(hass: HomeAssistant) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    with patch(COORDINATOR, AsyncMock(side_effect=DeviceNotFound("gone"))):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
