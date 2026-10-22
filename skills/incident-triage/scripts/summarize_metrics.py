#!/usr/bin/env python3
"""Summarize a metric time series around an incident.

Input: JSON file in the shape returned by the query_metrics tool.

    {
      "metric": "cpu_usage",
      "unit": "%",
      "threshold": 90,
      "points": [{"ts": "2026-10-21T10:30:00+09:00", "value": 41.2}, ...]
    }

Usage:
    python summarize_metrics.py metrics.json [--event-time ISO8601] [--threshold N]

Prints a JSON summary to stdout. Standard library only.
"""

import argparse
import json
import statistics
import sys
from datetime import datetime


def parse_ts(value):
    # Python < 3.11 does not accept a trailing "Z" in fromisoformat.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_points(data):
    points = []
    for item in data.get("points", []):
        if item.get("value") is None:
            continue
        points.append((parse_ts(item["ts"]), float(item["value"])))
    points.sort(key=lambda p: p[0])
    return points


def trend(values):
    """Least-squares slope over the last 5 points.

    Labelled rising/falling when the per-point change exceeds 1% of the mean.
    """
    tail = values[-5:]
    if len(tail) < 3:
        return "unknown", 0.0
    n = len(tail)
    mean_x = (n - 1) / 2
    mean_y = sum(tail) / n
    num = sum((i - mean_x) * (y - mean_y) for i, y in enumerate(tail))
    den = sum((i - mean_x) ** 2 for i in range(n))
    slope = num / den
    scale = max(abs(mean_y), 1e-9)
    if slope / scale > 0.01:
        return "rising", slope
    if slope / scale < -0.01:
        return "falling", slope
    return "flat", slope


def summarize(data, event_time=None, threshold=None):
    points = load_points(data)
    if not points:
        return {"error": "no data points"}

    threshold = threshold if threshold is not None else data.get("threshold")
    values = [v for _, v in points]

    before = [v for t, v in points if event_time and t < event_time]
    baseline = statistics.median(before) if before else None

    peak_ts, peak = max(points, key=lambda p: p[1])
    current_ts, current = points[-1]

    breach_start = None
    breach_minutes = None
    if threshold is not None:
        # Start of the latest continuous run above the threshold.
        for t, v in reversed(points):
            if v > threshold:
                breach_start = t
            else:
                break
        if breach_start is not None:
            breach_minutes = round((current_ts - breach_start).total_seconds() / 60, 1)

    direction, slope = trend(values)

    def pct(a, b):
        if a is None or b in (None, 0):
            return None
        return round((a - b) / abs(b) * 100, 1)

    return {
        "metric": data.get("metric"),
        "unit": data.get("unit"),
        "points": len(points),
        "range": {"from": points[0][0].isoformat(), "to": current_ts.isoformat()},
        "baseline_before_event": None if baseline is None else round(baseline, 2),
        "peak": {"value": round(peak, 2), "ts": peak_ts.isoformat()},
        "current": {"value": round(current, 2), "ts": current_ts.isoformat()},
        "change_vs_baseline_pct": pct(current, baseline),
        "threshold": threshold,
        "above_threshold_now": None if threshold is None else current > threshold,
        "breach_started_at": None if breach_start is None else breach_start.isoformat(),
        "breach_duration_minutes": breach_minutes,
        "trend_last_5": direction,
        "slope_per_point": round(slope, 3),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="metrics JSON file")
    parser.add_argument("--event-time", help="incident detected_at (ISO 8601)")
    parser.add_argument("--threshold", type=float, help="override threshold in the file")
    args = parser.parse_args(argv)

    try:
        with open(args.path, encoding="utf-8") as f:
            data = json.load(f)
        event_time = parse_ts(args.event_time) if args.event_time else None
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": f"cannot read input: {exc}"}, ensure_ascii=False))
        return 1

    print(json.dumps(summarize(data, event_time, args.threshold), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
