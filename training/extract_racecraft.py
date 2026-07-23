"""Turn a completed evaluation trajectory into learned line/braking metadata."""

import argparse
import json
from pathlib import Path
import statistics


def aggregate_trajectory(track, trajectory):
    buckets = {}
    for sample in trajectory:
        buckets.setdefault(int(sample["index"]), []).append(sample)

    learned = []
    for index in sorted(buckets):
        point = track.center_points[index]
        normal = (-__import__("math").sin(point[2]), __import__("math").cos(point[2]))
        offsets = [
            (sample["x"] - point[0]) * normal[0]
            + (sample["y"] - point[1]) * normal[1]
            for sample in buckets[index]
        ]
        learned.append(
            {
                "index": index,
                "lateral_offset_m": round(statistics.median(offsets), 3),
                "speed_kmh": round(
                    statistics.median(s["speed_kmh"] for s in buckets[index]), 1
                ),
                "brake": round(
                    statistics.median(s["brake"] for s in buckets[index]), 3
                ),
                "throttle": round(
                    statistics.median(s["throttle"] for s in buckets[index]), 3
                ),
            }
        )
    return learned


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("trajectory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--confirm-extract", action="store_true")
    args = parser.parse_args(argv)
    if not args.confirm_extract:
        print("未处理轨迹：请先人工确认评估有效，再加入 --confirm-extract。")
        return 0

    # Imports are delayed so a dry run has no simulation dependencies.
    from training.racing_env import Track

    payload = json.loads(args.trajectory.read_text(encoding="utf-8"))
    track = Track(payload["track_id"])
    result = {
        "format": "game_racing_learned_racecraft_v1",
        "track_id": payload["track_id"],
        "valid_laps": payload["valid_laps"],
        "best_lap_time": payload["best_lap_time"],
        "samples": aggregate_trajectory(track, payload["trajectory"]),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
