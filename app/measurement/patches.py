# app/measurement/patches.py
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Patch:
    r: int
    g: int
    b: int
    label: str = ""
    is_hdr: bool = False
    nits: float = 0.0


@dataclass
class PatchSequence:
    name: str
    patches: list[Patch] = field(default_factory=list)

    def __len__(self):
        return len(self.patches)

    def __iter__(self):
        return iter(self.patches)


def _gray(pct: float) -> Patch:
    v = round(pct / 100 * 255)
    return Patch(r=v, g=v, b=v, label=f"{pct:.0f}%")


def _hdr_gray(nits: float, peak_nits: float = 1000.0) -> Patch:
    pq_linear = nits / peak_nits
    v = round(pq_linear ** (1 / 2.4) * 255) if pq_linear > 0 else 0
    v = max(0, min(255, v))
    return Patch(r=v, g=v, b=v, label=f"{nits:.0f} nits", is_hdr=True, nits=nits)


SDR_GRAYSCALE_21: list[Patch] = [_gray(i * 5) for i in range(21)]

SDR_PRIMARIES: list[Patch] = [
    Patch(255, 0,   0,   "Red 100%"),
    Patch(0,   255, 0,   "Green 100%"),
    Patch(0,   0,   255, "Blue 100%"),
    Patch(0,   255, 255, "Cyan 100%"),
    Patch(255, 0,   255, "Magenta 100%"),
    Patch(255, 255, 0,   "Yellow 100%"),
]

SDR_SECONDARIES: list[Patch] = [
    Patch(128, 0,   0,   "Red 50%"),
    Patch(0,   128, 0,   "Green 50%"),
    Patch(0,   0,   128, "Blue 50%"),
]

HDR10_GRAYSCALE: list[Patch] = [
    _hdr_gray(0), _hdr_gray(1), _hdr_gray(2), _hdr_gray(5),
    _hdr_gray(10), _hdr_gray(20), _hdr_gray(50), _hdr_gray(100),
    _hdr_gray(200), _hdr_gray(400), _hdr_gray(600), _hdr_gray(800),
    _hdr_gray(1000),
]


def build_sdr_full() -> PatchSequence:
    patches = list(SDR_GRAYSCALE_21) + list(SDR_PRIMARIES) + list(SDR_SECONDARIES)
    return PatchSequence(name="SDR Full", patches=patches)


def build_hdr10_full() -> PatchSequence:
    patches = list(HDR10_GRAYSCALE) + list(SDR_PRIMARIES)
    return PatchSequence(name="HDR10 Full", patches=patches)
