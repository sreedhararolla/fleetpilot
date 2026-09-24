# Hackathon trail

FleetPilot was built by two AI agents working as one team: **Claude Opus 5.5** (`opus`) and **GPT-5.6 Sol** (`sol`), run by the neutral referee in [`../referee/`](../referee/referee.py). It was a 45-minute smoke run against the Base Power x AITX brief ([`board/BRIEF.md`](board/BRIEF.md)), judged by **GPT-6 Astra**.

| Phase | Where to look |
|---|---|
| 1. Independent pitches | `board/pitches/` |
| 2. Cross-critiques | `board/critiques/` |
| 3. Plan, tasks, decisions | `board/PLAN.md`, `board/tasks.json`, `board/DECISIONS.md` |
| 4. Parallel build (branches `opus`, `sol`) | git history, `board/messages/` |
| 5. Cross-review and fixes | `board/reviews/` |
| 6. Integration on `main` | git history |
| 7. Judging (7.5/10) | `JUDGE.json` |

`logs/turns.jsonl` has one line per turn. `logs/raw/` has every prompt and response, and `logs/referee.log` is the timeline.
Usage in `SUMMARY.json` was corrected after the run (see its `note`).
