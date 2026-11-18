"""Minimal async client for the Crestron Home local REST API (/cws/api)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import aiohttp

# Crestron sessions expire after 10 minutes; refresh a bit before that.
SESSION_TTL = 9 * 60
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


class CrestronHomeError(Exception):
    """Generic API / connection error."""


class CrestronHomeAuthError(CrestronHomeError):
    """The API token was rejected (e.g. regenerated, or reset by a firmware update)."""


class CrestronHomeClient:
    """Talks to a Crestron Home processor."""

    def __init__(self, session: aiohttp.ClientSession, host: str, token: str) -> None:
        self._session = session
        self._base = f"https://{host}/cws/api"
        self._token = token
        self._authkey: str | None = None
        self._login_at = 0.0
        self._lock = asyncio.Lock()
        self.api_version: str | None = None

    async def login(self, force: bool = False) -> None:
        async with self._lock:
            if not force and self._authkey and time.monotonic() - self._login_at < SESSION_TTL:
                return
            try:
                async with self._session.get(
                    f"{self._base}/login",
                    headers={"Crestron-RestAPI-AuthToken": self._token, "Accept": "application/json"},
                    ssl=False,
                    timeout=REQUEST_TIMEOUT,
                ) as resp:
                    if resp.status in (401, 403):
                        raise CrestronHomeAuthError("API token rejected")
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
            except CrestronHomeAuthError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
                raise CrestronHomeError(f"Login failed: {err}") from err
            authkey = data.get("authkey") if isinstance(data, dict) else None
            if not authkey:
                raise CrestronHomeAuthError("Login response had no authkey")
            self._authkey = authkey
            self._login_at = time.monotonic()
            self.api_version = data.get("version")

    async def _request(self, method: str, path: str, body: Any = None, _retry: bool = True) -> Any:
        await self.login()
        kwargs: dict[str, Any] = {
            "headers": {"Crestron-RestAPI-AuthKey": self._authkey or "", "Accept": "application/json"},
            "ssl": False,
            "timeout": REQUEST_TIMEOUT,
        }
        if method == "POST":
            # The processor rejects POSTs without a body (HTTP 411).
            kwargs["json"] = body if body is not None else {}
        try:
            async with self._session.request(method, f"{self._base}{path}", **kwargs) as resp:
                if resp.status in (401, 403):
                    if _retry:
                        self._authkey = None
                        return await self._request(method, path, body, _retry=False)
                    raise CrestronHomeAuthError("Session rejected after re-login")
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise CrestronHomeError(f"{method} {path} failed: {err}") from err
        if isinstance(data, dict) and data.get("status") == "failure":
            raise CrestronHomeError(f"{method} {path}: {data.get('errorMessage') or 'failure'}")
        return data

    # --- reads -------------------------------------------------------------

    async def get_rooms(self) -> list[dict]:
        return (await self._request("GET", "/rooms")).get("rooms", [])

    async def get_lights(self) -> list[dict]:
        return (await self._request("GET", "/lights")).get("lights", [])

    async def get_scenes(self) -> list[dict]:
        return (await self._request("GET", "/scenes")).get("scenes", [])

    async def get_door_locks(self) -> list[dict]:
        try:
            return (await self._request("GET", "/doorlocks")).get("doorLocks", [])
        except CrestronHomeAuthError:
            raise
        except CrestronHomeError:
            return []  # older firmware may not expose this endpoint

    async def get_media_rooms(self) -> list[dict]:
        try:
            return (await self._request("GET", "/mediarooms")).get("mediaRooms", [])
        except CrestronHomeAuthError:
            raise
        except CrestronHomeError:
            return []

    # --- commands ----------------------------------------------------------

    async def media_select_source(self, room_id: int, source_id: int) -> None:
        await self._request("POST", f"/mediarooms/{room_id}/selectsource/{source_id}")

    async def media_power(self, room_id: int, on: bool) -> None:
        await self._request("POST", f"/mediarooms/{room_id}/power/{'on' if on else 'off'}")

    async def media_volume(self, room_id: int, level: int) -> None:
        # Crestron's docs say 0-100 percent, but processors (e.g. MC4-R fw 2.8000) take the
        # same 0-65535 scale they report in currentVolumeLevel. Sending percent sets ~0.
        await self._request("POST", f"/mediarooms/{room_id}/volume/{max(0, min(65535, int(level)))}")

    async def media_mute(self, room_id: int, mute: bool) -> None:
        await self._request("POST", f"/mediarooms/{room_id}/{'mute' if mute else 'unmute'}")


    async def set_light_level(self, light_id: int, level: int, fade_ms: int = 0) -> None:
        level = max(0, min(65535, int(level)))
        await self._request(
            "POST", "/lights/SetState", {"lights": [{"id": light_id, "level": level, "time": fade_ms}]}
        )

    async def recall_scene(self, scene_id: int) -> None:
        await self._request("POST", f"/scenes/recall/{scene_id}")

    async def lock(self, lock_id: int) -> None:
        await self._request("POST", f"/doorlocks/lock/{lock_id}")

    async def unlock(self, lock_id: int) -> None:
        await self._request("POST", f"/doorlocks/unlock/{lock_id}")
