"""Crestron Home integration (local REST API)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import CrestronHomeClient
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, MANUFACTURER, PLATFORMS
from .coordinator import CrestronHomeCoordinator

type CrestronHomeConfigEntry = ConfigEntry[CrestronHomeCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: CrestronHomeConfigEntry) -> bool:
    # Processors use a self-signed certificate.
    session = async_create_clientsession(hass, verify_ssl=False)
    client = CrestronHomeClient(session, entry.data[CONF_HOST], entry.data[CONF_TOKEN])
    interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = CrestronHomeCoordinator(hass, entry, client, interval)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # Hub device that every Crestron device hangs off.
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Crestron Home",
        manufacturer=MANUFACTURER,
        model="Crestron Home processor",
        sw_version=client.api_version,
        configuration_url=f"https://{entry.data[CONF_HOST]}",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: CrestronHomeConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: CrestronHomeConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
