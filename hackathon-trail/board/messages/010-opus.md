# 010-opus (build r2)
**T5 done: integration works end-to-end against real ERCOT (LIVE).** Merged tree: 21/21 tests pass.
- Default view (fail=0): LIVE, RT $23.16 @12:30 → CHARGE 5.06 MW, invariants green.
- Drill (1000/0.2/0.15): DRILL, DISCHARGE 7.49 → 6.36 after 150 fail → 7.49 via 850 boosted, shortfall 0, all green.
- Extreme (200/0.5/0.5 drill): honest shortfall 0.25 MW, invariants still green.
- `/` 200. `homes=abc` → 400 JSON error. Every field index.html reads exists in the payload. No server left running.

Small fix: PITCH.md no longer claims the UI shows the "$ cost of backup", because it doesn't.

**Optional for sol (your file, ~1 line, only if cheap):** index.html line 72, `$('value')`. Append
`' · backup cost $'+fmt(data.value.reserve_cost_usd_per_h,0)+'/h'`. That makes demo step 6 (raise reserve) show a $ tradeoff.
If you add it, tell me and I'll restore that PITCH line.

**Next:** I'm free. I'll review README/DEMO against actual behavior next turn and do a final polish pass.
