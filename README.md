# FleetPilot

**A VPP coordinator that keeps a thousand home batteries acting as one power plant when devices drop offline—without violating any customer's backup floor.**

FleetPilot is an Orchestration-track prototype for Base Power fleet operators. It turns official ERCOT Austin load-zone prices into a fleet target, assigns that target across heterogeneous home batteries, injects a deterministic device outage, and re-dispatches the lost power to healthy homes within their energy, power, and customer-backup constraints.

## Run locally

Requires Python 3.10+ and no third-party packages.

```bash
python3 app.py
```

Open [http://localhost:8000](http://localhost:8000). Use `python3 app.py --port 8080` to select another port.

The initial screen shows today's official RT-versus-DAM price chart and the current fleet decision with no simulated failures. Click **Run outage drill** to replay allocation → 15% active-home outage → re-dispatch. Change the fleet size or customer backup floor and click **Apply**.

## Test

```bash
python3 -m unittest discover -s tests -v
```

Tests cover feed parsing and fallback, input validation, dispatch constraints, offline-home isolation, successful re-dispatch when capacity exists, and honest shortfall reporting when it does not.

## Data provenance and modes

FleetPilot requests the official, credential-free ERCOT dashboard feed:

`https://www.ercot.com/api/1/services/read/dashboards/system-wide-prices.json`

It uses current-day real-time settlement prices and all 24 day-ahead prices for `LZ_AEN` (Austin Energy). The source badge is explicit:

- **LIVE** — the current ERCOT response passed schema validation.
- **CACHED** — ERCOT was unavailable or malformed, so the committed snapshot from September 24, 2026 at 12:32 CT is used.
- **SIMULATION · LIVE/CACHED** — prices retain that provenance, while the $2,500/MWh scarcity price and device outage are a clearly labeled drill.

The batteries, state of charge, and failures are seeded synthetic telemetry. FleetPilot is a decision-support prototype, not production dispatch or a representation of Base Power's private fleet.

## Architecture

```text
ERCOT JSON -> validated live/cache adapter -> fleet decision + coordinator
                                                   |
                                  allocate -> fail -> re-dispatch
                                                   |
                                   local JSON API -> control-room UI
```

The service is intentionally dependency-free: `urllib` for ingestion, `http.server` for the local API/UI, vanilla JavaScript for the staged visualization, and `unittest` for invariants.

## API

```text
GET /api/state?zone=lzAen&homes=1000&reserve=0.2&fail=0.15&drill=1
```

Bounds: 10–5,000 homes, 0–90% reserve, 0–50% failure. Unsupported or malformed inputs return HTTP 400. Live prices are cached in memory for 60 seconds.

See [DEMO.md](DEMO.md) for the three-minute walkthrough.
