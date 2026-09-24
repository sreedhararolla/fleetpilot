#!/usr/bin/env python3
"""FleetPilot local demo server. Run with: python3 app.py"""

from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fleetpilot.data import ALLOWED_ZONES, load_prices
from fleetpilot.engine import run

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "web" / "index.html"
_price_cache: tuple[float, tuple[list[dict], list[dict], dict]] | None = None


def cached_prices() -> tuple[list[dict], list[dict], dict]:
    global _price_cache
    now = time.monotonic()
    if _price_cache is None or now - _price_cache[0] >= 60:
        _price_cache = (now, load_prices())
    return _price_cache[1]


def _single(query: dict[str, list[str]], key: str, default: str) -> str:
    values = query.get(key, [default])
    if len(values) != 1:
        raise ValueError(f"{key} must appear once")
    return values[0]


def parse_inputs(query: dict[str, list[str]]) -> dict:
    zone = _single(query, "zone", "lzAen")
    if zone not in ALLOWED_ZONES:
        raise ValueError(f"zone must be one of {sorted(ALLOWED_ZONES)}")
    try:
        homes = int(_single(query, "homes", "1000"))
        reserve = float(_single(query, "reserve", "0.2"))
        drill_raw = _single(query, "drill", "0")
        if drill_raw not in {"0", "1"}:
            raise ValueError("drill must be 0 or 1")
        drill = drill_raw == "1"
        fail = float(_single(query, "fail", "0.15" if drill else "0"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid query: {exc}") from exc
    if not 10 <= homes <= 5000:
        raise ValueError("homes must be between 10 and 5000")
    if not 0 <= reserve <= 0.9:
        raise ValueError("reserve must be between 0 and 0.9")
    if not 0 <= fail <= 0.5:
        raise ValueError("fail must be between 0 and 0.5")
    return {"zone": zone, "homes": homes, "reserve": reserve, "fail": fail, "drill": drill}


class Handler(BaseHTTPRequestHandler):
    server_version = "FleetPilot/1.0"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload, separators=(",", ":")).encode(), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
            return
        if parsed.path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
            return
        if parsed.path != "/api/state":
            self._json(404, {"error": "not found"})
            return
        try:
            inputs = parse_inputs(parse_qs(parsed.query, keep_blank_values=True))
            rt, dam, meta = cached_prices()
            payload = run(
                rt,
                dam,
                homes=inputs["homes"],
                reserve=inputs["reserve"],
                fail=inputs["fail"],
                drill=inputs["drill"],
            )
            payload["mode"] = "DRILL" if inputs["drill"] else meta["mode"]
            payload["source"] = meta
            # Echo the already-normalized public series so the UI can make the
            # real grid input visible. Drill changes only the decision price;
            # these series retain their LIVE/CACHED provenance.
            payload["prices"] = {"rt": rt, "dam": dam}
            self._json(200, payload)
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:
            self._json(500, {"error": "state calculation failed", "detail": str(exc)})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="FleetPilot VPP orchestration demo")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"FleetPilot ready at http://localhost:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
