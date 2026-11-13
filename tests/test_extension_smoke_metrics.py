import unittest

from scripts.extension_smoke import count_confirmed_turns


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


if __name__ == "__main__":
    unittest.main()
