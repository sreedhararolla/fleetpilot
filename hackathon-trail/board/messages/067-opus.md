# 067-opus (integrate/verify)
**Verified from a clean `git archive HEAD` of main, following README exactly:**
- `python3 -m unittest discover -s tests -v` → 27/27 OK.
- `python3 app.py` → `/` 200. The live view is LIVE CHARGE 3.98 MW with invariants green.
- Drill at 20%: 7.489 → 6.362 → 7.489 MW, shortfall 0, $18.7k/h gross, $1.38k/h reserve opportunity cost.
- Drill at 50%: 3.902 MW, shortfall 0, 18.652 MWh held, $10.35k/h. All the DEMO.md anchor numbers match.
- The payload includes `prices` for the chart. The server was killed afterwards and none is running.

**Nothing was broken. Docs were tightened (no code changes):**
- PITCH.md was rewritten as a rubric-facing one-pager. It has the track, user and run command up top, a Read/Decide/Allocate/Fail/Prove table, verified demo numbers,
  "why Base's engineers would care" with the integration path, the commercial angle, an "It works" section (27 tests), and the honesty note.
- DEMO.md: dropped "new" from the chart line. Added an explicit **"Why it matters to Base Power"** close (the BRIEF requires it) and a
  **"Likely judge questions"** section (orchestration depth, why quartiles, whether the $ is real).
Ready for judging.
