import unittest
from scripts.release_gate import evaluate_release


def passing():
    return {
        "seconds_requested":60,
        "start":{"ok":True},
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


def corner_events():
    cells = [(0,0),(17,0),(17,9),(0,9)]
    events = [
        {"kind":"spawn","type":"gift","cell":{"x":x,"y":y},"time":i*1000}
        for i,(x,y) in enumerate(cells)
    ]
    events.extend([
        {"kind":"pickup","type":"gift","time":5000},
        {"kind":"pickup","type":"gift","time":6000},
        {"kind":"pickup","type":"gift","time":7000},
        {"kind":"expire","type":"gift","cell":{"x":17,"y":0},"time":8000},
    ])
    return events


def set_corner_report(report):
    report["gift_spawns"] = 4
    report["gift_pickups"] = 3
    report["gift_expirations"] = [{"kind":"expire","type":"gift","cell":{"x":17,"y":0},"time":8000}]
    report["active_gifts"] = 0
    report["state"]["score"] = 1500
    report["simulator_events"] = corner_events()


class ReleaseGateTests(unittest.TestCase):
    def test_passing_e2e_evidence(self):
        self.assertEqual(evaluate_release(passing()), [])

    def test_no_input_is_failure(self):
        report=passing(); report["cdp_commands"]=0
        self.assertTrue(evaluate_release(report))

    def test_start_not_acknowledged_is_failure(self):
        report=passing(); report["start"]={"ok":False}
        self.assertIn("game start was not positively acknowledged", evaluate_release(report))

    def test_missing_trajectory_confirmation_is_failure(self):
        report=passing(); report["confirmed_turns"]=97
        self.assertIn("confirmed turns differ from observed trajectory turns", evaluate_release(report))

    def test_missing_live_worker_log_is_failure(self):
        report=passing(); report["log_source"]="storage-fallback"
        self.assertTrue(evaluate_release(report))

    def test_reverse_guard_blocking_internal_request_is_safe(self):
        report=passing(); report["reverse_guard"]=2
        report["simulator_events"]=[]
        self.assertEqual(evaluate_release(report), [])

    def test_actual_reverse_key_reaching_game_is_failure(self):
        report=passing()
        report["simulator_events"]=[{"kind":"reverse-rejected","key":"ArrowUp"}]
        self.assertIn("a reverse-direction key reached the game", evaluate_release(report))

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

    def test_ten_expirations_are_allowed(self):
        report=passing()
        report["gift_spawns"]=33
        report["gift_expirations"]=[{"kind":"expire","cell":{"x":17,"y":0},"time":i*1000} for i in range(10)]
        self.assertEqual(evaluate_release(report), [])

    def test_eleven_expirations_are_failure(self):
        report=passing()
        report["gift_spawns"]=34
        report["gift_expirations"]=[{"kind":"expire","cell":{"x":17,"y":0},"time":i*1000} for i in range(11)]
        self.assertIn("more than ten expired gifts in the release test", evaluate_release(report))

    def test_12_minute_run_must_exceed_70000_points(self):
        report=passing()
        report["seconds_requested"]=720
        report["state"]["time"]=720010
        report["wall_seconds_elapsed"]=720
        report["gift_pickups"]=140
        report["gift_spawns"]=140
        report["gift_expirations"]=[]
        report["state"]["score"]=70000
        self.assertIn("12-minute run did not exceed 70000 points", evaluate_release(report))

    def test_12_minute_run_over_70000_points_passes_score_gate(self):
        report=passing()
        report["seconds_requested"]=720
        report["state"]["time"]=720010
        report["wall_seconds_elapsed"]=720
        report["gift_pickups"]=141
        report["gift_spawns"]=141
        report["gift_expirations"]=[]
        report["state"]["score"]=70500
        self.assertNotIn("12-minute run did not exceed 70000 points", evaluate_release(report))

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

    def test_corner_scenario_requires_all_four_corners(self):
        report=passing()
        report["scenario"]="corners"
        set_corner_report(report)
        self.assertEqual(evaluate_release(report), [])

    def test_corner_scenario_fails_if_one_corner_not_exercised(self):
        report=passing()
        report["scenario"]="corners"
        set_corner_report(report)
        report["simulator_events"] = report["simulator_events"][:-5]
        self.assertTrue(any("all four corners" in x for x in evaluate_release(report)))

    def test_event_history_must_match_report_counts(self):
        report=passing()
        report["simulator_events"]=[{"kind":"spawn","type":"gift","cell":{"x":0,"y":0}}]
        self.assertTrue(any("event history" in x for x in evaluate_release(report)))

    def test_long_edge_scenario_requires_all_four_sides(self):
        report=passing()
        report["scenario"]="edge-gifts"
        report["seconds_requested"]=180
        report["state"]["time"]=180100
        report["wall_seconds_elapsed"]=180
        set_corner_report(report)
        self.assertEqual(evaluate_release(report), [])


if __name__ == "__main__":
    unittest.main()
