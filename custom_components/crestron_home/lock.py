"""Crestron Home door locks."""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CrestronHomeError
from .coordinator import CrestronHomeCoordinator
from .entity import CrestronHomeEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CrestronHomeCoordinator = entry.runtime_data
    async_add_entities(CrestronHomeLock(coordinator, lid) for lid in coordinator.data.locks)


class CrestronHomeLock(CrestronHomeEntity, LockEntity):
    _attr_name = None

    def __init__(self, coordinator: CrestronHomeCoordinator, lock_id: int) -> None:
        super().__init__(coordinator, "locks", lock_id)
        self._attr_device_info = self._device_info_for(coordinator.data.locks[lock_id], "Door lock")

    @property
    def _status(self) -> str:
        item = self._item
        return str(item.get("status") or "").strip().lower() if item else ""

    @property
    def is_locked(self) -> bool | None:
        # Crestron reports "Locked", "Unlocked", or "" when the lock didn't confirm
        # (e.g. jammed bolt). Treat "" as unknown rather than guessing.
        status = self._status
        if status == "locked":
            return True
        if status == "unlocked":
            return False
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        item = self._item or {}
        return {"crestron_status": item.get("status"), "crestron_id": self._item_id}

    async def _run(self, action) -> None:
        try:
            await action(self._item_id)
        except CrestronHomeError as err:
            raise HomeAssistantError(f"Crestron lock command failed: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_lock(self, **kwargs: Any) -> None:
        await self._run(self.coordinator.client.lock)

    async def async_unlock(self, **kwargs: Any) -> None:
        await self._run(self.coordinator.client.unlock)
