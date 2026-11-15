import datetime
import unittest

from relay import Buttons, parse_report


class RelayTests(unittest.TestCase):
    def test_navigation_masks(self):
        for mask, name in ((0x200, "up"), (0x800, "down"), (0x400, "right"), (0x1000, "left")):
            self.assertEqual(Buttons().update(mask, 0), [name])

    def test_select_tap_is_sent_on_release_not_press(self):
        state = Buttons()
        self.assertEqual(state.update(0x8, 0), [])
        self.assertEqual(state.update(0x8, 0.1), [])
        self.assertEqual(state.repeat(0.1), [])
        self.assertEqual(state.update(0, 0.15), ["select"])

    def test_select_hold_is_sent_once_without_an_initial_click(self):
        state = Buttons()
        self.assertEqual(state.update(0x8, 0), [])
        self.assertEqual(state.repeat(0.24), [])
        self.assertEqual(state.repeat(0.25), ["select_hold"])
        self.assertEqual(state.repeat(3), [])
        self.assertEqual(state.update(0, 3.1), [])

    def test_select_release_at_hold_threshold_sends_hold_once(self):
        state = Buttons()
        state.update(0x8, 0)
        self.assertEqual(state.update(0, 0.25), ["select_hold"])
        self.assertEqual(state.repeat(1), [])

    def test_select_tap_works_after_a_hold(self):
        state = Buttons()
        state.update(0x8, 0)
        state.repeat(0.7)
        state.update(0, 0.8)
        self.assertEqual(state.update(0x8, 1), [])
        self.assertEqual(state.update(0, 1.1), ["select"])

    def test_select_just_below_threshold_remains_a_normal_click(self):
        state = Buttons()
        state.update(0x8, 0)
        self.assertEqual(state.update(0, 0.249), ["select"])
        self.assertEqual(state.repeat(0.3), [])

    def test_disconnect_discards_pending_select_without_a_ghost_click(self):
        state = Buttons()
        state.update(0x8, 0)
        state.clear()
        self.assertEqual(state.repeat(2), [])
        self.assertEqual(state.update(0, 2), [])

    def test_select_and_home_hold_state_are_independent(self):
        state = Buttons()
        state.update(0x8, 0)
        state.update(0x9, 0.2)
        self.assertEqual(state.repeat(0.25), ["select_hold"])
        self.assertEqual(state.repeat(0.9), ["control_center"])
        self.assertEqual(state.update(0, 1), [])

    def test_press_is_not_duplicated(self):
        state = Buttons()
        self.assertEqual(state.update(0x100, 0), ["play_pause"])
        self.assertEqual(state.update(0x100, 0.1), [])
        self.assertEqual(state.update(0, 0.2), [])
        self.assertEqual(state.update(0x100, 0.3), ["play_pause"])

    def test_hold_delay_repeat_and_release(self):
        state = Buttons()
        state.update(0x200, 0)
        self.assertEqual(state.repeat(0.3), [])
        self.assertEqual(state.repeat(0.35), ["up"])
        self.assertEqual(state.repeat(0.4), [])
        state.update(0, 0.45)
        self.assertEqual(state.repeat(0.6), [])

    def test_missing_release_is_bounded(self):
        state = Buttons()
        state.update(0x200, 0)
        self.assertEqual(state.repeat(3), [])
        self.assertEqual(state.repeat(5), [])

    def test_playback_and_home_never_repeat(self):
        state = Buttons()
        state.update(0x101, 0)
        self.assertEqual(state.repeat(0.5), [])

    def test_microphone_unknown_ignored(self):
        self.assertEqual(Buttons().update(0xE020, 0), [])

    def test_power_tap_opens_menu_only_on_release(self):
        state = Buttons()
        self.assertEqual(state.update(0x10, 0), [])
        self.assertEqual(state.repeat(0.7), [])
        self.assertEqual(state.update(0, 0.8), ["power_menu"])

    def test_power_hold_suspends_once_without_waking(self):
        state = Buttons()
        self.assertEqual(state.update(0x10, 0), [])
        self.assertEqual(state.repeat(0.99), [])
        self.assertEqual(state.repeat(1), ["suspend"])
        self.assertEqual(state.repeat(4), [])
        self.assertEqual(state.update(0, 4.1), [])

    def test_power_release_at_threshold_suspends(self):
        state = Buttons()
        state.update(0x10, 0)
        self.assertEqual(state.update(0, 1), ["suspend"])

    def test_disconnect_drops_pending_power(self):
        state = Buttons()
        state.update(0x10, 0)
        state.clear()
        self.assertEqual(state.repeat(2), [])
        self.assertEqual(state.update(0, 2), [])

    def test_power_can_be_tapped_after_suspending(self):
        state = Buttons()
        state.update(0x10, 0)
        state.repeat(1)
        state.update(0, 1.1)
        state.update(0x10, 2)
        self.assertEqual(state.update(0, 2.2), ["power_menu"])

    def test_power_and_home_use_independent_thresholds(self):
        state = Buttons()
        state.update(0x11, 0)
        self.assertEqual(state.repeat(0.65), ["control_center"])
        self.assertEqual(state.repeat(1), ["suspend"])
        self.assertEqual(state.update(0, 1.1), [])

    def test_disconnect_clears_hold(self):
        state = Buttons()
        state.update(0x200, 0)
        state.clear()
        self.assertEqual(state.repeat(0.5), [])

    def test_fresh_report(self):
        line = "2026-11-13T22:54:56.610Z input report_id=0xFB raw=00 02 | buttons=Up"
        now = datetime.datetime.fromisoformat("2026-11-13T22:54:56.700+00:00").timestamp()
        self.assertEqual(parse_report(line, now), 0x200)
        self.assertIsNone(parse_report(line, now + 1))
        self.assertIsNone(parse_report(line, now - 1))

    def test_other_reports_ignored(self):
        self.assertIsNone(
            parse_report("2026-11-13T22:54:56.610Z input report_id=0xFC raw=00 02 | touch", 0)
        )
        self.assertIsNone(parse_report("unrelated or malformed", 0))

    def test_home_tap_waits_for_release(self):
        state = Buttons()
        self.assertEqual(state.update(1, 0), [])
        self.assertEqual(state.repeat(0.3), [])
        self.assertEqual(state.update(0, 0.4), ["home"])

    def test_home_hold_opens_control_center_once(self):
        state = Buttons()
        self.assertEqual(state.update(1, 0), [])
        self.assertEqual(state.repeat(0.65), ["control_center"])
        self.assertEqual(state.repeat(1), [])
        self.assertEqual(state.update(0, 1.2), [])

    def test_home_release_at_threshold(self):
        state = Buttons()
        state.update(1, 0)
        self.assertEqual(state.update(0, 0.7), ["control_center"])

    def test_disconnect_drops_pending_home(self):
        state = Buttons()
        state.update(1, 0)
        state.clear()
        self.assertEqual(state.repeat(1), [])
        self.assertEqual(state.update(0, 1), [])

    def test_back_tap_waits_for_release(self):
        state = Buttons()
        self.assertEqual(state.update(0x40, 0), [])
        self.assertEqual(state.repeat(0.3), [])
        self.assertEqual(state.update(0, 0.4), ["menu"])

    def test_back_hold_does_not_send_initial_tap(self):
        state = Buttons()
        self.assertEqual(state.update(0x40, 0), [])
        self.assertEqual(state.repeat(0.65), ["menu_hold"])
        self.assertEqual(state.repeat(1), [])
        self.assertEqual(state.update(0, 1.2), [])

    def test_back_release_at_threshold(self):
        state = Buttons()
        state.update(0x40, 0)
        self.assertEqual(state.update(0, 0.7), ["menu_hold"])

    def test_back_can_be_tapped_again_after_hold(self):
        state = Buttons()
        state.update(0x40, 0)
        state.repeat(0.7)
        state.update(0, 0.8)
        self.assertEqual(state.update(0x40, 0.9), [])
        self.assertEqual(state.update(0, 1), ["menu"])

    def test_disconnect_drops_pending_back(self):
        state = Buttons()
        state.update(0x40, 0)
        state.clear()
        self.assertEqual(state.repeat(1), [])
        self.assertEqual(state.update(0, 1), [])

    def test_home_and_back_hold_state_are_independent(self):
        state = Buttons()
        state.update(0x40, 0)
        state.update(0x41, 0.2)
        self.assertEqual(state.repeat(0.7), ["menu_hold"])
        self.assertEqual(state.repeat(0.9), ["control_center"])
        self.assertEqual(state.update(0, 1), [])


if __name__ == "__main__":
    unittest.main()
