# 007-opus
**Did:** Accepted all your turn-6 changes (70% cap, deterministic active-home failure, bounds, allowlist, honest
shortfall). Added D8: when fail=0, all dispatch keys are still present with after_* = allocated, and the drill reason starts with "DRILL:".
Added D9: code goes in the worktrees. Plan is **locked**. All 10 tasks have exactly one owner.

(wt-opus is read-only this turn, so the build starts next turn.)
**Next (me):** T1–T3 in wt-opus: `fleetpilot/__init__.py`, `fleet.py`, `engine.py`, `tests/test_engine.py`. Then PITCH.md.

**Need from sol:** T6/T8/T9 against the PLAN.md contract. Commit `data/fixture_prices.json` early. Also, in app.py
import `from fleetpilot.engine import run` and `from fleetpilot.data import load_prices`.
