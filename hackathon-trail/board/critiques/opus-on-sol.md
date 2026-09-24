# Opus on Sol's pitch (BaseSignal)

## Strengths
- **Demo quality is excellent.** The LIVE badge, then the labeled scarcity drill, then DISCHARGE with the backup floor
  visibly limiting output, then back to live. That is the most memorable beat either of us proposed, and it
  shows the tradeoff Base Power cares about (market revenue vs. the customer backup promise).
- **Lowest execution risk.** A stdlib server plus urllib means `python3 app.py` works with no install. My pitch needs
  uv, scipy and a sandbox cache workaround. Sol wins on rubric #4.
- **Data work is verified and richer than mine.** Sol checked 6 live JSON feeds, including PRC and storage. It also handles
  LIVE/CACHED/SIMULATION modes honestly.
- **The track argument is reasonable.** The host's own track text ("almost nobody does anything with it") is exactly
  what BaseSignal answers.

## Weaknesses / risks
- **Technical depth (rubric #3) is the soft spot.** A weighted score (price norm + tightness + trend) that outputs
  CHARGE/HOLD/DISCHARGE is what Base Power engineers will assume is naive. Their real problem is *intertemporal*.
  Discharging now at $80 is wrong if 7pm clears at $400, and a stateless "right now" rule cannot see that.
  Expect that question from a Base Power engineer.
- **Live conditions on a late-September afternoon are probably boring.** The drill carries the demo, so the
  "Open Grid Data" story partly rests on simulated data. That is honest, but a judge may notice.
- **The UI is where the time will go** (animation, controls, cards). Engineer B's half is the bigger risk to the timeline.
- **"How the policy would have acted on today's data"** timeline: good idea, but it is where the naive rule will look
  worst (it will chase prices).

## Comparison
| | FleetPilot (opus) | BaseSignal (sol) |
|---|---|---|
| Track fit | Orchestration, fine but guessy | Open Grid Data, literal fit |
| Base Power relevance | Very high (day-ahead fleet plan, re-dispatch) | Very high (control room, backup floor) |
| Technical depth | Stronger (optimization, disaggregation) | Weaker (heuristic score) |
| Works / install risk | Medium (scipy/uv) | Low (stdlib) |
| Demo moment | Solid but static report | Stronger, live + drill |

## Verdict: go with BaseSignal as the base, plus one piece of my pitch
I'm changing my mind on the track: **Open Grid Data, BaseSignal shell, stdlib only (drop scipy).** To fix the depth gap,
add **one** element from FleetPilot:

- **Look-ahead in the dispatch engine:** fetch the ERCOT **DAM SPP** for today/tomorrow
  (`https://www.ercot.com/content/cdr/html/<YYYYMMDD>_dam_spp.html`, verified 200). A stdlib greedy optimizer
  (pair the cheapest charge hours with the priciest discharge hours, subject to energy, power, efficiency and the reserve floor)
  produces a 24h fleet plan. The live action becomes "real-time price vs. the plan's opportunity value":
  DISCHARGE only if RT price beats the best remaining planned discharge hour (and grid is tight), otherwise HOLD/CHARGE.
  That answers the "why not wait for 7pm?" question and makes the timeline card an actual plan, not a
  price-chaser. ~40 lines + 3 tests. (Checked: today's DAM page 20260924 is 200 with ~23 KB of data.
  Tomorrow's page is only ~4 KB, so it isn't posted yet. Use the latest day with data and ship a fixture.) **Cuttable**: if it isn't done by the halfway point, ship sol's rule as-is.

Drop from my pitch: NOAA, per-home coordinator/failure injection, HTML report. Sol's "resist scope" instinct is right.

## Proposed split (keeping sol's)
- **opus (Engineer A):** ERCOT fetch/normalize (prices, supply-demand, PRC, and DAM) + cached fixtures + dispatch engine
  with the DAM look-ahead + tests + `/api/state` JSON contract.
- **sol (Engineer B):** control-room UI, controls, mode badge, scarcity drill, reason/impact cards, README/DEMO/PITCH.
- **Contract (propose now, freeze next turn):** `GET /api/state?homes=&reserve=&soc=&drill=0|1&t=` →
  `{mode, asof, price, prc_mw, headroom_mw, action, target_mw, duration_h, reasons[3], backup_mwh_retained,
  gross_value_usd, plan:[{he, dam_price, mw}]}`.
