# app/tv/settings.py
from bscpylgtv import WebOsClient

_SET_PQ_URI = "ssap://externalpq/setExternalPqData"
_GET_PQ_URI = "ssap://externalpq/getExternalPqData"

_CMS_COLOR_KEYS = {
    "red":     ("colorManagementRedHue",     "colorManagementRedSaturation",     "colorManagementRedLuminance"),
    "green":   ("colorManagementGreenHue",   "colorManagementGreenSaturation",   "colorManagementGreenLuminance"),
    "blue":    ("colorManagementBlueHue",    "colorManagementBlueSaturation",    "colorManagementBlueLuminance"),
    "cyan":    ("colorManagementCyanHue",    "colorManagementCyanSaturation",    "colorManagementCyanLuminance"),
    "magenta": ("colorManagementMagentaHue", "colorManagementMagentaSaturation", "colorManagementMagentaLuminance"),
    "yellow":  ("colorManagementYellowHue",  "colorManagementYellowSaturation",  "colorManagementYellowLuminance"),
}


class LGTVSettings:
    def __init__(self, client: WebOsClient, pic_mode: str = "expert1"):
        self._client = client
        self.pic_mode = pic_mode

    async def _set(self, data: dict) -> None:
        result = await self._client.request(_SET_PQ_URI, {"picMode": self.pic_mode, "data": data})
        if not result.get("returnValue", False):
            error = result.get("errorText", "unknown error")
            raise RuntimeError(f"SSAP setExternalPqData failed: {error}")

    async def set_white_balance_2pt(
        self,
        red_gain: int, green_gain: int, blue_gain: int,
        red_offset: int, green_offset: int, blue_offset: int,
    ) -> None:
        await self._set({
            "whiteBalanceRedGain": red_gain,
            "whiteBalanceGreenGain": green_gain,
            "whiteBalanceBlueGain": blue_gain,
            "whiteBalanceRedOffset": red_offset,
            "whiteBalanceGreenOffset": green_offset,
            "whiteBalanceBlueOffset": blue_offset,
        })

    async def set_white_balance_20pt(
        self,
        red: list[int],
        green: list[int],
        blue: list[int],
    ) -> None:
        if len(red) != 20 or len(green) != 20 or len(blue) != 20:
            raise ValueError("20-point white balance requires exactly 20 values per channel")
        await self._set({
            "whiteBalance20ptRed": red,
            "whiteBalance20ptGreen": green,
            "whiteBalance20ptBlue": blue,
        })

    async def set_cms_color(
        self, color: str, hue: int, saturation: int, luminance: int
    ) -> None:
        if color not in _CMS_COLOR_KEYS:
            raise ValueError(f"Unknown color '{color}'. Must be one of: {list(_CMS_COLOR_KEYS)}")
        hue_key, sat_key, lum_key = _CMS_COLOR_KEYS[color]
        await self._set({hue_key: hue, sat_key: saturation, lum_key: luminance})

    async def set_dynamic_contrast(self, value: str) -> None:
        await self._set({"dynamicContrast": value})

    async def set_dynamic_color(self, value: str) -> None:
        await self._set({"dynamicColor": value})

    async def set_asbl(self, enabled: bool) -> None:
        await self._set({"autoStaticBrightnessLimit": "on" if enabled else "off"})

    async def set_local_dimming(self, value: str) -> None:
        await self._set({"localDimming": value})

    async def set_energy_saving(self, value: str) -> None:
        await self._set({"energySaving": value})
