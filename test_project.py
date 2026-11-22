import unittest
from project import analyze


def event(eid, kind, amounts, phase="Harbor"):
    return {"id": eid, "phase": phase, "kind": kind, "amounts": amounts}


class EconomyTests(unittest.TestCase):
    def test_multi_resource_failure_is_atomic(self):
        result = analyze({"opening": {"ore": 3, "keys": 1}, "events": [event("gate", "spend", {"ore": 3, "keys": 2})]})
        self.assertEqual(result["closing_balances"], {"ore": 3, "keys": 1})
        self.assertEqual(result["phases"]["Harbor"]["shortfalls"], {"keys": 1})
        self.assertEqual([r["Applied change"] for r in result["rows"]], [0, 0])

    def test_grant_changes_only_later_spends(self):
        result = analyze({"opening": {"ore": 0}, "events": [event("early", "spend", {"ore": 2}),
                          event("gift", "grant", {"ore": 4}), event("later", "spend", {"ore": 2}, "Coast")]})
        self.assertEqual(result["closing_balances"]["ore"], 2)
        self.assertEqual(result["rows"][0]["Status"], "Blocked")
        self.assertEqual(result["rows"][2]["Status"], "Applied")

    def test_repeated_shortfalls_are_summed_by_phase_without_mixing_resources(self):
        result = analyze({"opening": {"a": 0, "b": 0}, "events": [
            event("x", "spend", {"a": 2, "b": 7}), event("y", "spend", {"a": 3})]})
        self.assertEqual(result["phases"]["Harbor"]["shortfalls"], {"a": 5, "b": 7})

    def test_invalid_amount_and_duplicate_id(self):
        for events in ([event("x", "grant", {"a": True})], [event("x", "grant", {"a": 1})] * 2):
            with self.subTest(events=events), self.assertRaises(ValueError):
                analyze({"opening": {"a": 0}, "events": events})
