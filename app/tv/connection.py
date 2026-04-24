# app/tv/connection.py
import asyncio
import logging
import re
from bscpylgtv import WebOsClient
from app.tv.state import TVSettingsSnapshot, ChipGeneration
from app.utils.keychain import save_client_key, load_client_key, delete_client_key

logger = logging.getLogger(__name__)

_COMPAT_BAD_MAJOR = 7
_COMPAT_BAD_MINOR_THRESHOLD = 3

_CHIP_MAP = {
    "C1": ChipGeneration.ALPHA9_GEN4,   # 2021
    "G1": ChipGeneration.ALPHA9_GEN4,
    "Z1": ChipGeneration.ALPHA9_GEN4,
    "B1": ChipGeneration.ALPHA9_GEN4,
    "C2": ChipGeneration.ALPHA9_GEN5,   # 2022
    "G2": ChipGeneration.ALPHA9_GEN5,
    "Z2": ChipGeneration.ALPHA9_GEN5,
    "B2": ChipGeneration.ALPHA9_GEN5,
    "C3": ChipGeneration.ALPHA9_GEN6,   # 2023
    "G3": ChipGeneration.ALPHA9_GEN6,
    "Z3": ChipGeneration.ALPHA9_GEN6,
    "B3": ChipGeneration.ALPHA9_GEN6,
    "C4": ChipGeneration.ALPHA9_GEN7,   # 2024
    "G4": ChipGeneration.ALPHA9_GEN7,
    "Z4": ChipGeneration.ALPHA9_GEN7,
    "B4": ChipGeneration.ALPHA9_GEN7,
    "C5": ChipGeneration.ALPHA9_GEN8,   # 2025
    "G5": ChipGeneration.ALPHA9_GEN8,
    "Z5": ChipGeneration.ALPHA9_GEN8,
    "B5": ChipGeneration.ALPHA9_GEN8,
    "C6": ChipGeneration.ALPHA9_GEN9,   # 2026 (chip name unconfirmed)
    "G6": ChipGeneration.ALPHA9_GEN9,
    "Z6": ChipGeneration.ALPHA9_GEN9,
    "B6": ChipGeneration.ALPHA9_GEN9,
}


def _detect_chip(model_name: str) -> ChipGeneration:
    if not model_name:
        logger.debug("Empty model_name — chip generation unknown")
        return ChipGeneration.UNKNOWN
    model_upper = model_name.upper()
    for suffix, gen in _CHIP_MAP.items():
        if re.search(rf"{re.escape(suffix)}(?!\d)", model_upper):
            return gen
    return ChipGeneration.UNKNOWN


def _is_firmware_incompatible(major: str, minor: str) -> bool:
    # webOS 7.3+ on 2021 C1 models broke the calibration API.
    # webOS 22+ uses calendar-year versioning and is unaffected.
    # Only major == 7, minor >= 3 is the confirmed bad range.
    try:
        return int(major) == _COMPAT_BAD_MAJOR and int(minor) >= _COMPAT_BAD_MINOR_THRESHOLD
    except ValueError:
        return False


class ConnectionManager:
    def __init__(self, ip: str):
        self.ip = ip
        self.snapshot = TVSettingsSnapshot()
        self.firmware_warning: bool = False
        self.client_key: str | None = load_client_key(ip)
        self._client: WebOsClient | None = None

    async def connect(self) -> None:
        client = WebOsClient(self.ip, client_key=self.client_key)
        try:
            await client.connect()
            self.client_key = client.client_key
            self._client = client
            await self._post_connect()
            save_client_key(self.ip, self.client_key)
        except Exception:
            self._client = None
            try:
                await client.disconnect()
            except Exception:
                pass
            raise

    async def _post_connect(self) -> None:
        info = await self._client.get_software_info()
        model = info.get("model_name", "")
        major = info.get("major_ver", "0")
        minor = info.get("minor_ver", "0")
        self.snapshot.chip_generation = _detect_chip(model)
        self.snapshot.webos_version = f"{major}.{minor}"
        self.firmware_warning = _is_firmware_incompatible(major, minor)
        if self.firmware_warning:
            logger.warning(
                "webOS %s.%s — calibration API may be incompatible", major, minor
            )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def reconnect_with_backoff(self, max_attempts: int = 3) -> bool:
        delays = [2, 4, 8]
        for attempt, delay in enumerate(delays[:max_attempts], 1):
            try:
                await self.connect()
                return True
            except Exception as e:
                logger.warning("Reconnect attempt %d failed: %s", attempt, e)
                if attempt < max_attempts:
                    await asyncio.sleep(delay)
        return False

    def clear_stored_key(self) -> None:
        delete_client_key(self.ip)
        self.client_key = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> WebOsClient | None:
        return self._client
