import sys
import types
import unittest
import json
import threading
import urllib.request
from unittest.mock import patch

# Sol's build branch may be tested before Opus's engine branch is merged.
try:
    import fleetpilot.engine  # noqa: F401
except ModuleNotFoundError:
    stub = types.ModuleType("fleetpilot.engine")
    stub.run = lambda *args, **kwargs: {}
    sys.modules["fleetpilot.engine"] = stub

import app


class InputTests(unittest.TestCase):
    def test_default_live_request_has_no_failure(self):
        values = app.parse_inputs({})
        self.assertFalse(values["drill"])
        self.assertEqual(values["fail"], 0)

    def test_drill_defaults_to_fifteen_percent_failure(self):
        values = app.parse_inputs({"drill": ["1"]})
        self.assertTrue(values["drill"])
        self.assertEqual(values["fail"], 0.15)

    def test_rejects_out_of_bounds_and_unknown_zone(self):
        invalid = [
            {"homes": ["5001"]},
            {"reserve": [".91"]},
            {"fail": [".51"]},
            {"drill": ["yes"]},
            {"zone": ["lzMoon"]},
        ]
        for query in invalid:
            with self.subTest(query=query), self.assertRaises(ValueError):
                app.parse_inputs(query)


class ApiIntegrationTests(unittest.TestCase):
    def test_drill_endpoint_runs_real_engine_contract(self):
        rt = [{"t": "12:30", "price": 23.16}]
        dam = [{"t": f"{hour:02d}:00", "price": 20.0 + hour * 2} for hour in range(1, 25)]
        meta = {"mode": "CACHED", "last_updated": "fixture", "feed": "test", "zone": "lzAen"}

        with patch.object(app, "cached_prices", return_value=(rt, dam, meta)), \
             patch.object(app.Handler, "log_message", lambda *args: None):
            server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/api/state?drill=1&fail=.15"
                with urllib.request.urlopen(url, timeout=2) as response:
                    payload = json.load(response)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        self.assertEqual(payload["mode"], "DRILL")
        self.assertEqual(payload["source"]["mode"], "CACHED")
        self.assertEqual(payload["decision"]["action"], "DISCHARGE")
        self.assertEqual(payload["prices"], {"rt": rt, "dam": dam})
        self.assertGreater(payload["dispatch"]["failed_homes"], 0)
        self.assertEqual(payload["dispatch"]["shortfall_mw"], 0)
        self.assertTrue(all(payload["invariants"].values()))
        self.assertEqual([event["step"] for event in payload["events"]],
                         ["decide", "allocate", "failure", "redispatch"])


if __name__ == "__main__":
    unittest.main()
