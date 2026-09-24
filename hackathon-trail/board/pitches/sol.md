# Pitch: BaseSignal — turn public ERCOT telemetry into a battery fleet decision

## Track and prize strategy

**Primary track: Open Grid Data.** This is the best prize bet because it answers the host's own challenge literally—Texas publishes rich live data, but operators still need a decision, not another chart. A generic orchestration demo will be crowded with agents/job queues, while “Most Commercializable” is broad and invites polished SaaS competitors. BaseSignal uses multiple live ERCOT feeds to produce the exact operational output Base Power engineers care about: **charge, hold, or discharge; how many MW; and why now**. It also has a credible commercial story without diluting the primary track.

The differentiator is the last mile from open data to an auditable VPP action. ERCOT already visualizes each feed separately. BaseSignal fuses them, respects fleet constraints, and exposes the reasoning.

## Project idea

BaseSignal is a local “dispatch copilot” for a hypothetical Base battery fleet. It ingests live ERCOT conditions and evaluates a transparent policy every refresh:

- real-time settlement price and price trend;
- physical responsive capability / grid condition;
- supply–demand headroom and forecast gap;
- system storage behavior and renewable mix;
- operator inputs: fleet homes, 39 kWh/home, state of charge, minimum customer backup reserve, and max ramp.

It returns:

1. a large **CHARGE / HOLD / DISCHARGE** recommendation;
2. a constrained fleet power target in MW and duration;
3. the three strongest contributing signals, shown with source timestamps;
4. impact estimates: homes participating, MWh retained for backup, and gross market value at the current price;
5. a simple timeline showing how the policy would have acted on today's data.

The decision engine should be rules/score based, not fake AI: normalize price against the observed daily range, grid tightness against available-capacity margin, and renewable/storage context; then clamp output by energy, reserve floor, and ramp limits. That is easy to explain and test.

## User and problem

**User:** a Base Power fleet-operations engineer or control-room operator.

**Problem:** ERCOT's public telemetry is fragmented across dashboards and describes the grid, but does not answer “what should our distributed battery fleet do right now, given customer-backup promises?” An operator needs a quick recommendation with provenance and safe constraints, especially when price and reserves move quickly.

## Three-minute demo moment

Open one local dashboard. It visibly says **LIVE ERCOT**, shows feed freshness, current price, available margin, storage flow, and BaseSignal's current action. Change the fleet from 1,000 to 10,000 homes and the reserve floor from 20% to 40%; the MW target and retained backup MWh update instantly.

Then click **Scarcity drill**. This is explicitly labeled a simulation, not live data. Price rises and reserves tighten over ~8 seconds. The recommendation flips from HOLD/CHARGE to **DISCHARGE 100 MW**, the battery animation fans power from thousands of homes onto the grid, and a reason panel says, for example, “price spike + shrinking headroom; output capped to preserve 40% customer backup.” Turn the backup floor higher and the system sacrifices market revenue rather than violating the customer constraint. Click **Return to live** and it resumes the real feed.

That transition is the memorable moment: public grid data becomes a fleet action, and the safety tradeoff is visible rather than hand-waved.

## Architecture

Keep it dependency-light and robust:

```text
Official ERCOT public JSON
  -> Python fetch/cache adapter (timeouts, validation, bundled fallback snapshots)
  -> normalized GridSnapshot
  -> deterministic dispatch engine (price + tightness + trend, constrained by SoC/reserve/ramp)
  -> local JSON endpoint
  -> single-page control-room UI (HTML/CSS/JS, lightweight charts)
```

The backend can use Python's standard library HTTP server and `urllib`, so `python3 app.py` is genuinely one command with no install risk. Cache the last successful response and ship a small, timestamped fixture for offline judging. The UI must distinguish **LIVE**, **CACHED**, and **SIMULATION** modes.

Core tests should cover: low-price charge, high-price/low-reserve discharge, neutral hold, backup-floor clamping, ramp clamping, malformed/upstream-timeout fallback, and units (MW/MWh).

## Data sources — verified reachable

All are official ERCOT, public, JSON, and required no credentials when checked on **2026-09-24 around 12:30 CT**:

- `https://www.ercot.com/api/1/services/read/dashboards/system-wide-prices.json` — HTTP 200; ~25 KB; current-day real-time settlement prices for hubs/load zones, with timestamps. Use `lzNorth` or a selectable load zone.
- `https://www.ercot.com/api/1/services/read/dashboards/supply-demand.json` — HTTP 200; ~82 KB; five-minute capacity, demand, and forecast points.
- `https://www.ercot.com/api/1/services/read/dashboards/daily-prc.json` — HTTP 200; ~500 KB; current grid condition and physical responsive capability (PRC), plus intraday history.
- `https://www.ercot.com/api/1/services/read/dashboards/energy-storage-resources.json` — HTTP 200; ~82 KB; current/previous-day aggregate charging, discharging, and net output.
- `https://www.ercot.com/api/1/services/read/dashboards/fuel-mix.json` — HTTP 200; ~135 KB; five-minute generation by fuel, including storage, wind, and solar.
- Optional depth: `generation-outages.json` and `ancillary-services.json` at the same base URL were also HTTP 200, but should be omitted unless core work is finished.

The human-facing official index is `https://www.ercot.com/gridmktinfo/dashboards`. The registered ERCOT Public API requires auth, but these dashboard backing feeds do not; we should use the latter and document that distinction.

## What two engineers can build in 27 build-minutes

Strict MVP split:

- **Engineer A:** fetch/normalize three essential feeds (prices, supply-demand, PRC), implement dispatch function and six fast unit tests, add cached fallback.
- **Engineer B:** one polished static control-room page, fleet/reserve controls, mode badge, scarcity animation, and reason/impact cards.
- **Together in final minutes:** wire JSON, run one-command smoke test, rehearse the live-to-scarcity-to-live demo, and write the short README/demo script.

Cut fuel mix and storage telemetry first if time slips. Do not build authentication, forecasting ML, a database, maps, multi-agent infrastructure, or actual device control. The winning artifact is one correct decision loop with a sharp visual payoff.

## Main risks and mitigations

- **Live conditions are boring.** Make that honest: show the real HOLD state, then run a clearly labeled scarcity drill through the same decision engine.
- **ERCOT throttles or changes a feed.** Use short timeouts, schema guards, last-good in-memory cache, and committed fixtures; make data mode impossible to miss.
- **Operational recommendation looks simplistic.** Show the formula, component scores, units, constraints, and source freshness. Call it an operator decision aid/prototype—not autonomous production dispatch.
- **Market value calculation is challenged.** Label it “gross energy value” and compute `MW × hours × $/MWh`; do not imply settled profit or ancillary-service revenue.
- **Scope overruns.** Three feeds and four UI cards are sufficient. Every optional data source is a cuttable enhancement.

## Backup ideas

1. **Outage-to-Reserve:** Open Grid Data dashboard that combines generation outages, PRC, and supply-demand forecasts into a customer-backup reserve recommendation by hour. It is simpler, but less dynamic and less directly tied to market dispatch.
2. **Fleet Choreographer:** Orchestration-track visual simulator that schedules 10,000 independent batteries under feeder MW limits, SoC floors, and deadlines, comparing naive simultaneous dispatch with staggered coordination. Technically crisp and testable, but it gives up the unusually strong live-data story.

