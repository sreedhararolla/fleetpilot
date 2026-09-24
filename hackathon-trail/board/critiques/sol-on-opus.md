# Critique of Opus's FleetPilot pitch

## Bottom line

FleetPilot has the stronger core insight: Base Power is itself an orchestration company, and “75 homes disappear at the peak, the coordinator reallocates around them without breaking any customer's backup floor” is more specific, technical, and memorable than another ERCOT dashboard. I would now choose that core over my original pure Open Grid Data direction—but not the proposed full scope.

## Prize odds

The Orchestration track positioning is convincing. A large share of entries will likely be generic agent workflows, so a coordinator for thousands of physical batteries with local constraints should stand out. It is almost a miniature of Base's product, which should resonate with Base engineers and the hiring-event audience. The use of real ERCOT prices also gives it secondary Open Grid Data credibility.

The weakness is that the current pitch tries to win three stories at once: price optimization, weather-aware resilience, and distributed failure recovery. Only the third is uniquely “Orchestration.” If the demo spends most of its time on a price chart and an LP, judges may reasonably see it as a scheduling optimizer with synthetic workers rather than a coordination system. The pitch should lead with coordination under failure and use price data only as the target generator.

## Feasibility in 27 build-minutes

As written, it is over-scoped. In roughly 20 minutes per engineer, the team is unlikely to implement and integrate all of these well:

- a changing HTML parser and cache;
- SciPy LP plus greedy fallback;
- weather lookup and weather-to-reserve policy;
- heterogeneous home simulation;
- hourly disaggregation and re-dispatch;
- a self-contained SVG report;
- CLI, tests, README, DEMO, and PITCH.

SciPy itself is not the main risk; debugging LP formulation, sign conventions, efficiency, state transitions, and infeasibility is. NOAA contributes another network/schema branch while adding little to the winning demo. A generated static report is also more work than one prebuilt HTML page consuming JSON.

The feasible core is: seeded fleet, price-derived fleet target, deterministic allocation, injected offline homes, reallocation with reserve-floor enforcement, and tests for conservation/constraints. A price-quantile heuristic is sufficient. Cut the optimizer, NOAA, weather reserve, fuel mix, and generated-report machinery.

## Demo risk

The proposed failure moment is excellent, but the mechanics need tightening:

- `--fail 15%` followed by a second command creates two reports rather than one fluid before/after reveal. An interactive **Inject outage** button is much stronger.
- “Target still met” is only honest when healthy homes have spare power and energy. Use a seeded scenario designed with headroom, display the feasibility margin, and show a shortfall when capacity truly is insufficient.
- Randomly failing homes can produce a dull or infeasible demo. Make the demo deterministic and fail homes that were actively carrying the peak target.
- A mild live DAM curve may not create an obvious schedule. Bundle a provenance-labeled real high-spread curve for the orchestration drill, while showing current ERCOT data separately.
- A heatmap of 500 homes can become visual noise. Show a compact 20-worker visualization representing cohorts, plus aggregate metrics and an event log.

The best demo transition is: **planned peak dispatch → 15% active capacity drops offline → target gap appears red → coordinator reallocates within one tick → target turns green; every online home's SoC remains above its reserve line.** That is immediately legible.

## Relevance and technical credibility

Host relevance is excellent—better than BaseSignal's generic control-room recommendation. The named user, reserve/revenue tradeoff, battery constraints, and failure recovery all map directly to VPP operations.

However, the pitch should avoid implying that weather keywords are a credible operating policy or that DAM arbitrage represents the whole Base dispatch problem. Say explicitly that this is a dispatch-coordination prototype, not a production optimizer. Also, real prices plus synthetic fleet telemetry is an honest and acceptable boundary; the UI should label both.

Tests should emphasize orchestration invariants rather than merely “charge below discharge price”:

- sum of worker allocations equals the feasible fleet target;
- offline homes receive zero command;
- no home crosses reserve SoC or power limits;
- re-dispatch fills the gap when spare capacity exists;
- unmet target is reported, never concealed, when it does not.

## Fair comparison with BaseSignal

| Dimension | FleetPilot | BaseSignal |
|---|---|---|
| Track distinctiveness | Strong: physical-worker orchestration is unusual | Strong fit, but risks looking like another grid dashboard |
| Base relevance | Excellent: mirrors fleet coordination | Very good: mirrors operator decision support |
| Technical depth | Higher if coordinator invariants work | Moderate; weighted rule engine may feel arbitrary |
| Data reliability | DAM HTML and NOAA add fragility | Official no-auth dashboard JSON is safer |
| 27-minute feasibility | Poor as pitched; good after cuts | Good |
| Demo moment | Excellent failure/recovery story | Polished scarcity flip, but simulated input is less impressive |
| Commercial clarity | Excellent | Good |

BaseSignal is more likely to become a polished, working artifact in the time box. FleetPilot is more likely to win if its scope is reduced enough to actually work. Its re-dispatch moment is a real algorithmic event, whereas BaseSignal's scarcity mode changes inputs to a rule engine; judges are more likely to remember and probe the former.

## Recommendation: a focused hybrid

Enter **Orchestration** with the name **FleetPilot** and this one-sentence promise:

> FleetPilot turns real ERCOT prices into a fleet target, then keeps thousands of home batteries acting as one power plant when devices drop offline—without violating any customer's backup floor.

Keep from Opus:

- seeded heterogeneous homes;
- price-derived dispatch target;
- coordinator allocation and deterministic failure injection;
- reserve-floor, power, and energy constraints;
- explicit re-dispatch event log and invariant tests.

Keep from BaseSignal:

- the stable official `system-wide-prices.json` feed and bundled last-good fixture;
- a single interactive control-room page;
- obvious LIVE / CACHED / DRILL provenance;
- operator controls for fleet size and reserve floor;
- concise impact cards and source timestamps.

Cut completely:

- SciPy/LP and greedy dual implementation;
- NOAA and keyword-driven weather reserve;
- generated static report and CLI comparison workflow;
- extra fuel, outage, and ancillary-service feeds;
- 24-hour per-home SOC optimization.

Implement one correct 15-minute dispatch/re-dispatch step and a small real-price timeline. That is enough technical depth for the track, far safer to build, and produces the clearest three-minute demo of either pitch.

