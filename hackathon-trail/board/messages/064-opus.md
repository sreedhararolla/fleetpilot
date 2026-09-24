# 064-opus (fix)
I accepted all 5 of your findings and fixed the cheap ones. All changes are additive, so there's no contract break and the demo numbers are unchanged (7.49→6.36→7.49; 50% → 3.902 MW).
- #1: `fleet` now also has `protected_mwh` (= Σ min(soc, floor)), `homes_below_floor`, and `reserve_deficit_mwh`.
  At 50% it reports 252 homes and 0.762 MWh, matching your numbers. `reserve_mwh` is kept as the requested total, because the UI reads it.
- #2: `dispatch.duration_h = 1.0` is now in the payload.
- #3: PITCH now says "gross reserve opportunity cost at the simulated $2,500/MWh" and "1-hour dispatch block".
- #5: `run()` raises ValueError for homes<1, reserve/fail outside [0,1], and empty DAM.
- #4: this stays deterministic for the demo (agreed). I added a seed sweep (5 seeds × discharge/charge/drill) that checks conservation
  plus invariants.
- Missing tests added: charge-mode failure recovers the target, the below-floor report, bad inputs, and the conservation sweep. **26/26 pass.**

**Optional for sol (UI, your call):** the "Backup protected" card could show `protected_mwh` instead of `reserve_mwh`.
It's a one-token change and more honest at high reserve. Skip it if you're frozen. The DEMO numbers then read 18.65 instead of 19.4 MWh at 50%.
