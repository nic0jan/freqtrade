import argparse
import csv
import os
import sys
from datetime import UTC, datetime

import requests


DATA_DIR = os.path.join("user_data", "external", "sentiment")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def iso_utc(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


def save_csv(path: str, rows: list[tuple[str, float, str | None]]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "value", "symbol"])  # symbol optional
        for t, v, s in rows:
            writer.writerow([t, f"{v:.6f}", s or ""])
    os.replace(tmp, path)


def collect_fear_greed(limit: int = 1000) -> None:
    ensure_dir(DATA_DIR)
    url = f"https://api.alternative.me/fng/?limit={limit}&format=json"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    rows: list[tuple[str, float, str | None]] = []
    for entry in data:
        ts = int(entry.get("timestamp", 0))
        raw_val = float(entry.get("value", 50.0))
        # Map 0..100 -> -1..1
        norm = (raw_val - 50.0) / 50.0
        # Snap to daily 00:00:00 UTC
        dt = datetime.fromtimestamp(ts, tz=UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        rows.append((dt.isoformat(), max(-1.0, min(1.0, norm)), None))
    out = os.path.join(DATA_DIR, "fear_greed.csv")
    save_csv(out, sorted(rows, key=lambda r: r[0]))
    print(f"Saved {len(rows)} Fear&Greed rows -> {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect and backfill sentiment datasets.")
    parser.add_argument("--fng", action="store_true", help="Collect Alternative.me Fear & Greed")
    parser.add_argument(
        "--gdelt", action="store_true", help="Backfill GDELT GlobalTone as news sentiment"
    )
    parser.add_argument("--all", action="store_true", help="Collect all available public sources")
    parser.add_argument("--limit", type=int, default=1000, help="Max datapoints per source")
    args = parser.parse_args()

    if not args.fng and not args.all:
        print("Nothing to do. Use --fng or --all.")
        sys.exit(0)

    if args.fng or args.all:
        collect_fear_greed(limit=args.limit)
    if args.gdelt or args.all:
        # GDELT hourly GKG Aggregation is large; provide guidance instead of heavy default.
        # Placeholder: encourage the user to generate a CSV with columns timestamp,value,symbol.
        # For now, create an empty skeleton file if not present to illustrate schema.
        ensure_dir(DATA_DIR)
        out = os.path.join(DATA_DIR, "news.csv")
        if not os.path.isfile(out):
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "value", "symbol"])  # symbol optional
            print(f"Created skeleton news CSV -> {out}")
        else:
            print(f"Found existing news CSV -> {out}")


if __name__ == "__main__":
    main()
