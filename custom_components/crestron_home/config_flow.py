"""Config flow for Crestron Home."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .api import CrestronHomeAuthError, CrestronHomeClient, CrestronHomeError
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_VOLUME_SCALE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VOLUME_SCALE,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    VOLUME_SCALE_PERCENT,
    VOLUME_SCALE_RAW,
)


class CrestronHomeConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, host: str, token: str) -> str | None:
        """Return an error key, or None if the credentials work."""
        client = CrestronHomeClient(async_create_clientsession(self.hass, verify_ssl=False), host, token)
        try:
            await client.login(force=True)
            await client.get_rooms()
        except CrestronHomeAuthError:
            return "invalid_auth"
        except CrestronHomeError:
            return "cannot_connect"
        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            if (error := await self._validate(host, user_input[CONF_TOKEN].strip())) is None:
                return self.async_create_entry(
                    title=f"Crestron Home ({host})",
                    data={CONF_HOST: host, CONF_TOKEN: user_input[CONF_TOKEN].strip()},
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str, vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            if (error := await self._validate(entry.data[CONF_HOST], token)) is None:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_TOKEN: token})
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return CrestronHomeOptionsFlow()


class CrestronHomeOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        opts = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=300)),
                    vol.Required(
                        CONF_VOLUME_SCALE, default=opts.get(CONF_VOLUME_SCALE, DEFAULT_VOLUME_SCALE)
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[VOLUME_SCALE_RAW, VOLUME_SCALE_PERCENT],
                            translation_key=CONF_VOLUME_SCALE,
                            mode=SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )
