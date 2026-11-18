"""Crestron Home media rooms: power, source selection, and (where Crestron controls it) volume/mute."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CrestronHomeError
from .const import CONF_VOLUME_SCALE, DEFAULT_VOLUME_SCALE, VOLUME_SCALE_PERCENT
from .coordinator import CrestronHomeCoordinator
from .entity import CrestronHomeEntity

# Volume is always reported as 0-65535; the scale used to set it is an option.
MAX_LEVEL = 65535


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CrestronHomeCoordinator = entry.runtime_data
    async_add_entities(CrestronHomeMediaRoom(coordinator, mid) for mid in coordinator.data.media)


def _has(controls: list | None) -> bool:
    return any(str(c).lower() != "none" for c in controls or [])


class CrestronHomeMediaRoom(CrestronHomeEntity, MediaPlayerEntity):
    _attr_name = None
    _attr_volume_step = 0.02

    def __init__(self, coordinator: CrestronHomeCoordinator, room_id: int) -> None:
        super().__init__(coordinator, "media", room_id)
        item = coordinator.data.media[room_id]
        info = self._device_info_for(item, "Media room")
        info["name"] = f"{item.get('name')} Media"
        self._attr_device_info = info

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        # Crestron only reports volume/mute controls while a source is active
        # (e.g. a receiver behind the source), so evaluate this on every update.
        item = self._item or {}
        features = (
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )
        if _has(item.get("availableVolumeControls")):
            features |= MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP
        if _has(item.get("availableMuteControls")):
            features |= MediaPlayerEntityFeature.VOLUME_MUTE
        return features

    @property
    def _sources(self) -> dict[str, int]:
        item = self._item or {}
        return {s.get("sourceName"): s.get("id") for s in item.get("availableSources") or []}

    @property
    def state(self) -> MediaPlayerState | None:
        item = self._item
        if item is None:
            return None
        return MediaPlayerState.ON if str(item.get("currentPowerState", "")).lower() == "on" else MediaPlayerState.OFF

    @property
    def source_list(self) -> list[str]:
        return list(self._sources)

    @property
    def source(self) -> str | None:
        current = (self._item or {}).get("currentSourceId")
        return next((name for name, sid in self._sources.items() if sid == current), None)

    @property
    def volume_level(self) -> float | None:
        item = self._item
        if not item or not self.supported_features & MediaPlayerEntityFeature.VOLUME_SET:
            return None
        return max(0.0, min(1.0, item.get("currentVolumeLevel", 0) / MAX_LEVEL))

    @property
    def is_volume_muted(self) -> bool | None:
        item = self._item
        if not item or not self.supported_features & MediaPlayerEntityFeature.VOLUME_MUTE:
            return None
        return str(item.get("currentMuteState", "")).lower() == "muted"

    async def _run(self, coro) -> None:
        try:
            await coro
        except CrestronHomeError as err:
            raise HomeAssistantError(f"Crestron media command failed: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        await self._run(self.coordinator.client.media_power(self._item_id, True))

    async def async_turn_off(self) -> None:
        await self._run(self.coordinator.client.media_power(self._item_id, False))

    async def async_select_source(self, source: str) -> None:
        if source not in self._sources:
            raise ServiceValidationError(f"Unknown source '{source}'. Options: {', '.join(self._sources)}")
        await self._run(self.coordinator.client.media_select_source(self._item_id, self._sources[source]))

    async def async_set_volume_level(self, volume: float) -> None:
        volume = max(0.0, min(1.0, volume))
        level = round(volume * MAX_LEVEL)
        scale = self.coordinator.config_entry.options.get(CONF_VOLUME_SCALE, DEFAULT_VOLUME_SCALE)
        sent = round(volume * 100) if scale == VOLUME_SCALE_PERCENT else level
        await self._run(self.coordinator.client.media_volume(self._item_id, sent))
        if self._item is not None:
            self._item["currentVolumeLevel"] = level  # optimistic, so rapid taps keep stepping
            self.async_write_ha_state()

    async def async_mute_volume(self, mute: bool) -> None:
        await self._run(self.coordinator.client.media_mute(self._item_id, mute))
