# 001-opus
**Did:** Read BRIEF, checked data reachability (ERCOT DAM/RT SPP HTML pages, ERCOT dashboard JSON
fuel-mix/system-wide-demand/supply-demand all 200; NOAA api.weather.gov 200; todays-outlook.json 403).
Env: Python 3.12 + uv available; scipy 1.18.1 installs via uv (set `UV_CACHE_DIR=$TMPDIR/uvc`,
the home cache is read-only in the sandbox).
Wrote pitches/opus.md: **FleetPilot** (Orchestration track) — plan tomorrow's VPP fleet dispatch on
real ERCOT DAM load-zone prices, weather-aware backup reserve, coordinator re-dispatch when homes fail,
self-contained HTML report.

**Next:** read your pitch, critique, converge on one idea + interface split in DECISIONS.md.

**Need from sol:** your pitch; if we merge ideas, keep the core = real ERCOT prices + a coordination
step Base Power engineers would recognize. Proposed split: one of us does data+planner+tests, the other
fleet/coordinator/report/docs.
