# app/measurement/store.py
from __future__ import annotations
import json
from pathlib import Path
from app.measurement.session import PatchResult
from app.measurement.patches import Patch
from app.meter.device import XYZReading


def save_cgats(results: list[PatchResult], path: Path) -> None:
    path = Path(path)
    lines = [
        "CGATS.17",
        'ORIGINATOR "lg-oled-cal"',
        "NUMBER_OF_FIELDS 8",
        "BEGIN_DATA_FORMAT",
        "SAMPLE_ID SAMPLE_NAME RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z",
        "END_DATA_FORMAT",
        f"NUMBER_OF_SETS {len(results)}",
        "BEGIN_DATA",
    ]
    for i, r in enumerate(results, start=1):
        lines.append(
            f"{i} {r.patch.label or str(i)} "
            f"{r.patch.r} {r.patch.g} {r.patch.b} "
            f"{r.reading.X:.6f} {r.reading.Y:.6f} {r.reading.Z:.6f}"
        )
    lines.append("END_DATA")
    path.write_text("\n".join(lines))


def load_cgats(path: Path) -> list[PatchResult]:
    path = Path(path)
    results: list[PatchResult] = []
    in_data = False
    for line in path.read_text().splitlines():
        line = line.strip()
        if line == "BEGIN_DATA":
            in_data = True
            continue
        if line == "END_DATA":
            break
        if in_data and line:
            parts = line.split()
            if len(parts) >= 8:
                label = parts[1]
                r, g, b = int(parts[2]), int(parts[3]), int(parts[4])
                X, Y, Z = float(parts[5]), float(parts[6]), float(parts[7])
                results.append(PatchResult(
                    patch=Patch(r=r, g=g, b=b, label=label),
                    reading=XYZReading(X=X, Y=Y, Z=Z),
                ))
    return results


def save_json(results: list[PatchResult], path: Path) -> None:
    data = [
        {
            "patch": {"r": r.patch.r, "g": r.patch.g, "b": r.patch.b, "label": r.patch.label},
            "xyz": {"X": r.reading.X, "Y": r.reading.Y, "Z": r.reading.Z},
        }
        for r in results
    ]
    Path(path).write_text(json.dumps(data, indent=2))


def load_json(path: Path) -> list[PatchResult]:
    data = json.loads(Path(path).read_text())
    return [
        PatchResult(
            patch=Patch(r=d["patch"]["r"], g=d["patch"]["g"], b=d["patch"]["b"],
                        label=d["patch"]["label"]),
            reading=XYZReading(X=d["xyz"]["X"], Y=d["xyz"]["Y"], Z=d["xyz"]["Z"]),
        )
        for d in data
    ]
