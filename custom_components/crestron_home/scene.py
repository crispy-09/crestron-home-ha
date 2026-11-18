"""Crestron Home scenes."""

from __future__ import annotations

from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CrestronHomeError
from .const import DOMAIN, MANUFACTURER
from .coordinator import CrestronHomeCoordinator
from .entity import CrestronHomeEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CrestronHomeCoordinator = entry.runtime_data
    async_add_entities(CrestronHomeScene(coordinator, sid) for sid in coordinator.data.scenes)


class CrestronHomeScene(CrestronHomeEntity, Scene):
    """A Crestron scene. Grouped under one HA device per Crestron room."""

    def __init__(self, coordinator: CrestronHomeCoordinator, scene_id: int) -> None:
        super().__init__(coordinator, "scenes", scene_id)
        item = coordinator.data.scenes[scene_id]
        self._attr_name = item.get("name")
        room_id = item.get("roomId")
        room = coordinator.data.rooms.get(room_id, "Crestron Home")
        entry_id = coordinator.config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_room_{room_id}")},
            name=f"{room} Scenes",
            manufacturer=MANUFACTURER,
            model="Crestron Home room",
            suggested_area=room if room_id != 1001 else None,  # 1001 = "Whole House"
            via_device=(DOMAIN, entry_id),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        item = self._item or {}
        return {
            "active": bool(item.get("status")),
            "crestron_type": item.get("type"),
            "crestron_id": self._item_id,
        }

    async def async_activate(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.client.recall_scene(self._item_id)
        except CrestronHomeError as err:
            raise HomeAssistantError(f"Failed to recall scene: {err}") from err
        await self.coordinator.async_request_refresh()
