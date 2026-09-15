from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from ps5_remoteplay import DeviceNotFound, DeviceStatus, OAuthError, PS5Error, RemotePlayHttpError

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ps5_remoteplay.const import CONF_CREDENTIALS, CONF_PASSCODE, DOMAIN

from .conftest import CREDENTIALS, DEVICE_ID, HOST, make_device, make_entry

FLOW = "custom_components.ps5_remoteplay.config_flow"


@pytest.fixture(autouse=True)
def mock_network_and_setup():
    with (
        patch(f"{FLOW}.async_get_clientsession"),
        patch("custom_components.ps5_remoteplay.async_setup_entry", AsyncMock(return_value=True)),
    ):
        yield
REDIRECT = "https://remoteplay.dl.playstation.net/remoteplay/redirect?code=abc"


async def _start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})


async def test_full_flow(hass: HomeAssistant) -> None:
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"

    with (
        patch(f"{FLOW}.get_device", AsyncMock(return_value=make_device())),
        patch(f"{FLOW}.account_id_from_redirect", AsyncMock(return_value="AAAAAAAAAEI=")) as oauth,
        patch(f"{FLOW}.register", AsyncMock(return_value=CREDENTIALS)) as register,
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: f" {HOST} "})
        assert result["step_id"] == "auth"
        assert "oauth/authorize" in result["description_placeholders"]["login_url"]

        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"redirect_url": REDIRECT})
        assert result["step_id"] == "link"
        assert oauth.await_args.args[0] == REDIRECT

        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"pin": "12345678"})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "PS5-497"
    assert result["result"].unique_id == DEVICE_ID
    assert result["data"] == {CONF_HOST: HOST, CONF_CREDENTIALS: CREDENTIALS.to_dict()}
    register.assert_awaited_once_with(HOST, "AAAAAAAAAEI=", "12345678")


async def test_user_step_errors(hass: HomeAssistant) -> None:
    result = await _start(hass)
    with patch(f"{FLOW}.get_device", AsyncMock(side_effect=DeviceNotFound("nope"))):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["errors"] == {"base": "cannot_connect"}

    with patch(f"{FLOW}.get_device", AsyncMock(return_value=make_device(DeviceStatus.STANDBY))):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["errors"] == {"base": "not_awake"}


async def test_auth_and_link_errors(hass: HomeAssistant) -> None:
    result = await _start(hass)
    with patch(f"{FLOW}.get_device", AsyncMock(return_value=make_device())):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})

    for error, expected in ((OAuthError("bad"), "invalid_redirect"), (aiohttp.ClientError(), "psn_unreachable")):
        with patch(f"{FLOW}.account_id_from_redirect", AsyncMock(side_effect=error)):
            result = await hass.config_entries.flow.async_configure(result["flow_id"], {"redirect_url": REDIRECT})
        assert result["step_id"] == "auth" and result["errors"] == {"base": expected}

    with patch(f"{FLOW}.account_id_from_redirect", AsyncMock(return_value="AAAAAAAAAEI=")):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"redirect_url": REDIRECT})

    cases = (
        (RemotePlayHttpError(403, "80108B09"), {"pin": "invalid_pin"}),
        (ValueError("PIN must be numeric"), {"pin": "invalid_pin"}),
        (RemotePlayHttpError(403, "80108b10"), {"base": "registration_failed"}),
        (PS5Error("no answer"), {"base": "link_not_open"}),
        (OSError("unreachable"), {"base": "cannot_connect"}),
    )
    for error, expected in cases:
        with patch(f"{FLOW}.register", AsyncMock(side_effect=error)):
            result = await hass.config_entries.flow.async_configure(result["flow_id"], {"pin": "1234"})
        assert result["step_id"] == "link" and result["errors"] == expected

    with patch(f"{FLOW}.register", AsyncMock(return_value=CREDENTIALS)):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"pin": "12345678"})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_already_configured_updates_host(hass: HomeAssistant) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    result = await _start(hass)
    with patch(f"{FLOW}.get_device", AsyncMock(return_value=make_device())):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: "10.12.12.99"})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "10.12.12.99"


async def test_reauth(hass: HomeAssistant) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    new_credentials = CREDENTIALS.to_dict() | {"user-credential": "42"}

    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    with patch(f"{FLOW}.get_device", AsyncMock(return_value=make_device(DeviceStatus.STANDBY))):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"base": "not_awake"}

    with (
        patch(f"{FLOW}.get_device", AsyncMock(return_value=make_device())),
        patch(f"{FLOW}.account_id_from_redirect", AsyncMock(return_value="AAAAAAAAAEI=")),
        patch(f"{FLOW}.register", AsyncMock(return_value=type(CREDENTIALS).from_dict(new_credentials))),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"redirect_url": REDIRECT})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"pin": "12345678"})

    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reauth_successful"
    assert entry.data[CONF_CREDENTIALS]["user-credential"] == "42"


async def test_options_passcode(hass: HomeAssistant) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_PASSCODE: "12a4"})
    assert result["errors"] == {CONF_PASSCODE: "invalid_passcode"}

    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_PASSCODE: "1234"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_PASSCODE: "1234"}
