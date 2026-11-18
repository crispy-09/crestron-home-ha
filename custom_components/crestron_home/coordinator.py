"""Polling coordinator for Crestron Home."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CrestronHomeAuthError, CrestronHomeClient, CrestronHomeError
from .const import DOMAIN, EVENT_SCENE_ACTIVATED

_LOGGER = logging.getLogger(__name__)


@dataclass
class CrestronHomeData:
    rooms: dict[int, str] = field(default_factory=dict)
    lights: dict[int, dict] = field(default_factory=dict)
    scenes: dict[int, dict] = field(default_factory=dict)
    locks: dict[int, dict] = field(default_factory=dict)
    media: dict[int, dict] = field(default_factory=dict)


class CrestronHomeCoordinator(DataUpdateCoordinator[CrestronHomeData]):
    """Fetches all Crestron Home state in one pass."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: CrestronHomeClient, interval: int
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.client = client

    async def _async_update_data(self) -> CrestronHomeData:
        try:
            rooms = await self.client.get_rooms()
            lights = await self.client.get_lights()
            scenes = await self.client.get_scenes()
            locks = await self.client.get_door_locks()
            media = await self.client.get_media_rooms()
        except CrestronHomeAuthError as err:
            raise ConfigEntryAuthFailed(
                "Crestron Home rejected the API token. Firmware updates can reset it; "
                "copy the current token from the Crestron Home setup app."
            ) from err
        except CrestronHomeError as err:
            raise UpdateFailed(str(err)) from err

        new = CrestronHomeData(
            rooms={r["id"]: r.get("name", "") for r in rooms},
            lights={x["id"]: x for x in lights},
            scenes={x["id"]: x for x in scenes},
            locks={x["id"]: x for x in locks},
            media={x["id"]: x for x in media},
        )

        # Fire an event for every scene that just became active.
        if self.data is not None:
            for sid, scene in new.scenes.items():
                old = self.data.scenes.get(sid)
                if scene.get("status") and old is not None and not old.get("status"):
                    self.hass.bus.async_fire(
                        EVENT_SCENE_ACTIVATED,
                        {
                            "scene_id": sid,
                            "name": scene.get("name"),
                            "room": new.rooms.get(scene.get("roomId"), ""),
                            "type": scene.get("type"),
                        },
                    )
        return new
