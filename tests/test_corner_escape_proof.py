import unittest
from scripts.corner_escape_proof import audit_objective_gift_skips, prove_corner_trap


def spawn(kind, cell, at=0):
    return {"kind": "spawn", "type": kind, "cell": {"x": cell[0], "y": cell[1]}, "time": at}


class CornerEscapeProofTests(unittest.TestCase):
    def test_upper_right_corner_persistent_girl_is_objectively_blocked(self):
        events = [spawn("girl", (17, 1)), spawn("gift", (17, 0), 33416.5)]
        proof = prove_corner_trap((17, 0), 33416.5, 47430.5, events)
        self.assertIsNotNone(proof)
        self.assertEqual(proof["free_neighbor_count"], 1)
        self.assertEqual(proof["blocked_neighbors"], [{"x": 17, "y": 1}])

    def test_corner_unblocked_is_unproven(self):
        self.assertIsNone(prove_corner_trap((17, 0), 100, 200, []))

    def test_middle_of_edge_is_not_a_corner_proof(self):
        self.assertIsNone(prove_corner_trap((5, 0), 100, 200, [spawn("girl", (5, 1))]))

    def test_girl_spawn_after_gift_does_not_prove_entire_lifetime(self):
        self.assertIsNone(prove_corner_trap((17, 0), 100, 200, [spawn("girl", (17, 1), 150)]))

    def test_girl_removed_before_expiry_invalidates_proof(self):
        events = [spawn("girl", (17, 1)), {"kind": "pickup", "type": "girl", "time": 150}]
        self.assertIsNone(prove_corner_trap((17, 0), 100, 200, events))

    def test_reset_during_lifetime_invalidates_proof(self):
        events = [spawn("girl", (17, 1)), {"kind": "reset", "time": 150}]
        self.assertIsNone(prove_corner_trap((17, 0), 100, 200, events))

    def test_missing_spawn_evidence_is_diagnostic_not_a_release_failure(self):
        expiry = {"kind": "expire", "type": "gift", "cell": {"x": 17, "y": 0}, "time": 200}
        audits, failures = audit_objective_gift_skips([expiry], [], [spawn("girl", (17, 1))])
        self.assertEqual(audits[0]["classification"], "not_independently_proven")
        self.assertEqual(failures, [])

    def test_audit_accepts_independently_proven_skip(self):
        gift = spawn("gift", (17, 0), 100)
        expiry = {"kind": "expire", "type": "gift", "cell": {"x": 17, "y": 0}, "time": 200}
        audits, failures = audit_objective_gift_skips([expiry], [gift], [spawn("girl", (17, 1)), gift, expiry])
        self.assertFalse(failures)
        self.assertEqual(audits[0]["classification"], "independently_proven")


if __name__ == "__main__":
    unittest.main()
