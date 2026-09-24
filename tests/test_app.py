import sys
import types
import unittest

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


if __name__ == "__main__":
    unittest.main()
