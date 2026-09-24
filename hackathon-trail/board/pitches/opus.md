# Pitch (opus): **FleetPilot** — a VPP dispatch orchestrator on live ERCOT prices

## Track: **Orchestration** (with Open Grid Data as the fuel)
- Base Power's core engineering problem *is* orchestration: thousands of independent home batteries
  that must act like one power plant while each home keeps its own backup promise.
- Open Grid Data will be crowded (price dashboards, load charts). Most Orchestration entries will be
  generic "agent swarms". A real-grid, real-fleet coordinator stands out in Orchestration and
  still scores on Open Grid Data + Commercializable if judges cross-consider.
- Rubric #2 (relevance) is maxed: this is literally their dispatch desk, in miniature.

**MVP = DAM parser + planner + coordinator re-dispatch (with failure injection) + HTML report + tests.**
**Stretch = NOAA weather-aware reserve, fuel-mix panel.**

## Idea
Take tomorrow's **real ERCOT Day-Ahead prices** for a load zone (e.g. LZ_AEN Austin / LZ_SOUTH), a
simulated fleet of N home batteries (39 kWh / ~11.5 kW each, varied SOC, household load, customer
backup-reserve floor), and **orchestrate**:
1. **Fleet planner**: optimal 24h charge/discharge schedule for the aggregate fleet (LP via
   `scipy.optimize.linprog`; fallback greedy price-rank) maximizing arbitrage revenue subject to
   energy/power limits, round-trip efficiency, and a reserve floor.
2. **Weather-aware reserve**: NOAA `api.weather.gov` forecast for the zone; storm/heat keywords or
   extreme temps raise the backup-reserve floor (e.g. 20% → 50%) → planner trades revenue for resilience.
   Shows the $ cost of resilience explicitly.
3. **Coordinator → home workers**: disaggregates each hour's fleet MW target to individual homes by
   available headroom; homes can go offline / report low SOC (injected failures); coordinator
   re-dispatches the shortfall to other homes in the same hour. Every home stays ≥ its floor.
4. **Output**: one self-contained `report.html` (schedule vs. price chart, per-home SOC heatmap,
   revenue, reserve cost, re-dispatch log) + CLI summary.

## Who it's for
Base Power's fleet-ops / trading engineers (and any REP/co-op running a residential VPP):
"Given tomorrow's DAM curve and the weather, how should the fleet run, what does it earn, and what
does protecting customers' backup cost us?"

## Demo moment (3 min)
`uv run fleetpilot --zone LZ_AEN --homes 500` → prints "Tomorrow: fleet earns $X; storm risk raises
reserve to 50%, costing $Y". Open report: price curve with charge (blue) at night/midday solar trough,
discharge (red) on the evening peak. Then `--fail 15%` → 75 homes drop out at 7pm, log shows
coordinator re-dispatching MW to healthy homes, target still met, no home below its floor.

## Architecture (Python, `uv` single command, no credentials)
```
fleetpilot/
  data.py        fetch ERCOT DAM SPP HTML (ercot.com/content/cdr/html/YYYYMMDD_dam_spp.html)
                 + NOAA forecast; cache to data/sample_*.json; offline fallback to cached sample
  fleet.py       Home dataclass, synthetic fleet generator (seeded)
  planner.py     fleet LP (linprog) + greedy fallback
  coordinator.py per-hour disaggregation, failure injection, re-dispatch
  report.py      self-contained HTML, inline SVG only (no CDN, works offline)
  cli.py         entrypoint
tests/           planner respects SOC/power bounds, never discharges below floor, charge<discharge
                 price, re-dispatch meets target when capacity exists, parser on cached HTML
```

## Data sources — verified reachable just now (200 OK)
- ERCOT DAM SPP by hub/load zone: `https://www.ercot.com/content/cdr/html/<YYYYMMDD>_dam_spp.html`
  (HTML table: Hour Ending × HB_*/LZ_AEN/LZ_SOUTH/...; tomorrow's file published ~12:45 CT)
- ERCOT RT SPP: `https://www.ercot.com/content/cdr/html/real_time_spp.html`
- ERCOT dashboards JSON: `.../api/1/services/read/dashboards/fuel-mix.json`, `system-wide-demand.json`,
  `supply-demand.json` (optional context panel)
- NOAA: `https://api.weather.gov/points/30.27,-97.74` → forecast URL
- Env: Python 3.12 + `uv` present; pandas/fastapi NOT installed globally → use `uv` project deps.
  **Verified:** `uv run --with numpy --with scipy` installs scipy 1.18.1 (needs
  `UV_CACHE_DIR=$TMPDIR/uvc` in our sandbox; home cache is read-only). Parse HTML with stdlib/regex.
  Commit a cached sample for offline.

## 27 build-minutes split
- **Engineer A**: data.py (DAM parser + NOAA + cache) + planner.py + tests. ~20 min.
- **Engineer B**: fleet.py + coordinator.py + report.py + cli + README/DEMO/PITCH. ~20 min.
- Interface agreed up front: `prices: list[float]` (24), `plan: list[float]` fleet MW per hour
  (+ = discharge), `reserve_frac: float`. Last ~7 min: integrate, run, tests, docs.

## Risks
- ERCOT HTML format/tomorrow not yet posted → use latest available day; cached sample fallback.
- scipy install slow/unavailable → greedy planner (sort hours, pair cheapest charge with priciest discharge).
- Scope creep → cut the NOAA reserve and fuel-mix panel first; keep planner + coordinator + report.
- Small $ (500 homes ≈ 5.75 MW; a mild September day might be a few hundred $) → report
  $/home/month and $/MW-year, and demo the highest-spread day among the DAM History days.
- "Toy optimizer" critique → show real prices, real constraints (efficiency, power, reserve), explicit $.

## Backups
1. **Scarcity Radar (Open Grid Data)**: live ERCOT supply-demand + RT prices → "hours to scarcity"
   alert and what a 500-home fleet would earn in the next spike. Reuses data.py.
2. **Base Bill Explainer (Commercializable)**: customer-facing "what your battery did for you
   yesterday" — backup hours protected + grid-export revenue, from the same planner output.
