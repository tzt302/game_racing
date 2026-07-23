"""Import five circuits from real FastF1 qualifying telemetry.

This is a development-time tool.  The generated JSON is dependency-free at
runtime, so players do not need FastF1, pandas, SciPy or a network connection.
"""

from __future__ import annotations

import json
from pathlib import Path

import fastf1
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "fastf1"
OUTPUT = ROOT / "src" / "track" / "telemetry_layouts.json"

CIRCUITS = {
    "spa": {
        "round": 13,
        "length_m": 7004,
        "width": 15.0,
        "laps": 3,
    },
    "silverstone": {
        "round": 12,
        "length_m": 5891,
        "width": 15.0,
        "laps": 3,
    },
    "monza": {
        "round": 16,
        "length_m": 5793,
        "width": 15.0,
        "laps": 3,
    },
    "monaco": {
        "round": 8,
        "length_m": 3337,
        "width": 11.0,
        "laps": 4,
    },
    "shanghai": {
        "round": 2,
        "length_m": 5451,
        "width": 15.0,
        "laps": 3,
    },
}


def seconds(value) -> float:
    return round(float(value.total_seconds()), 3)


def circular_smooth(values: np.ndarray, radius: int = 3) -> np.ndarray:
    padded = np.concatenate((values[-radius:], values, values[:radius]))
    kernel = np.ones(radius * 2 + 1, dtype=float) / (radius * 2 + 1)
    return np.convolve(padded, kernel, mode="valid")


def import_circuit(track_id: str, spec: dict) -> dict:
    session = fastf1.get_session(2025, spec["round"], "Q")
    session.load(telemetry=True, weather=False, messages=False)
    lap = session.laps.pick_fastest()
    telemetry = lap.get_telemetry().dropna(
        subset=["Time", "Distance", "X", "Y", "Speed", "RPM", "nGear", "Throttle", "Brake"]
    )
    telemetry = telemetry.sort_values("Distance").drop_duplicates("Distance")

    source_distance = telemetry["Distance"].to_numpy(dtype=float)
    source_distance *= spec["length_m"] / source_distance[-1]
    sample_distance = np.arange(0.0, float(spec["length_m"]), 5.0)

    def interpolate(column):
        return np.interp(sample_distance, source_distance, telemetry[column].to_numpy(dtype=float))

    x = circular_smooth(interpolate("X"))
    y = circular_smooth(interpolate("Y"))
    z = circular_smooth(interpolate("Z"))
    x -= x.mean()
    y -= y.mean()
    z -= z.mean()

    # FastF1 position coordinates use an arbitrary circuit scale.  Preserve the
    # measured shape, then normalize its closed polyline to the published length.
    closed_x = np.append(x, x[0])
    closed_y = np.append(y, y[0])
    geometry_length = np.hypot(np.diff(closed_x), np.diff(closed_y)).sum()
    geometry_scale = spec["length_m"] / geometry_length
    x *= geometry_scale
    y *= geometry_scale
    z *= geometry_scale

    speed = interpolate("Speed")
    rpm = interpolate("RPM")
    gear = interpolate("nGear")
    throttle = interpolate("Throttle") / 100.0
    brake = interpolate("Brake")
    time_values = np.array([value.total_seconds() for value in telemetry["Time"]], dtype=float)
    lap_time_axis = np.interp(sample_distance, source_distance, time_values)

    sector_one = seconds(lap["Sector1Time"])
    sector_two = seconds(lap["Sector2Time"])
    split_times = [sector_one, sector_one + sector_two]
    sector_indices = [int(np.abs(lap_time_axis - split).argmin()) for split in split_times]

    points = []
    for i in range(len(sample_distance)):
        points.append(
            [
                round(float(x[i]), 2),
                round(float(y[i]), 2),
                round(float(speed[i]), 1),
                int(round(float(gear[i]))),
                round(float(throttle[i]), 3),
                bool(brake[i] >= 0.5),
                int(round(float(rpm[i]))),
                round(float(z[i]), 2),
            ]
        )

    return {
        "year": 2025,
        "event": session.event["EventName"],
        "session": "Qualifying",
        "driver": str(lap["Driver"]),
        "lap_time": seconds(lap["LapTime"]),
        "sector_times": [
            sector_one,
            sector_two,
            seconds(lap["Sector3Time"]),
        ],
        "sector_indices": sector_indices,
        "length_m": spec["length_m"],
        "width": spec["width"],
        "laps": spec["laps"],
        "sample_m": 5.0,
        "points": points,
    }


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE))
    fastf1.set_log_level("WARNING")
    output = {track_id: import_circuit(track_id, spec) for track_id, spec in CIRCUITS.items()}
    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    for track_id, data in output.items():
        print(
            f"{track_id:12} {len(data['points']):4} points  "
            f"{data['driver']} {data['lap_time']:.3f}s  sectors={data['sector_indices']}"
        )
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
