"""Crestron Home lights (native Crestron dimmers/switches)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_TRANSITION, ColorMode, LightEntity, LightEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CrestronHomeError
from .coordinator import CrestronHomeCoordinator
from .entity import CrestronHomeEntity

MAX_LEVEL = 65535


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CrestronHomeCoordinator = entry.runtime_data
    async_add_entities(CrestronHomeLight(coordinator, lid) for lid in coordinator.data.lights)


class CrestronHomeLight(CrestronHomeEntity, LightEntity):
    _attr_name = None  # use the device name

    def __init__(self, coordinator: CrestronHomeCoordinator, light_id: int) -> None:
        super().__init__(coordinator, "lights", light_id)
        item = coordinator.data.lights[light_id]
        self._dimmable = str(item.get("subType", "")).lower() == "dimmer"
        mode = ColorMode.BRIGHTNESS if self._dimmable else ColorMode.ONOFF
        self._attr_color_mode = mode
        self._attr_supported_color_modes = {mode}
        if self._dimmable:
            self._attr_supported_features = LightEntityFeature.TRANSITION
        self._attr_device_info = self._device_info_for(item, item.get("subType") or "Light")

    @property
    def is_on(self) -> bool | None:
        item = self._item
        return None if item is None else item.get("level", 0) > 0

    @property
    def brightness(self) -> int | None:
        item = self._item
        if item is None or not self._dimmable:
            return None
        return round(item.get("level", 0) * 255 / MAX_LEVEL)

    async def _set(self, level: int, transition: float | None = None) -> None:
        fade_ms = int((transition or 0) * 1000)
        try:
            await self.coordinator.client.set_light_level(self._item_id, level, fade_ms)
        except CrestronHomeError as err:
            raise HomeAssistantError(f"Failed to set {self.entity_id}: {err}") from err
        self._item["level"] = level  # optimistic until next poll
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self._dimmable and ATTR_BRIGHTNESS in kwargs:
            level = round(kwargs[ATTR_BRIGHTNESS] * MAX_LEVEL / 255)
        else:
            level = MAX_LEVEL
        await self._set(level, kwargs.get(ATTR_TRANSITION))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(0, kwargs.get(ATTR_TRANSITION))
