# FleetPilot: a thousand home batteries acting as one power plant, even when some drop offline

**Track:** Orchestration · **User:** Base Power fleet-ops / VPP dispatch engineers · **Run:** `python3 app.py` (stdlib only)

## Problem
Base operates hundreds of MWh of home batteries as a VPP in ERCOT. Every dispatch must do three things at once:
1. turn a **market signal** into a **fleet MW target**;
2. split it across thousands of batteries with different sizes and states of charge;
3. keep every customer's **backup promise**, even when devices drop mid-dispatch (Wi-Fi, inverter fault, owner override).

When a slice of the fleet disappears during a price spike, every MW that isn't re-dispatched is lost revenue and a missed
commitment. And an operator needs to *see* that no customer's backup was spent to cover it.

## What FleetPilot does
| Step | How |
|---|---|
| **Read** | Official, credential-free ERCOT `system-wide-prices.json`: 15-min RT and 24h DAM for LZ_AEN (Austin), plotted as a full-day RT vs DAM chart. Committed snapshot fallback, labeled **CACHED**. |
| **Decide** | RT ≥ today's DAM p75 → DISCHARGE; ≤ p25 → CHARGE; else HOLD. The target is capped at 70% of headroom to leave room for recovery. |
| **Allocate** | The target is split across homes in proportion to each home's headroom above its backup floor, for a 1-hour dispatch block. |
| **Fail → re-dispatch** | 15% of the dispatched homes go dark. Their lost MW moves to healthy homes' spare headroom. If there isn't enough headroom, FleetPilot reports an **honest shortfall** and never breaks a floor. |
| **Prove** | Invariants on every run: dispatch never pushes a home below its floor, no home exceeds 11.5 kW, and offline homes output exactly 0. |

## The demo moment (verified numbers)
Scarcity drill, 1,000 homes, 20% reserve: **7.49 MW → 150 homes fail → 6.36 MW → 850 homes pick it up → 7.49 MW**, zero
shortfall, all invariants green.
Raise the reserve to 50%: the target drops to **3.9 MW**, and the gross reserve opportunity cost rises from **$1.4k/h to $10.4k/h**
(at the simulated $2,500/MWh). The screen shows **18.7 MWh actually held**, plus the 252 homes that already started below
the new floor (0.8 MWh gap). It surfaces that gap and doesn't hide it.

## Why Base's engineers would care
- It's the dispatch desk's core loop (signal → target → fault-tolerant allocation → proof), made explicit, testable and explainable.
- It prices the **backup-vs-revenue tradeoff** in $/h, the number product, ops and trading argue about.
- The integration path is clear: swap the synthetic fleet for real telemetry, the quartile rule for Base's bid schedule, and the payload for a device API.

## Commercial angle
Every REP, co-op and muni launching a residential VPP (including Base's utility partners) needs this layer, and needs to
show a regulator or customer that backup promises held during dispatch.

## It works
One command, no dependencies, and a LIVE/CACHED/SIMULATION provenance badge. There are 27 unit and integration tests: conservation across seeds,
floor/power invariants, honest shortfall, charge-mode recovery, feed validation and fallback, and API bounds.

*Honesty note: the ERCOT prices are real. The fleet, the $2,500 spike and the outage are synthetic and labeled as such in the UI.*
