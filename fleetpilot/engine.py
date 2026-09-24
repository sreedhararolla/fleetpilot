"""FleetPilot coordinator: decide a fleet target from ERCOT prices, allocate it across homes,
survive a failure of dispatched homes by re-dispatching, and check the per-home invariants."""
import math

from .fleet import make_fleet

DURATION_H = 1.0          # each dispatch block is sustained for one hour
MAX_INTENSITY = 0.70      # D4: never ask for more than 70% of available headroom
MIN_INTENSITY = 0.40
DRILL_PRICE = 2500.0      # $/MWh synthetic scarcity spike
SAMPLE_SIZE = 200
EPS = 1e-6


def percentile(values, q):
    """Linear-interpolated percentile, q in [0, 1]."""
    xs = sorted(values)
    if not xs:
        raise ValueError("no prices")
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def decide(price, dam_prices, drill=False):
    """RT price vs today's DAM distribution -> (action, intensity, reason, p25, p75)."""
    p25, p75 = percentile(dam_prices, 0.25), percentile(dam_prices, 0.75)
    spread = max(p75 - p25, 1.0)
    prefix = "DRILL: " if drill else ""
    if price >= p75:
        k = min(1.0, (price - p75) / spread)
        return ("DISCHARGE", MIN_INTENSITY + (MAX_INTENSITY - MIN_INTENSITY) * k,
                f"{prefix}RT ${price:,.2f} ≥ today's DAM p75 ${p75:,.2f}: export while it pays", p25, p75)
    if price <= p25:
        k = min(1.0, (p25 - price) / spread)
        return ("CHARGE", MIN_INTENSITY + (MAX_INTENSITY - MIN_INTENSITY) * k,
                f"{prefix}RT ${price:,.2f} ≤ today's DAM p25 ${p25:,.2f}: store cheap energy", p25, p75)
    return ("HOLD", 0.0,
            f"{prefix}RT ${price:,.2f} is inside today's DAM band ${p25:,.2f}–${p75:,.2f}: hold charge", p25, p75)


def allocate(headroom, target_kw):
    """Split target_kw across homes in proportion to their headroom (never exceeds any home's headroom)."""
    total = sum(headroom.values())
    if total <= EPS or target_kw <= EPS:
        return {hid: 0.0 for hid in headroom}
    share = min(1.0, target_kw / total)
    return {hid: h * share for hid, h in headroom.items()}


def fail_homes(alloc, fail):
    """Deterministically fail `fail` fraction of actively dispatched homes, lowest IDs first."""
    active = sorted(hid for hid, kw in alloc.items() if kw > EPS)
    return set(active[:math.ceil(len(active) * fail)]) if fail > 0 else set()


def redispatch(alloc, headroom, failed):
    """Zero failed homes and push their lost kW onto healthy homes' spare headroom.
    Returns (new_alloc, lost_kw, shortfall_kw, boosted_ids)."""
    new = dict(alloc)
    lost = sum(new[hid] for hid in failed)
    for hid in failed:
        new[hid] = 0.0
    spare = {hid: headroom[hid] - new[hid] for hid in new if hid not in failed}
    total_spare = sum(spare.values())
    moved = min(lost, total_spare)
    boosted = set()
    if moved > EPS:
        for hid, s in spare.items():
            add = s * moved / total_spare
            if add > EPS:
                new[hid] += add
                boosted.add(hid)
    return new, lost, max(0.0, lost - moved), boosted


def run(rt, dam, homes=1000, reserve=0.2, fail=0.15, drill=False, seed=7):
    if homes < 1 or not 0 <= reserve <= 1 or not 0 <= fail <= 1:
        raise ValueError("homes must be >= 1; reserve and fail must be within [0, 1]")
    if not dam:
        raise ValueError("DAM prices are required")
    dam_prices = [p["price"] for p in dam]
    now = dict(rt[-1]) if rt else dict(dam[0])
    if drill:
        now["price"] = DRILL_PRICE
    price = now["price"]

    fleet = make_fleet(homes, reserve, seed)
    action, intensity, reason, p25, p75 = decide(price, dam_prices, drill)
    sign = {"DISCHARGE": 1.0, "CHARGE": -1.0, "HOLD": 0.0}[action]

    if action == "CHARGE":
        headroom = {h.id: h.charge_headroom_kw(DURATION_H) for h in fleet}
    else:
        headroom = {h.id: h.discharge_headroom_kw(DURATION_H) for h in fleet}
    target_kw = intensity * sum(headroom.values()) if sign else 0.0

    alloc = allocate(headroom, target_kw)
    failed = fail_homes(alloc, fail)
    after_fail_kw = sum(kw for hid, kw in alloc.items() if hid not in failed)
    final, lost, shortfall, boosted = redispatch(alloc, headroom, failed)
    delivered_kw = sum(final.values())

    events = [{"step": "decide", "msg": f"{action} target {target_kw / 1000:.2f} MW — {reason}"},
              {"step": "allocate", "msg": f"{sum(1 for kw in alloc.values() if kw > EPS)} homes dispatched "
                                          f"for {sum(alloc.values()) / 1000:.2f} MW, split by headroom"}]
    if failed:
        events.append({"step": "failure", "msg": f"{len(failed)} dispatched homes went offline: "
                                                 f"-{lost / 1000:.2f} MW"})
        tail = f", shortfall {shortfall / 1000:.2f} MW" if shortfall > EPS else ", target met"
        events.append({"step": "redispatch", "msg": f"{len(boosted)} healthy homes picked up "
                                                    f"{(lost - shortfall) / 1000:.2f} MW{tail}"})

    by_id = {h.id: h for h in fleet}
    below_floor = over_power = over_cap = False
    for hid, kw in final.items():
        h = by_id[hid]
        post = h.soc_kwh - sign * kw * DURATION_H
        below_floor |= sign > 0 and kw > EPS and post < h.floor_kwh - EPS  # idle homes already under floor are exempt
        over_cap |= sign < 0 and post > h.cap_kwh + EPS
        over_power |= kw > h.max_kw + EPS
    invariants = {"no_home_below_floor": not below_floor and not over_cap,
                  "no_home_over_power": not over_power,
                  "failed_homes_zero_output": all(final[hid] == 0.0 for hid in failed)}

    step = max(1, homes // SAMPLE_SIZE)
    sample = []
    for h in fleet[::step][:SAMPLE_SIZE]:
        status = "failed" if h.id in failed else "boosted" if h.id in boosted else "ok"
        sample.append({"id": h.id, "soc_pct": round(100 * h.soc_kwh / h.cap_kwh, 1),
                       "floor_pct": round(100 * reserve, 1),
                       "kw_before": round(sign * alloc[h.id], 2), "kw_after": round(sign * final[h.id], 2),
                       "status": status})

    reserve_cost = 0.0
    if action == "DISCHARGE":
        no_reserve_kw = sum(min(h.max_kw, h.soc_kwh / DURATION_H) for h in fleet)
        reserve_cost = intensity * (no_reserve_kw - sum(headroom.values())) / 1000 * price

    mw = lambda kw: round(kw / 1000, 3)
    return {
        "now": now,
        "decision": {"action": action, "target_mw": mw(target_kw), "reason": reason,
                     "dam_p25": round(p25, 2), "dam_p75": round(p75, 2)},
        "fleet": {"homes": homes, "online_before": homes, "online_after": homes - len(failed),
                  "power_mw": mw(sum(h.max_kw for h in fleet)),
                  "energy_mwh": mw(sum(h.soc_kwh for h in fleet)),
                  "reserve_mwh": mw(sum(h.floor_kwh for h in fleet)),  # requested floor total
                  "protected_mwh": mw(sum(min(h.soc_kwh, h.floor_kwh) for h in fleet)),  # actually held
                  "homes_below_floor": sum(1 for h in fleet if h.soc_kwh < h.floor_kwh),
                  "reserve_deficit_mwh": mw(sum(max(0.0, h.floor_kwh - h.soc_kwh) for h in fleet))},
        "dispatch": {"target_mw": mw(target_kw), "duration_h": DURATION_H, "allocated_mw": mw(sum(alloc.values())),
                     "after_failure_mw": mw(after_fail_kw), "after_redispatch_mw": mw(delivered_kw),
                     "shortfall_mw": mw(shortfall), "failed_homes": len(failed), "boosted_homes": len(boosted)},
        "events": events,
        "homes_sample": sample,
        "invariants": invariants,
        "value": {"gross_usd_per_h": round(sign * delivered_kw / 1000 * price, 2),
                  "reserve_cost_usd_per_h": round(reserve_cost, 2)},
    }
