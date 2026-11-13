import unittest

from scripts.extension_smoke import count_confirmed_turns
from scripts.gift_skip_policy import assess_expired_gift_skips


class ConfirmedTurnMetricsTests(unittest.TestCase):
    def test_counts_trajectory_confirmation_but_not_browser_acknowledgement(self):
        log = "\n".join([
            "ВВОД ПОДТВЕРЖДЁН CDP: команда #1 ArrowDown",
            "ПОВОРОТ ПОДТВЕРЖДЁН БРАУЗЕРОМ: команда #1 ArrowDown; ждём фактическое изменение курса",
            "ПОВОРОТ ПОДТВЕРЖДЁН ПО ТРАЕКТОРИИ: ArrowDown (вниз); движение 14px",
            "ПОВОРОТ ПОДТВЕРЖДЁН БРАУЗЕРОМ: команда #2 ArrowLeft; ждём фактическое изменение курса",
            "ПОВОРОТ ПОДТВЕРЖДЁН ПО ТРАЕКТОРИИ: ArrowLeft (влево); движение 12px",
        ])
        self.assertEqual(count_confirmed_turns(log), 2)

    def test_supports_legacy_generic_confirmation(self):
        log = "ПОВОРОТ ПОДТВЕРЖДЁН: ArrowUp (вверх)"
        self.assertEqual(count_confirmed_turns(log), 1)

    def test_browser_acknowledgement_alone_is_not_a_confirmed_turn(self):
        log = "ПОВОРОТ ПОДТВЕРЖДЁН БРАУЗЕРОМ: команда #1 ArrowRight; ждём фактическое изменение курса"
        self.assertEqual(count_confirmed_turns(log), 0)

    def test_empty_log_has_no_confirmed_turns(self):
        self.assertEqual(count_confirmed_turns(""), 0)


class GiftSkipPolicyTests(unittest.TestCase):
    STARTED_AT = "2026-11-13T15:00:20+0300"

    def assess(self, cell, spawn_ms, expiry_ms, log_lines):
        expiration = {"time": expiry_ms, "cell": cell}
        spawn = {"time": spawn_ms, "cell": cell}
        return assess_expired_gift_skips(
            [expiration], [spawn], "\n".join(log_lines), self.STARTED_AT
        )

    def test_matching_no_safe_route_for_same_live_gift_is_accepted(self):
        diagnostics, accepted, failures = self.assess(
            {"x": 17, "y": 0}, 33416.7, 47430.6,
            ["15:01:07 ЦЕЛИ: gift@914,144 +500; выбрана нет; статус=not-selected,причина=no-safe-route,выход=0"],
        )
        self.assertEqual(accepted, 1)
        self.assertEqual(failures, [])
        self.assertEqual(diagnostics[0]["classification"], "accepted_no_safe_route")
        self.assertEqual(diagnostics[0]["target_pixel"], {"x": 914, "y": 144})

    def test_no_safe_route_for_another_cell_does_not_justify_skip(self):
        diagnostics, accepted, failures = self.assess(
            {"x": 17, "y": 0}, 33416.7, 47430.6,
            ["15:01:07 ЦЕЛИ: gift@874,144 +500; выбрана нет; статус=not-selected,причина=no-safe-route,выход=0"],
        )
        self.assertEqual(accepted, 0)
        self.assertEqual(diagnostics[0]["classification"], "unjustified_expiry")
        self.assertTrue(any("without matching no-safe-route evidence" in item for item in failures))

    def test_evidence_after_expiry_does_not_justify_skip(self):
        diagnostics, accepted, failures = self.assess(
            {"x": 17, "y": 0}, 33416.7, 47430.6,
            ["15:01:09 ЦЕЛИ: gift@914,144 +500; выбрана нет; статус=not-selected,причина=no-safe-route,выход=0"],
        )
        self.assertEqual(accepted, 0)
        self.assertEqual(diagnostics[0]["classification"], "unjustified_expiry")
        self.assertTrue(failures)

    def test_evidence_before_gift_spawn_does_not_justify_skip(self):
        diagnostics, accepted, failures = self.assess(
            {"x": 17, "y": 0}, 33416.7, 47430.6,
            ["15:00:30 ЦЕЛИ: gift@914,144 +500; выбрана нет; статус=not-selected,причина=no-safe-route,выход=0"],
        )
        self.assertEqual(accepted, 0)
        self.assertEqual(diagnostics[0]["classification"], "unjustified_expiry")
        self.assertTrue(failures)

    def test_two_objective_skips_are_allowed(self):
        cells = [{"x": 0, "y": 0}, {"x": 1, "y": 0}]
        expirations = [{"time": 12000, "cell": cell} for cell in cells]
        spawns = [{"time": 1000, "cell": cell} for cell in cells]
        lines = [
            "15:00:25 ЦЕЛИ: gift@234,144 +500; выбрана нет; причина=no-safe-route",
            "15:00:25 ЦЕЛИ: gift@274,144 +500; выбрана нет; причина=no-safe-route",
        ]
        diagnostics, accepted, failures = assess_expired_gift_skips(
            expirations, spawns, "\n".join(lines), self.STARTED_AT
        )
        self.assertEqual(accepted, 2)
        self.assertEqual(len(diagnostics), 2)
        self.assertEqual(failures, [])

    def test_three_objective_skips_exceed_the_allowance(self):
        cells = [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 2, "y": 0}]
        expirations = [{"time": 12000, "cell": cell} for cell in cells]
        spawns = [{"time": 1000, "cell": cell} for cell in cells]
        lines = [
            "15:00:25 ЦЕЛИ: gift@234,144 +500; выбрана нет; причина=no-safe-route",
            "15:00:25 ЦЕЛИ: gift@274,144 +500; выбрана нет; причина=no-safe-route",
            "15:00:25 ЦЕЛИ: gift@314,144 +500; выбрана нет; причина=no-safe-route",
        ]
        diagnostics, accepted, failures = assess_expired_gift_skips(
            expirations, spawns, "\n".join(lines), self.STARTED_AT
        )
        self.assertEqual(accepted, 3)
        self.assertEqual(len(diagnostics), 3)
        self.assertTrue(any("exceed the allowance of 2" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
