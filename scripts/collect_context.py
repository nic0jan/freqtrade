import argparse
import csv
import os
from datetime import UTC, datetime

import requests


DATA_DIR = os.path.join("user_data", "external", "context")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_csv(path: str, rows: list[tuple[str, float, str | None]]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "value", "symbol"])  # symbol optional
        for t, v, s in rows:
            w.writerow([t, f"{v:.8f}", s or ""])
    os.replace(tmp, path)


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


def collect_btc_dominance() -> None:
    """Skeleton: user provides a CSV, or integrate from a data vendor.
    This will just create a header file if missing, to document schema.
    """
    ensure_dir(DATA_DIR)
    out = os.path.join(DATA_DIR, "btc_dominance.csv")
    if not os.path.isfile(out):
        save_csv(out, [])
        print(f"Created schema file: {out}")
    else:
        print(f"Found existing: {out}")


def collect_dxy() -> None:
    ensure_dir(DATA_DIR)
    out = os.path.join(DATA_DIR, "dxy.csv")
    if not os.path.isfile(out):
        save_csv(out, [])
        print(f"Created schema file: {out}")
    else:
        print(f"Found existing: {out}")


def collect_spx() -> None:
    ensure_dir(DATA_DIR)
    out = os.path.join(DATA_DIR, "spx_futures.csv")
    if not os.path.isfile(out):
        save_csv(out, [])
        print(f"Created schema file: {out}")
    else:
        print(f"Found existing: {out}")


def collect_binance_funding(symbol: str = "BTCUSDT") -> None:
    """Binance funding rates via public API.
    API: https://binance-docs.github.io/apidocs/spot/en/#index-price-and-mark-price-kline-candlestick-data (futures funding history documented elsewhere)
    We'll use /fapi/v1/fundingRate
    """
    ensure_dir(DATA_DIR)
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    params = {"symbol": symbol, "limit": 1000}
    rows: list[tuple[str, float, str | None]] = []
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    for e in data:
        # fundingTime in ms, fundingRate as string
        ts = int(e.get("fundingTime", 0)) // 1000
        fr = float(e.get("fundingRate", 0.0))
        # Normalize small values to roughly [-1,1] scale is left to service; store raw
        dt = datetime.fromtimestamp(ts, tz=UTC)
        rows.append((dt.isoformat(), fr, symbol.replace("USDT", "")))
    out = os.path.join(DATA_DIR, "funding_rate.csv")
    save_csv(out, sorted(rows, key=lambda r: r[0]))
    print(f"Saved {len(rows)} funding rows -> {out}")


def collect_binance_open_interest(symbol: str = "BTCUSDT") -> None:
    """Open interest history is not available in simple public REST without API key; this is a placeholder.
    Creates schema file if missing.
    """
    ensure_dir(DATA_DIR)
    out = os.path.join(DATA_DIR, "open_interest.csv")
    if not os.path.isfile(out):
        save_csv(out, [])
        print(f"Created schema file: {out}")
    else:
        print(f"Found existing: {out}")


def collect_basis_placeholder(symbol: str = "BTCUSDT") -> None:
    ensure_dir(DATA_DIR)
    out = os.path.join(DATA_DIR, "basis.csv")
    if not os.path.isfile(out):
        save_csv(out, [])
        print(f"Created schema file: {out}")
    else:
        print(f"Found existing: {out}")


def collect_long_short_placeholder(symbol: str = "BTCUSDT") -> None:
    ensure_dir(DATA_DIR)
    out = os.path.join(DATA_DIR, "long_short_ratio.csv")
    if not os.path.isfile(out):
        save_csv(out, [])
        print(f"Created schema file: {out}")
    else:
        print(f"Found existing: {out}")


def main() -> None:
    p = argparse.ArgumentParser(description="Collect context datasets (macro & derivatives)")
    p.add_argument(
        "--symbol", type=str, default="BTCUSDT", help="Perp symbol for Binance endpoints"
    )
    p.add_argument("--fng", action="store_true", help="No-op here; use collect_sentiment.py")
    p.add_argument("--funding", action="store_true", help="Collect Binance funding history")
    p.add_argument("--oi", action="store_true", help="Create open interest schema (placeholder)")
    p.add_argument("--basis", action="store_true", help="Create basis schema (placeholder)")
    p.add_argument("--ls", action="store_true", help="Create long/short schema (placeholder)")
    p.add_argument("--btcdom", action="store_true", help="Create BTC dominance schema placeholder")
    p.add_argument("--dxy", action="store_true", help="Create DXY schema placeholder")
    p.add_argument("--spx", action="store_true", help="Create SPX futures schema placeholder")
    p.add_argument("--all", action="store_true", help="Run everything available")
    args = p.parse_args()

    if args.all or args.funding:
        collect_binance_funding(args.symbol)
    if args.all or args.oi:
        collect_binance_open_interest(args.symbol)
    if args.all or args.basis:
        collect_basis_placeholder(args.symbol)
    if args.all or args.ls:
        collect_long_short_placeholder(args.symbol)
    if args.all or args.btcdom:
        collect_btc_dominance()
    if args.all or args.dxy:
        collect_dxy()
    if args.all or args.spx:
        collect_spx()


if __name__ == "__main__":
    main()
