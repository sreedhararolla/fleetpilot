# Decisions

- **D1 (turn 5, opus as driver):** Build **FleetPilot** in the **Orchestration** track. This is sol's reduced hybrid (critiques/sol-on-opus.md).
  Both of us independently came around to the other's pitch; the re-dispatch event is the memorable, Base-specific beat.
- **D2:** **stdlib only** (http.server, urllib, unittest). No scipy/LP, no NOAA, no static report, no extra feeds.
- **D3:** Data = ERCOT `dashboards/system-wide-prices.json` (it contains both `rtSppData` 15-min and `damSppData` hourly).
  Default zone `lzAen` (Austin). Committed fixture = CACHED fallback.
- **D4 (amended turn 6):** Decision rule = RT vs today's DAM p25/p75. The DAM gives the "is now actually a good hour?" context without an optimizer.
  Target is capped at 70% of fleet power. An 85% target left no practical headroom after 15% of dispatched homes failed;
  70% makes the default recovery credible while still producing a large dispatch.
- **D5:** Interfaces frozen in PLAN.md (`load_prices`, `engine.run`, `/api/state`). Changes need a line here.
- **D6:** Ownership: opus = fleet/engine/engine tests/PITCH; sol = data/app/web/data tests/README/DEMO.
- **D7 (turn 6, sol as navigator):** The default UI has no failure; Drill deterministically fails 15% of actively
  dispatched homes, then re-dispatches. Inputs are bounded. Extreme inputs may show a truthful shortfall rather than
  claiming recovery. The UI labels grid data as LIVE/CACHED and fleet/failure behavior as synthetic DRILL.

- **D8 (turn 7, opus):** Accept D4-amended (70% cap) and D7 in full. Contract clarification, with no shape change: when `fail=0`,
  `dispatch.after_failure_mw == dispatch.after_redispatch_mw == allocated_mw`, `failed_homes=0`, and there are no failure/redispatch
  events. The payload always has every key. In drill, engine `decision.reason` starts with "DRILL:".
- **D9:** Code lives in our worktrees (wt-opus / wt-sol). The referee merges them. File ownership per PLAN.md, so no merge collisions.

## Open objections

None. Sol's turn-6 items (70% cap, deterministic active-home failure in stable ID order, bounded inputs, zone
allowlist, honest shortfall, synthetic-fleet labeling) are all **accepted**. **PLAN LOCKED as of turn 7.**
