"""Shared entity base for Crestron Home."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import CrestronHomeCoordinator


class CrestronHomeEntity(CoordinatorEntity[CrestronHomeCoordinator]):
    """An entity backed by one Crestron Home device or scene."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CrestronHomeCoordinator, kind: str, item_id: int) -> None:
        super().__init__(coordinator)
        self._kind = kind
        self._item_id = item_id
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{kind}_{item_id}"

    @property
    def _item(self) -> dict | None:
        return getattr(self.coordinator.data, self._kind).get(self._item_id)

    @property
    def available(self) -> bool:
        item = self._item
        if not super().available or item is None:
            return False
        return item.get("connectionStatus", "online") != "offline"

    def _room_name(self, item: dict) -> str:
        return self.coordinator.data.rooms.get(item.get("roomId"), "")

    def _device_info_for(self, item: dict, model: str) -> DeviceInfo:
        """One HA device per Crestron device, placed in its Crestron room."""
        entry_id = self.coordinator.config_entry.entry_id
        return DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{self._kind}_{self._item_id}")},
            name=item.get("name"),
            manufacturer=MANUFACTURER,
            model=model,
            suggested_area=self._room_name(item) or None,
            via_device=(DOMAIN, entry_id),
        )
