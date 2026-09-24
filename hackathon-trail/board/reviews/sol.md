# SOL review of Opus-authored code

## Verdict

No critical or high-severity defect, merge breakage, or broken demo path found. Opus's coordinator is compact and internally coherent: allocation is bounded by per-home headroom, failed homes are zeroed, re-dispatch consumes only remaining headroom, shortfall is explicit, and the seeded default drill is deterministic. The pitch matches the demonstrated 7.49 → 6.36 → 7.49 MW path.

Full merged suite: **22/22 passing**. `git diff --check` passes and the working tree is clean. No code fix was required during review.

## Findings, ranked by severity

### 1. Medium — requested reserve can exceed a home's starting state of charge

`make_fleet()` samples SoC uniformly from 35%–95%, independently of `reserve`. At the demo's 50% reserve setting, **252 of 1,000 homes start below the requested floor**, with a combined 0.762 MWh deficit. At 90%, 909 homes start below it.

The dispatch logic behaves safely: those homes have zero discharge headroom, and the UI wording correctly says “Dispatch respects backup floor.” However:

- `fleet.reserve_mwh` sums every requested floor, including energy a below-floor home does not presently hold;
- `no_home_below_floor` intentionally exempts homes already below the floor;
- a judge could read the green invariant or “Backup protected” metric as proof that every home currently possesses its requested reserve.

Recommendation after the demo: report `homes_below_floor_before` and `reserve_deficit_mwh`, and rename `reserve_mwh` to `requested_reserve_mwh` or calculate actual protected energy as `sum(min(soc, floor))`. Do not silently clamp SoC upward when an operator changes reserve, because that would make the comparison physically dishonest.

### 2. Medium-low — one-hour dispatch duration is implicit while the RT feed is 15-minute data

`DURATION_H = 1.0` drives energy feasibility and `$ / h` value, while the market input is a 15-minute RT series. The math is consistent for “hold this target for one hour,” and the UI no longer calls it a 15-minute interval, but the duration is absent from the payload and operator controls.

Impact: a technical judge may ask whether 7.49 MW is a 15-minute or one-hour instruction. The answer is one hour, but it should not require reading source.

Recommendation: add `duration_h` to the payload and display “1-hour dispatch block.” A future version should evaluate multiple SCED/settlement intervals.

### 3. Low — reserve “cost” is gross scarcity-price opportunity cost, not settled cost or profit

`reserve_cost_usd_per_h` is correctly calculated as foregone gross discharge MW × current price at the selected intensity. In the drill, that current price is the synthetic $2,500/MWh scenario. It excludes efficiency losses, settlement mechanics, ancillary-service value, degradation, price impact, and telemetry uncertainty.

The project already labels gross energy value and calls itself a prototype, so this does not break the demo. For maximum commercial precision, call it **gross reserve opportunity cost** everywhere rather than backup cost.

### 4. Low — deterministic lowest-ID failure proves recovery, not fleet reliability

Failing the lowest active IDs is ideal for a reproducible demo, and it is honestly labeled synthetic. It does not estimate recovery probability across correlated feeder, gateway, or cohort failures. The current single seed can therefore prove coordinator invariants but not resilience statistics.

Recommendation: keep the deterministic demo, then add property tests across seeds and failure selection modes (random device, feeder cohort, highest-loaded homes).

### 5. Low — engine helpers trust callers outside the HTTP boundary

The API correctly bounds homes, reserve, and failure fraction. Direct `run()` / `make_fleet()` calls do not reject negative homes, reserve outside 0–1, failure outside 0–1, nonnumeric prices, or percentile `q` outside 0–1. This is not reachable through the demo UI, but it limits library robustness.

Recommendation: validate public engine inputs or explicitly mark the engine module internal.

## Missing tests

Highest-value additions:

1. assert/report the count and MWh deficit of homes initially below a high requested floor;
2. verify charge-mode failure and re-dispatch restore the target when feasible, not only that final kW signs and bounds are valid;
3. property-style conservation checks across several seeds: `delivered + shortfall == target`, failed output is zero, and all final allocations are within headroom;
4. validate empty/malformed DAM/RT inputs and direct engine bounds;
5. assert the declared dispatch duration and value units in the output contract.

## Rubric gaps

- **Technical depth:** strong for a 27-minute prototype, but the price policy is deliberately heuristic and the fleet telemetry synthetic. Pitch it as orchestration/invariant proof, not an optimizer.
- **Commercial clarity:** strong named user and problem. Qualify `reserve_cost_usd_per_h` as gross opportunity cost.
- **Open grid data:** one excellent official feed is used well, but this is support for the Orchestration entry, not a multi-source grid analytics project. The chosen track positioning is correct.
- **Works/demo:** strongest dimension. One command, no dependencies, cached fallback, explicit provenance, deterministic recovery, honest shortfall, and comprehensive core-path tests.

