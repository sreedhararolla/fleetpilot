import unittest

from fleetpilot.engine import allocate, decide, percentile, redispatch, run
from fleetpilot.fleet import make_fleet

DAM = [{"t": f"{h:02d}:00", "price": p} for h, p in enumerate(
    [30, 28, 27, 26, 26, 28, 35, 40, 38, 32, 30, 29, 30, 33, 38, 45, 60, 90, 120, 80, 55, 45, 38, 33], start=1)]
RT_MID = [{"t": "12:00", "price": 36.0}]
RT_LOW = [{"t": "03:00", "price": 10.0}]
RT_HIGH = [{"t": "19:00", "price": 150.0}]


class TestDecide(unittest.TestCase):
    def test_percentile(self):
        self.assertEqual(percentile([1, 2, 3, 4, 5], 0.5), 3)
        self.assertAlmostEqual(percentile([0, 10], 0.25), 2.5)

    def test_actions(self):
        prices = [p["price"] for p in DAM]
        self.assertEqual(decide(150, prices)[0], "DISCHARGE")
        self.assertEqual(decide(10, prices)[0], "CHARGE")
        self.assertEqual(decide(36, prices)[0], "HOLD")

    def test_intensity_capped(self):
        _, k, *_ = decide(1e6, [p["price"] for p in DAM])
        self.assertLessEqual(k, 0.70)


class TestCoordinator(unittest.TestCase):
    def test_allocate_respects_headroom(self):
        head = {0: 5.0, 1: 10.0}
        alloc = allocate(head, 1000.0)
        self.assertEqual(alloc, head)

    def test_redispatch_moves_lost_power(self):
        head = {0: 10.0, 1: 10.0, 2: 10.0}
        alloc = allocate(head, 15.0)
        new, lost, short, boosted = redispatch(alloc, head, {0})
        self.assertEqual(new[0], 0.0)
        self.assertAlmostEqual(sum(new.values()), 15.0)
        self.assertEqual(short, 0.0)
        self.assertEqual(boosted, {1, 2})

    def test_redispatch_reports_shortfall(self):
        head = {0: 10.0, 1: 10.0}
        new, lost, short, _ = redispatch({0: 10.0, 1: 10.0}, head, {0})
        self.assertAlmostEqual(short, 10.0)
        self.assertAlmostEqual(sum(new.values()), 10.0)

    def test_fleet_is_seeded(self):
        a, b = make_fleet(50, 0.2, seed=3), make_fleet(50, 0.2, seed=3)
        self.assertEqual([h.soc_kwh for h in a], [h.soc_kwh for h in b])


class TestRun(unittest.TestCase):
    def assert_invariants(self, out):
        self.assertTrue(all(out["invariants"].values()), out["invariants"])

    def test_default_drill_recovers(self):
        out = run(RT_MID, DAM, homes=1000, reserve=0.2, fail=0.15, drill=True)
        d = out["dispatch"]
        self.assertEqual(out["decision"]["action"], "DISCHARGE")
        self.assertTrue(out["decision"]["reason"].startswith("DRILL:"))
        self.assertGreater(d["failed_homes"], 0)
        self.assertLess(d["after_failure_mw"], d["target_mw"])
        self.assertAlmostEqual(d["after_redispatch_mw"], d["target_mw"], places=2)
        self.assertEqual(d["shortfall_mw"], 0.0)
        self.assertEqual([e["step"] for e in out["events"]], ["decide", "allocate", "failure", "redispatch"])
        self.assert_invariants(out)

    def test_extreme_failure_is_honest(self):
        out = run(RT_MID, DAM, homes=200, reserve=0.2, fail=0.5, drill=True)
        d = out["dispatch"]
        self.assertAlmostEqual(d["after_redispatch_mw"] + d["shortfall_mw"], d["target_mw"], places=2)
        self.assert_invariants(out)

    def test_no_failure_keys_consistent(self):
        out = run(RT_HIGH, DAM, fail=0)
        d = out["dispatch"]
        self.assertEqual(d["failed_homes"], 0)
        self.assertEqual(d["allocated_mw"], d["after_failure_mw"])
        self.assertEqual(d["allocated_mw"], d["after_redispatch_mw"])
        self.assertEqual(len(out["events"]), 2)

    def test_hold_is_zero(self):
        out = run(RT_MID, DAM)
        self.assertEqual(out["decision"]["action"], "HOLD")
        self.assertEqual(out["dispatch"]["after_redispatch_mw"], 0.0)
        self.assertEqual(out["value"]["gross_usd_per_h"], 0.0)

    def test_charge_never_overfills(self):
        out = run(RT_LOW, DAM, fail=0.15)
        self.assertEqual(out["decision"]["action"], "CHARGE")
        self.assertLess(out["value"]["gross_usd_per_h"], 0)
        self.assertTrue(all(h["kw_after"] <= 0 for h in out["homes_sample"]))
        self.assert_invariants(out)

    def test_higher_reserve_costs_revenue(self):
        lo = run(RT_HIGH, DAM, reserve=0.2, fail=0)
        hi = run(RT_HIGH, DAM, reserve=0.5, fail=0)
        self.assertLess(hi["dispatch"]["target_mw"], lo["dispatch"]["target_mw"])
        self.assertGreater(hi["value"]["reserve_cost_usd_per_h"], lo["value"]["reserve_cost_usd_per_h"])
        self.assert_invariants(hi)

    def test_conservation_across_seeds(self):
        for seed in range(5):
            for rt, drill in ((RT_HIGH, False), (RT_LOW, False), (RT_MID, True)):
                out = run(rt, DAM, homes=300, reserve=0.3, fail=0.25, drill=drill, seed=seed)
                d = out["dispatch"]
                self.assertAlmostEqual(d["after_redispatch_mw"] + d["shortfall_mw"], d["target_mw"], places=2)
                self.assert_invariants(out)

    def test_charge_failure_recovers(self):
        out = run(RT_LOW, DAM, fail=0.15)
        d = out["dispatch"]
        self.assertGreater(d["failed_homes"], 0)
        self.assertAlmostEqual(d["after_redispatch_mw"], d["target_mw"], places=2)
        self.assertEqual(d["shortfall_mw"], 0.0)

    def test_reports_homes_below_requested_floor(self):
        out = run(RT_HIGH, DAM, reserve=0.5, fail=0)
        f = out["fleet"]
        self.assertGreater(f["homes_below_floor"], 0)
        self.assertGreater(f["reserve_deficit_mwh"], 0)
        self.assertAlmostEqual(f["protected_mwh"] + f["reserve_deficit_mwh"], f["reserve_mwh"], places=2)
        self.assertEqual(out["dispatch"]["duration_h"], 1.0)

    def test_rejects_bad_inputs(self):
        for kwargs in ({"homes": 0}, {"reserve": 1.5}, {"fail": -0.1}):
            with self.assertRaises(ValueError):
                run(RT_MID, DAM, **kwargs)
        with self.assertRaises(ValueError):
            run(RT_MID, [])

    def test_sample_size(self):
        out = run(RT_HIGH, DAM, homes=5000, fail=0.15)
        self.assertLessEqual(len(out["homes_sample"]), 200)
        self.assertTrue(any(h["status"] == "failed" for h in out["homes_sample"]))


if __name__ == "__main__":
    unittest.main()
