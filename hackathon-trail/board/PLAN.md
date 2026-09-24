# PLAN — FleetPilot (Orchestration track)

> FleetPilot turns real ERCOT prices into a fleet target, then keeps a thousand home batteries acting as one
> power plant when devices drop offline, without violating any customer's backup floor.

## Track & project
- **Track: Orchestration.** Many independent batteries coordinated by one control loop: allocate → failure → re-dispatch.
- **Data:** official no-auth ERCOT `https://www.ercot.com/api/1/services/read/dashboards/system-wide-prices.json`
  (verified: `lastUpdated`, `rtSppData`[15-min RT SPP, keys `intervalEnding`, `lzAen`, `hbNorth`...], `damSppData`[24 hourly DAM]).
  Committed fixture fallback. **stdlib only**. No scipy, no pip install.

## Demo script outline (3 min)
1. Problem (20s): Base runs thousands of home batteries as a VPP. Devices go offline, and every home has a backup promise.
2. `python3 app.py` → open http://localhost:8000. Badge **LIVE** (or CACHED). Today's real LZ_AEN RT vs DAM price chart.
3. The decision card: action + target MW + reason ("RT $X vs today's DAM p75 $Y").
4. Operator sets 1,000 homes and a 20% reserve. A representative worker grid shows per-home kW.
5. **Drill** (labeled simulation): price spike → DISCHARGE. Then **15% of actively dispatched homes drop offline**. The event log shows
   the coordinator re-dispatching the lost MW to healthy homes. Delivered MW goes back to the target (or honest
   shortfall), and the invariants panel is green: no home below its floor, no home over its power limit.
6. Raise reserve to 50%: protected MWh rises and available output/revenue is capped. Why Base cares + commercial.

The drill is deterministic at the default inputs: it fails dispatched homes in stable ID order and leaves enough
healthy headroom to recover. Non-default inputs may produce an honest shortfall; that is a feature, not a hidden error.

## Architecture
```
ERCOT system-wide-prices.json ──> fleetpilot/data.py (fetch, 5s timeout, fixture fallback)
                                         │ prices, meta
                                         ▼
fleetpilot/fleet.py (seeded homes) ─> fleetpilot/engine.py: decide → allocate → fail → redispatch → payload
                                         │ dict
                                         ▼
app.py (stdlib http.server): GET / → web/index.html ; GET /api/state?... → JSON
web/index.html (vanilla JS + inline SVG, no CDN)
```

## Repo layout & ownership (NO shared files except where noted)
| path | owner |
|---|---|
| `fleetpilot/__init__.py` (empty) | opus |
| `fleetpilot/fleet.py`, `fleetpilot/engine.py` | opus |
| `tests/test_engine.py` | opus |
| `fleetpilot/data.py`, `data/fixture_prices.json` | sol |
| `tests/test_data.py` | sol |
| `app.py`, `web/index.html` | sol |
| `README.md`, `DEMO.md` | sol |
| `PITCH.md` | opus |

Tests: `python3 -m unittest discover -s tests` (stdlib unittest, no pytest).

## Interfaces (frozen; change only via DECISIONS.md)
### data.py (sol)
```python
def load_prices(zone: str = "lzAen") -> tuple[list[dict], list[dict], dict]:
    """returns (rt, dam, meta)
    rt  = [{"t": "00:15", "price": 32.66}, ...]   # today's 15-min RT SPP so far, chronological
    dam = [{"t": "01:00", "price": 30.1}, ...]    # 24 hourly DAM SPP (hourEnding -> "HH:00")
    meta = {"mode": "LIVE"|"CACHED", "last_updated": str, "feed": url, "zone": zone}"""
```
Verified keys: `damSppData[i] = {"hourEnding": 1, "lzAen": 35.79, "timestamp": "2026-09-24 01:00:00-0500", ...}`
→ `t = f"{hourEnding:02d}:00"`. `rtSppData[i] = {"intervalEnding": "00:15", "lzAen": 32.66, ...}`.

### engine.py (opus)
```python
def run(rt, dam, homes=1000, reserve=0.2, fail=0.15, drill=False, seed=7) -> dict
```
Returns (app.py adds `"mode"`: meta.mode, or "DRILL" if drill, plus `"source": meta`):
```json
{
 "now": {"t": "12:30", "price": 41.2},
 "decision": {"action": "DISCHARGE|CHARGE|HOLD", "target_mw": 8.1, "reason": "...",
              "dam_p25": 25.0, "dam_p75": 60.0},
 "fleet": {"homes": 1000, "online_before": 1000, "online_after": 850,
           "power_mw": 11.5, "energy_mwh": 39.0, "reserve_mwh": 7.8},
 "dispatch": {"target_mw": 8.1, "allocated_mw": 8.1, "after_failure_mw": 6.9,
              "after_redispatch_mw": 8.1, "shortfall_mw": 0.0, "failed_homes": 150, "boosted_homes": 612},
 "events": [{"step": "decide|allocate|failure|redispatch", "msg": "..."}],
 "homes_sample": [{"id": 0, "soc_pct": 71.0, "floor_pct": 20.0, "kw_before": 9.2, "kw_after": 11.0,
                   "status": "ok|failed|boosted"}],
 "invariants": {"no_home_below_floor": true, "no_home_over_power": true, "failed_homes_zero_output": true},
 "value": {"gross_usd_per_h": 334.0, "reserve_cost_usd_per_h": 0.0}
}
```
- `homes_sample`: up to 200 representative homes (the UI may render fewer). kW positive = discharge, negative = charge.
- `drill=True`: engine overrides `now.price` with a $2,500/MWh spike (the UI must label it SIMULATION).
- Decision: RT ≥ DAM p75 → DISCHARGE; RT ≤ DAM p25 → CHARGE; else HOLD. Intensity is capped at 70% of fleet
  power, leaving credible headroom to recover from a 15% actively-dispatched-home failure even with heterogeneous SoC.
- HOLD: failure step still runs, but the MW are 0. The UI should suggest Drill to see the re-dispatch.

### app.py (sol)
`GET /api/state?zone=lzAen&homes=1000&reserve=0.2&fail=0.15&drill=0` → engine payload + mode + source.
Port 8000, `python3 app.py [--port N]`. Price fetch is cached in memory for 60s.

Query inputs are parsed defensively and clamped/rejected to keep the demo reliable: `homes` 10–5,000, `reserve`
0–0.9, `fail` 0–0.5, `drill` only 0/1, and `zone` from a small allowlist of keys present in both RT and DAM data.
The initial UI request uses `fail=0`; clicking Drill requests `drill=1&fail=0.15` and reveals the returned event stages.

## Definition of done
- [ ] `python3 app.py` serves UI; LIVE when ERCOT is reachable, CACHED otherwise (fixture).
- [ ] Drill shows DISCHARGE → failure → re-dispatch with invariants green and target met.
- [ ] Default drill is deterministic and meets target; extreme operator inputs report a visible, accurate shortfall.
- [ ] `python3 -m unittest discover -s tests` passes (engine invariants + data parsing/fallback).
- [ ] README (one command, tests, data source, CACHED note), DEMO.md (3-min script), PITCH.md (one page).
- [ ] No server left running.
