# BRIEF — Base Power x AITX Talent Hackathon (Austin, Sept 25–27 2026)

You are a two-person team. Your goal: **build the project most likely to win a prize** at this hackathon.
You decide together which track to enter, what to build, and how. Nobody will decide for you.

## The event
- Hosted at **Base Power HQ, Austin TX**, presented by AITX Community, with Thrive Capital and a16z
  (Talent x Opportunity) supporting. Part of Austin Deep Tech Week.
- It is also a **hiring event**: Base Power's engineering team is present all weekend and is effectively the audience.
- Event page: https://luma.com/aitx-94j6

## The host: Base Power
- Austin startup and Texas retail electricity provider (REP) in ERCOT.
- Installs large home batteries (~39 kWh class) on a subscription, bundled with an electricity plan.
- Operates the fleet as a **virtual power plant (VPP)**: charges when power is cheap, discharges at
  peaks and during scarcity, earns ERCOT market revenue, and provides backup during outages.
- Also runs VPPs through utility partnerships (co-ops/munis). Hundreds of MWh deployed across Texas.

## Tracks (verbatim from the event page)
1. **Open Grid Data**: "The Texas grid publishes a huge amount of real time and historical data and almost
   nobody does anything with it." Prices, load, generation mix, outages.
2. **Orchestration**: "Build a system that coordinates many independent things. Agents, jobs, workers,
   whatever you want."
3. **Most Commercializable**: "Build something that could actually be a product. Name who it is for and
   what problem it solves."

Prize amounts, judging criteria and judges are **not published**. Infer them from the host and audience.

## Constraints for your build
- Time box: set by the referee (shown in every turn). Plan for a working demo, not a roadmap.
- Must run locally with one command, documented in `README.md`. Include tests for core logic.
- Public data is fair game (ERCOT public reports/APIs, EIA, NOAA weather, gridstatus-style open data).
  No paid APIs or credentials. If live data is unreachable, ship a cached sample dataset and say so.
- Final deliverables in the main repo: working code, `README.md`, `DEMO.md` (a 3-minute demo script:
  problem, who it's for, live walkthrough, why it matters to Base Power), and `PITCH.md` (one page).

## Rubric (used by the judge; 0–10 each)
1. **Track fit & prize odds**: clearly targets a track and would stand out against other teams there.
2. **Relevance to Base Power**: would their engineers care or use it (VPP dispatch, ERCOT markets, fleet ops, customers)?
3. **Technical depth**: non-trivial, correct, uses real grid data or real coordination problems well.
4. **It actually works**: runs from README, demo path works end-to-end, tests pass.
5. **Commercial clarity**: named user, named problem, credible value.
6. **Demo & pitch quality**: DEMO.md and PITCH.md are crisp and compelling.
