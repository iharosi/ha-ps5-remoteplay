import logging
from typing import Any

import aiohttp
import voluptuous as vol
from ps5_remoteplay import (
    DeviceStatus,
    OAuthError,
    PS5Error,
    RemotePlayHttpError,
    account_id_from_redirect,
    get_device,
    login_url,
    register,
)

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_CREDENTIALS, CONF_PASSCODE, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_REDIRECT_URL = "redirect_url"
CONF_PIN = "pin"

# RP-Application-Reason the console sends for a wrong Link Device PIN
_INVALID_PIN_REASON = "80108b09"


class PS5ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._name: str | None = None
        self._account_id: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "PS5OptionsFlow":
        return PS5OptionsFlow()

    async def _awake_device(self, host: str, errors: dict[str, str]):
        try:
            device = await get_device(host)
        except (PS5Error, OSError):
            errors["base"] = "cannot_connect"
            return None
        if device.status != DeviceStatus.AWAKE:
            errors["base"] = "not_awake"
            return None
        return device

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            if device := await self._awake_device(host, errors):
                await self.async_set_unique_id(device.id)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                self._host, self._name = host, device.name
                return await self.async_step_auth()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )

    async def async_step_auth(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                self._account_id = await account_id_from_redirect(
                    user_input[CONF_REDIRECT_URL], async_get_clientsession(self.hass)
                )
            except OAuthError as err:
                _LOGGER.debug("PSN sign-in failed: %s", err)
                errors["base"] = "invalid_redirect"
            except aiohttp.ClientError:
                errors["base"] = "psn_unreachable"
            else:
                return await self.async_step_link()

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema({vol.Required(CONF_REDIRECT_URL): str}),
            description_placeholders={"login_url": login_url()},
            errors=errors,
        )

    async def async_step_link(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                credentials = await register(self._host, self._account_id, user_input[CONF_PIN])
            except ValueError:
                errors[CONF_PIN] = "invalid_pin"
            except RemotePlayHttpError as err:
                _LOGGER.debug("Registration rejected: %s", err)
                if (err.reason_code or "").lower() == _INVALID_PIN_REASON:
                    errors[CONF_PIN] = "invalid_pin"
                else:
                    errors["base"] = "registration_failed"
            except PS5Error as err:
                _LOGGER.debug("Registration failed: %s", err)
                errors["base"] = "link_not_open"
            except OSError:
                errors["base"] = "cannot_connect"
            else:
                data = {CONF_HOST: self._host, CONF_CREDENTIALS: credentials.to_dict()}
                if self.source == SOURCE_REAUTH:
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(), data_updates=data
                    )
                return self.async_create_entry(title=self._name, data=data)

        return self.async_show_form(
            step_id="link",
            data_schema=vol.Schema({vol.Required(CONF_PIN): str}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        self._host, self._name = entry.data[CONF_HOST], entry.title
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None and await self._awake_device(self._host, errors):
            return await self.async_step_auth()

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={"name": self._name},
            errors=errors,
        )


class PS5OptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            passcode = user_input.get(CONF_PASSCODE, "").strip()
            if passcode and not (len(passcode) == 4 and passcode.isdigit()):
                errors[CONF_PASSCODE] = "invalid_passcode"
            else:
                return self.async_create_entry(data={CONF_PASSCODE: passcode})

        schema = vol.Schema(
            {
                vol.Optional(CONF_PASSCODE): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                )
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, self.config_entry.options),
            errors=errors,
        )
