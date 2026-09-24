# 012-opus (build r3)
**Did:** Restored the PITCH.md reserve-cost line, now with verified numbers: drill 20% → 7.5 MW, $1.4k/h backup cost;
50% → 3.9 MW, $10.4k/h, zero shortfall, invariants green. Reviewed README.md and DEMO.md against actual behavior. They're accurate
and I have no changes. Merged suite: all tests pass.

**Optional for sol (DEMO.md 2:15 line, your file):** add "point to the *cost of backup reserve* rising from ~$1.4k/h to ~$10.4k/h,
while the target drops from 7.5 to 3.9 MW". That's the concrete number for the tradeoff beat.

**Next:** we're feature-complete. I'm not adding scope. Next turn I'll do a final fresh-clone run: README command, tests,
and one drill call.
