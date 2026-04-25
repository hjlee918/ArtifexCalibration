# app/tv/dv_config.py
# VERIFY on hardware: the correct SSAP URI for DV config upload needs confirmation.
# LightSpace CMS guides in Resources/ reference DV config upload but do not document
# the raw SSAP endpoint. Update _DV_CONFIG_URI after testing on C1/C2.
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

_DV_CONFIG_URI = "ssap://externalpq/setDolbyVisionUserDisplayConfiguration"


@dataclass
class DolbyVisionConfig:
    raw_text: str

    async def upload(self, client) -> None:
        """Upload the DV config to the TV via SSAP."""
        payload = {"data": self.raw_text}
        result = await client.request(_DV_CONFIG_URI, payload)
        if not result.get("returnValue", False):
            error = result.get("errorText", "unknown error")
            raise RuntimeError(f"DV config upload failed: {error}")


def load_dv_config(path: Path) -> DolbyVisionConfig:
    """Load a Dolby Vision user display configuration file (.txt or .cfg)."""
    path = Path(path)
    if path.suffix.lower() not in (".txt", ".cfg"):
        raise ValueError(f"Expected .txt or .cfg file, got: {path.suffix}")
    return DolbyVisionConfig(raw_text=path.read_text())
