# FleetPilot — 3-minute demo

## Before judging

1. Run `python3 -m unittest discover -s tests -v`.
2. Run `python3 app.py` and open `http://localhost:8000`.
3. Confirm the source badge is LIVE or CACHED and the page shows a decision. Both modes are valid.
4. Stop any rehearsal server before the formal run, then start it fresh.

## Script

### 0:00–0:25 — Problem

“Base does not operate one battery. It coordinates thousands of independent home batteries as one power plant, while every home keeps a backup promise. When devices drop offline during a valuable dispatch, the fleet still has to deliver—or report an honest shortfall.”

Point to the title and source badge. “FleetPilot is that control loop in miniature.”

### 0:25–0:55 — Real grid input

Point to the LIVE/CACHED badge, update time, real-time price, DAM thresholds, and the full-day RT-versus-DAM chart.

“This is official ERCOT `LZ_AEN` data. We compare the latest real-time price with today's day-ahead quartiles to produce a transparent charge, hold, or discharge target. If the network fails, we use a timestamped committed ERCOT snapshot and say so.”

The ordinary live action may be HOLD or CHARGE. That is expected; do not imply otherwise.

### 0:55–1:20 — Customer constraint

Show 1,000 homes and the 20% backup floor. Point to protected MWh and the green invariant panel.

“The fleet is seeded and heterogeneous: different capacities and state of charge, one 11.5 kW power limit, and this operator-selected customer reserve. The grid data is real; the fleet telemetry is explicitly synthetic.”

### 1:20–2:15 — Memorable moment

Click **Run outage drill** once, then pause while the three stages animate.

“The drill injects a clearly labeled $2,500 scarcity price. FleetPilot allocates the target. Then 15% of actively dispatched homes drop offline…”

Pause on the red middle card and red worker cells.

“…and the coordinator reassigns the missing megawatts to healthy batteries with headroom.”

Point to restored MW, boosted amber workers, event log, zero shortfall, and three green invariants. At the default inputs,
the stable drill result is approximately **7.49 → 6.36 → 7.49 MW**, with 150 failed and 850 boosted homes.

“Offline homes receive zero. No home exceeds its power limit. No home crosses its backup floor. If capacity is genuinely insufficient, FleetPilot displays the shortfall instead of hiding it.”

### 2:15–2:40 — Resilience tradeoff

Before changing the control, point out the 20% case: about 7.8 MWh actually held for backup and $1.4k/h shown as the cost
of reserve. Move the backup floor to 50%, click **Run outage drill**, then point to about 18.7 MWh actually protected, a
target reduced from roughly 7.5 to 3.9 MW, and about $10.4k/h in gross reserve opportunity cost. The screen also flags
that 252 synthetic homes already sit below the newly requested floor, representing a 0.8 MWh pre-existing gap.

“The same operator can reserve more energy for customers. Here that trades away about 3.6 MW of dispatch opportunity.
FleetPilot distinguishes energy actually held from the requested policy and surfaces the pre-existing gap rather than
pretending it is protected. The constraint and its gross opportunity cost are visible and auditable.”

### 2:40–3:00 — Close

“FleetPilot is not pretending to be Base's production optimizer. It proves the difficult coordination loop: real market signal in, thousands of constrained devices, failure, recovery, and truthful delivery out. That is what makes a distributed fleet behave like a dependable power plant.”

**Why it matters to Base Power:** “This is your dispatch desk's loop. Swap our synthetic fleet for your telemetry and our
quartile rule for your bid schedule, and the allocation, re-dispatch, and invariant checks carry over. It also answers
the question your ops and product teams share: what does each extra point of customer backup cost us per hour?”

## Likely judge questions

- **“Is the orchestration real or one function?”** Each home is an independently constrained worker (energy, power,
  floor). The coordinator allocates, detects the failed set, and re-dispatches only into remaining headroom. It's
  deterministic so the invariants are provable. In production, the same loop runs every dispatch interval.
- **“Why quartiles, not an optimizer?”** It's transparent and testable in a demo. The coordinator doesn't depend on how
  the target is chosen.
- **“Is the $ real?”** The prices are real ERCOT. The drill price and the fleet are synthetic, and the value is gross opportunity, not settled profit.

## Fallbacks

- If ERCOT is unavailable, continue with CACHED; this is intentional and labeled.
- If the default drill shows a small shortfall, say “the coordinator refuses to fake capacity” and point to the red value. Do not refresh repeatedly.
- If port 8000 is occupied, use `python3 app.py --port 8080`.
