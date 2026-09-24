# FleetPilot: one power plant out of a thousand homes, even when some drop offline

**Track:** Orchestration · **Built for:** Base Power fleet-ops / VPP dispatch engineers

## The problem
Base runs hundreds of MWh of home batteries as a virtual power plant in ERCOT. Every dispatch has to do three things at once:
1. turn a **market signal** into a **fleet MW target**;
2. split that target across thousands of batteries with different sizes and states of charge;
3. keep every customer's **backup promise**, even when devices go offline in the middle of a dispatch (Wi-Fi drops, inverter faults, homeowner override).

Today that coordination logic sits inside internal systems that nobody outside can see. When a slice of the fleet
disappears during an evening price spike, every MW that isn't re-dispatched is revenue lost and a commitment missed.

## What FleetPilot does
- **Reads real ERCOT prices** (official public `system-wide-prices.json`: 15-min RT and hourly DAM SPP, Austin
  zone by default; falls back to a committed snapshot, clearly labeled CACHED).
- **Decides:** the RT price is compared with today's DAM distribution. In the top quartile it DISCHARGES, in the bottom quartile it CHARGES, otherwise it HOLDS.
  The target is capped at 70% of fleet headroom so there is room to recover from failures.
- **Coordinates:** it allocates the target across homes in proportion to each home's headroom above its backup floor.
- **Survives failure:** it knocks 15% of the dispatched homes offline. The coordinator puts the lost MW on healthy homes'
  spare headroom and restores the target. If it can't restore it, it reports an **honest shortfall** instead of breaking a customer's floor.
- **Proves it:** it checks invariants on every run: no home pushed below its floor, no home over 11.5 kW, and failed homes at exactly 0.

## Demo in one line
Live ERCOT prices → scarcity drill → 1,000 homes discharge 7.5 MW → 150 go dark (−1.1 MW) → 850 pick it up →
target met, all invariants green. Then raise the reserve to 50%: protected MWh rise, the target shrinks, and the
**"cost of backup reserve" in $/h** grows on screen (drill, 1-hour dispatch block: 20% reserve → 7.5 MW, $1.4k/h gross reserve opportunity cost at the
simulated $2,500/MWh; 50% → 3.9 MW, $10.4k/h, still zero shortfall). At 50%, the API also reports how many homes
*start* below the requested floor (`homes_below_floor`, `reserve_deficit_mwh`). Dispatch never pushes them lower.

## Why it matters to Base
- It is the dispatch desk's core loop, made explicit, testable and explainable to an operator.
- It turns the backup-vs-revenue tradeoff into a number (`reserve_cost_usd_per_h`, the gross opportunity cost, not settled profit) that product and ops can reason about.
- It gives a clear path forward: plug the real telemetry in for the synthetic fleet, the real bid schedule in for the price rule, and add a real device API.

## Commercial angle
Every REP, co-op and muni launching a residential VPP (Base's own utility partners included) needs this layer:
market signal → fleet target → fault-tolerant allocation → proof that customers stayed protected.

*Honesty note: the grid prices are real; the fleet and the drill are synthetic and labeled that way in the UI.*
