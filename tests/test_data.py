import io
import json
import unittest
from unittest.mock import patch

from fleetpilot import data


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class DataTests(unittest.TestCase):
    def setUp(self):
        self.fixture = data.FIXTURE_PATH.read_bytes()

    def test_parses_live_payload_to_frozen_shape(self):
        with patch.object(data, "urlopen", return_value=FakeResponse(self.fixture)):
            rt, dam, meta = data.load_prices()
        self.assertEqual(meta["mode"], "LIVE")
        self.assertEqual(meta["zone"], "lzAen")
        self.assertEqual(rt[-1], {"t": "12:30", "price": 23.16})
        self.assertEqual(dam[-1], {"t": "24:00", "price": 39.34})

    def test_network_failure_uses_cached_fixture(self):
        with patch.object(data, "urlopen", side_effect=OSError("offline")):
            rt, dam, meta = data.load_prices()
        self.assertEqual(meta["mode"], "CACHED")
        self.assertIn("offline", meta["fallback_reason"])
        self.assertTrue(rt)
        self.assertEqual(len(dam), 24)

    def test_malformed_live_payload_uses_cached_fixture(self):
        malformed = json.dumps({"rtSppData": [{"intervalEnding": "12:00", "lzAen": None}]}).encode()
        with patch.object(data, "urlopen", return_value=FakeResponse(malformed)):
            _, _, meta = data.load_prices()
        self.assertEqual(meta["mode"], "CACHED")

    def test_valid_feed_without_timestamp_is_explicitly_unknown(self):
        payload = json.loads(self.fixture)
        payload.pop("lastUpdated")
        with patch.object(data, "urlopen", return_value=FakeResponse(json.dumps(payload).encode())):
            _, _, meta = data.load_prices()
        self.assertEqual(meta["mode"], "LIVE")
        self.assertEqual(meta["last_updated"], "Unknown")

    def test_unknown_zone_is_rejected_before_network(self):
        with patch.object(data, "urlopen") as opener:
            with self.assertRaisesRegex(ValueError, "unsupported zone"):
                data.load_prices("notAZone")
        opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
