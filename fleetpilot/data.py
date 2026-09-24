"""ERCOT price ingestion with a validated, committed fallback fixture."""

from __future__ import annotations

import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

FEED_URL = "https://www.ercot.com/api/1/services/read/dashboards/system-wide-prices.json"
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "fixture_prices.json"
ALLOWED_ZONES = frozenset({"lzAen"})


def _number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _parse(payload: object, zone: str) -> tuple[list[dict], list[dict], str]:
    if not isinstance(payload, dict):
        raise ValueError("ERCOT payload is not an object")

    rt_rows = payload.get("rtSppData")
    dam_rows = payload.get("damSppData")
    if not isinstance(rt_rows, list) or not isinstance(dam_rows, list):
        raise ValueError("ERCOT payload is missing price series")

    rt: list[dict] = []
    for row in rt_rows:
        if not isinstance(row, dict):
            continue
        time = row.get("intervalEnding")
        price = row.get(zone)
        if isinstance(time, str) and time and _number(price):
            rt.append({"t": time, "price": float(price)})

    dam: list[dict] = []
    for row in dam_rows:
        if not isinstance(row, dict):
            continue
        hour = row.get("hourEnding")
        price = row.get(zone)
        if _number(hour) and 1 <= int(hour) <= 24 and _number(price):
            dam.append({"t": f"{int(hour):02d}:00", "price": float(price)})

    if not rt or not dam:
        raise ValueError(f"no usable price data for {zone}")
    return rt, dam, str(payload.get("lastUpdated") or "Unknown")


def _read_fixture() -> object:
    with FIXTURE_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_prices(zone: str = "lzAen") -> tuple[list[dict], list[dict], dict]:
    """Return normalized RT prices, DAM prices, and source metadata.

    Live data is accepted only after schema validation. Any network, JSON, or live
    schema failure falls back to the committed ERCOT snapshot. Unknown zones are
    rejected rather than silently mapped to a different location.
    """

    if zone not in ALLOWED_ZONES:
        raise ValueError(f"unsupported zone {zone!r}; choose one of {sorted(ALLOWED_ZONES)}")

    mode = "LIVE"
    fallback_reason = ""
    try:
        request = Request(FEED_URL, headers={"User-Agent": "FleetPilot/1.0"})
        with urlopen(request, timeout=5) as response:
            payload = json.load(response)
        rt, dam, last_updated = _parse(payload, zone)
    except Exception as exc:  # upstream reliability boundary; fixture is validated below
        mode = "CACHED"
        fallback_reason = f"{type(exc).__name__}: {exc}"
        rt, dam, last_updated = _parse(_read_fixture(), zone)

    meta = {
        "mode": mode,
        "last_updated": last_updated,
        "feed": FEED_URL,
        "zone": zone,
    }
    if fallback_reason:
        meta["fallback_reason"] = fallback_reason
    return rt, dam, meta

