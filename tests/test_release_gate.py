import unittest
from copy import deepcopy
from scripts.release_gate import evaluate_release


def passing():
    return {
        "seconds_requested":60,
        "state":{"mode":"playing","time":60010,"score":11500},
        "cdp_commands":100,
        "confirmed_turns":98,
        "actual_turns":98,
        "log_source":"worker-memory",
        "reverse_guard":0,
        "autopilot_abort":False,
        "game_over_events":[],
        "page_errors":[],
        "gift_spawns":24,
        "gift_pickups":23,
        "gift_expirations":[{"kind":"expire","cell":{"x":17,"y":0},"time":47430}],
        "active_gifts":0,
        "non_gift_pickups":[],
        "wall_seconds_elapsed":60.0,
    }


class ReleaseGateTests(unittest.TestCase):
    def test_passing_e2e_evidence(self):
        self.assertEqual(evaluate_release(passing()), [])

    def test_no_input_is_failure(self):
        report=passing(); report["cdp_commands"]=0
        self.assertTrue(evaluate_release(report))

    def test_missing_trajectory_confirmation_is_failure(self):
        report=passing(); report["confirmed_turns"]=97
        self.assertIn("confirmed turns differ from observed trajectory turns", evaluate_release(report))

    def test_missing_live_worker_log_is_failure(self):
        report=passing(); report["log_source"]="storage-fallback"
        self.assertTrue(evaluate_release(report))

    def test_reverse_guard_is_failure(self):
        report=passing(); report["reverse_guard"]=1
        self.assertTrue(evaluate_release(report))

    def test_game_over_is_failure(self):
        report=passing(); report["game_over_events"]=[{"kind":"game-over"}]
        report["state"]["mode"]="over"
        self.assertTrue(evaluate_release(report))

    def test_pause_is_failure(self):
        report=passing(); report["state"]["mode"]="paused"
        self.assertTrue(evaluate_release(report))

    def test_early_end_is_failure(self):
        report=passing(); report["state"]["time"]=58900
        self.assertTrue(evaluate_release(report))

    def test_early_wall_clock_end_is_failure(self):
        report=passing(); report["wall_seconds_elapsed"]=55
        self.assertTrue(evaluate_release(report))

    def test_non_gift_pickup_is_failure(self):
        report=passing(); report["non_gift_pickups"]=["girl"]
        self.assertTrue(evaluate_release(report))

    def test_unjustified_expiry_is_failure(self):
        report=passing()
        self.assertTrue(evaluate_release(report,["unjustified expiry"],[]))
        self.assertTrue(evaluate_release(report,[],["unproven escape"]))

    def test_three_expirations_are_failure(self):
        report=passing()
        report["gift_spawns"]=26
        report["gift_expirations"] = report["gift_expirations"]*3
        self.assertTrue(evaluate_release(report))

    def test_missing_pickup_is_failure(self):
        report=passing(); report["gift_pickups"]=0
        self.assertTrue(evaluate_release(report))

    def test_missing_javascript_errors_are_failure(self):
        report=passing(); report["page_errors"]=["Uncaught error"]
        self.assertTrue(evaluate_release(report))

    def test_score_and_accounting_mismatch_are_failures(self):
        report=passing(); report["state"]["score"]=12000
        report["gift_spawns"]=25
        failures=evaluate_release(report)
        self.assertTrue(any("score" in x for x in failures))
        self.assertTrue(any("accounting" in x for x in failures))


if __name__ == "__main__":
    unittest.main()
