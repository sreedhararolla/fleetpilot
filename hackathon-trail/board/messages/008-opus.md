# 008-opus (build r1)
**Done (wt-opus):** T1 `fleetpilot/fleet.py`, T2 `fleetpilot/engine.py`, T3 `tests/test_engine.py` (14 tests, all pass with
`python3 -m unittest discover -s tests`), T4 `PITCH.md`. Also created `fleetpilot/__init__.py`.

Engine follows the PLAN.md contract exactly: `run(rt, dam, homes, reserve, fail, drill, seed)`. The default drill (1000 homes, 20%, fail .15) gives:
target 7.49 MW → 150 failed (−1.13 MW, after_failure 6.36) → 850 boosted → 7.49 MW, shortfall 0, invariants all true,
gross $18.7k/h, reserve_cost $1.38k/h. With fail=0 there are 2 events (decide, allocate) and after_* == allocated.
`homes_sample` is evenly spaced (step = homes//200), so failed homes appear in the sample. kW is + for discharge, − for charge.
`fleet.energy_mwh` = current stored energy (SOC), not nameplate.

**Next (me):** T5 integration smoke test once your data.py/app.py lands on `sol`. Until then I'm free.

**Need from sol:** your branch has no code yet. You own 5 tasks, so I can take some. **Unless you've already started it, I'll take
T7 (tests/test_data.py) or README.md next round.** Tell me which in your message. Otherwise I'll only do T5, so we don't collide.
