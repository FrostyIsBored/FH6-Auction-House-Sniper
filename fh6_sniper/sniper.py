"""Sniper state machine and the GameIO wrapper used by tests."""
from __future__ import annotations
import logging
import random
import time
from . import actions, capture, vision
from .vision import Screen

log = logging.getLogger("fh6.sniper")


def _names(screens) -> str:
    return "{" + ", ".join(sorted(s.name for s in screens)) + "}"


class GameIO:
    """Glue between capture + vision + input. Swappable for testing."""

    def __init__(self, cfg, templates):
        self.cfg = cfg
        self.templates = templates
        self._last_screen = None

    def screen(self, targets=None) -> Screen:
        """Identify the current screen. If `targets` is a set of Screen,
        only those (plus the priority results templates and the last-known
        screen) are matched."""
        if (targets is not None and self._last_screen is not None
                and self._last_screen != Screen.UNKNOWN):
            targets = targets | {self._last_screen}
        frame = capture.grab_screen(self.cfg.window_title)
        result = vision.identify_screen(
            frame, self.templates, self.cfg.match_threshold, targets=targets)
        if result != self._last_screen:
            log.info("screen -> %s", result.name)
            self._last_screen = result
        return result

    def focused(self) -> bool:
        return capture.is_game_focused(self.cfg.window_title)

    def confirm_highlighted(self) -> bool:
        frame = capture.grab_screen(self.cfg.window_title)
        return vision.is_confirm_highlighted(
            frame, self.cfg.lime_hsv_lower, self.cfg.lime_hsv_upper)

    def card_sold(self) -> bool:
        frame = capture.grab_screen(self.cfg.window_title)
        return vision.is_card_sold(frame)

    def first_buyable_slot(self) -> int:
        frame = capture.grab_screen(self.cfg.window_title)
        return vision.first_buyable_slot(frame)

    def press(self, name: str, times: int = 1) -> None:
        log.info("press %s%s", name, f" x{times}" if times > 1 else "")
        actions.tap_key(name, times,
                        self.cfg.key_hold_ms, self.cfg.between_keys_ms)


class Sniper:
    """Drives the auction house loop through a GameIO."""

    def __init__(self, io, cfg, clock=time.monotonic, sleeper=time.sleep,
                 on_purchase=None, on_status=None, on_stats=None):
        self.io = io
        self.cfg = cfg
        self.clock = clock
        self.sleeper = sleeper
        self.on_purchase = on_purchase
        self.on_status = on_status
        self.on_stats = on_stats
        self.cars_bought = 0
        self.searches = 0
        self.failed_buyouts = 0
        self.started_at = None
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def _status(self, text: str) -> None:
        log.info("[status] %s", text)
        if self.on_status:
            self.on_status(text)

    def _emit_stats(self) -> None:
        if self.on_stats:
            self.on_stats(self.searches, self.cars_bought,
                          self.failed_buyouts)

    def _poll_delay(self) -> None:
        lo, hi = self.cfg.poll_interval_ms
        self.sleeper(random.uniform(lo, hi) / 1000.0)

    def _guard_focus(self) -> None:
        """Block until FH6 is the foreground window. Sets the Paused status
        once on entry, not on every tick."""
        if self.io.focused():
            return
        self._status("Paused: FH6 not focused")
        while not self.io.focused():
            if self._stop:
                return
            self.sleeper(0.5)

    def _press(self, name: str, times: int = 1) -> None:
        """Send a keypress, but only while FH6 has focus."""
        self._guard_focus()
        if self._stop:
            return
        self.io.press(name, times)

    def wait_for(self, screens: set, timeout: float):
        """Poll until the current screen is in `screens`, or timeout. Time
        spent in _guard_focus does not count toward the timeout."""
        deadline = self.clock() + timeout
        while self.clock() < deadline:
            if self._stop:
                return None
            before = self.clock()
            self._guard_focus()
            if self._stop:
                return None
            deadline += self.clock() - before
            current = self.io.screen(targets=screens)
            if current in screens:
                log.info("wait_for %s -> %s", _names(screens), current.name)
                return current
            self._poll_delay()
        log.info("wait_for %s -> TIMEOUT after %.0fs", _names(screens), timeout)
        return None

    def _press_until(self, key, from_screen, targets,
                     settle: float = 0.7, reach: float = 8.0,
                     attempts: int = 4):
        """Press `key` until a target screen is reached. If the screen has
        not left `from_screen` within `settle`, retry the press."""
        inner_targets = targets | {from_screen}
        for _ in range(attempts):
            if self._stop:
                return None
            self._press(key)
            deadline = self.clock() + settle
            while self.clock() < deadline:
                if self._stop:
                    return None
                s = self.io.screen(targets=inner_targets)
                if s in targets:
                    return s
                if s != from_screen:
                    return self.wait_for(targets, reach)
                self._poll_delay()
        return None

    def _goto_search_config(self) -> bool:
        """Get to the Search config screen. Returns success."""
        s = self.io.screen()
        for _ in range(10):
            if self._stop:
                return False
            if s == Screen.SEARCH_CONFIG:
                return True
            if s == Screen.AH_LANDING:
                return self._enter_search_from_landing(known=s)
            if s == Screen.UNKNOWN:
                self.sleeper(0.3)
                s = self.io.screen()
                continue
            self._press("esc")
            s = self._await_settle(prev=s)
        self._status("Lost: start the bot in the Auction House")
        return False

    def _enter_search_from_landing(self, known=None) -> bool:
        """From the AH landing menu, open Search Auctions."""
        self._status("Opening Search Auctions")
        for attempt in range(1, 5):
            if self._stop:
                return False
            s = known if known is not None else self.io.screen()
            known = None
            log.info("enter_search attempt %d: screen=%s", attempt, s.name)
            if s == Screen.SEARCH_CONFIG:
                return True
            if s == Screen.UNKNOWN:
                self.sleeper(0.6)
                continue
            if s != Screen.AH_LANDING:
                self._press("esc")
                self.sleeper(0.3)
                continue
            # Landing menu takes a moment to become input-ready; this delay
            # stops the first Enter being dropped.
            self.sleeper(0.2)
            self._press("enter")
            if self.wait_for({Screen.SEARCH_CONFIG}, 0.9) is not None:
                return True
        log.info("enter_search: gave up after 4 attempts")
        return False

    def _navigate_to_confirm(self) -> bool:
        """Press Down until the Confirm button is highlighted."""
        for _ in range(12):
            if self._stop:
                return False
            if self.io.confirm_highlighted():
                return True
            self._press("down")
        return self.io.confirm_highlighted()

    def _recover(self) -> str:
        """ESC out toward Search config or AH landing. Never ESCs from an
        UNKNOWN frame."""
        self._status("Recovering")
        s = self.io.screen()
        for _ in range(10):
            if self._stop:
                return "recover_failed"
            if s in (Screen.SEARCH_CONFIG, Screen.AH_LANDING):
                return "recovered"
            if s == Screen.UNKNOWN:
                self.sleeper(0.3)
                s = self.io.screen()
                continue
            self._press("esc")
            s = self._await_settle(prev=s)
        log.info("recover: gave up")
        return "recover_failed"

    def _await_settle(self, prev, timeout: float = 1.2):
        """Poll until the screen settles to a recognised state other than
        `prev`, or timeout. Used right after an ESC."""
        deadline = self.clock() + timeout
        while self.clock() < deadline:
            if self._stop:
                return Screen.UNKNOWN
            self._poll_delay()
            s = self.io.screen()
            if s != Screen.UNKNOWN and s != prev:
                return s
        return Screen.UNKNOWN

    def _back_to_landing(self, known=None) -> None:
        """ESC out to the AH landing menu, however many screens deep."""
        s = known if known is not None else self.io.screen()
        for _ in range(6):
            if self._stop:
                return
            if s == Screen.AH_LANDING:
                return
            if s == Screen.UNKNOWN:
                self.sleeper(0.3)
                s = self.io.screen()
                continue
            self._press("esc")
            s = self._await_settle(prev=s)

    def _escape_player_options(self) -> str:
        """ESC out of the Player Options menu a sold car can open. ESCs
        even from UNKNOWN screens; stops at AH_LANDING.

        Returns "no_cars" - the car was sold before we could snipe it,
        which is a missed-search, not a failed buyout.
        """
        self._status("Listing already sold, skipping")
        for _ in range(6):
            if self._stop:
                return "recover_failed"
            if self.io.screen() == Screen.AH_LANDING:
                return "no_cars"
            self._press("esc")
            self.sleeper(0.6)
        return "no_cars"

    def _collect(self) -> None:
        """Collect a won car. The Claim Car popup has two stages that both
        read as CLAIM_CAR; press Enter until the screen leaves it."""
        self._status("Collecting car")
        if self._press_until("y", Screen.RESULTS_HAS_CARS,
                             {Screen.AUCTION_OPTIONS}) is None:
            return
        if self._press_until("enter", Screen.AUCTION_OPTIONS,
                             {Screen.CLAIM_CAR}) is None:
            return
        deadline = self.clock() + self.cfg.timeout_claim_s
        while self.clock() < deadline:
            if self._stop:
                return
            s = self.io.screen()
            if s == Screen.CLAIM_CAR:
                self._press("enter")
                self.sleeper(1.0)
            elif s == Screen.UNKNOWN:
                self.sleeper(0.3)
            else:
                return

    def run_once(self) -> str:
        """One snipe attempt.

        Returns: bought | failed | no_cars | recovered | recover_failed.
        """
        log.info("--- run_once ---")
        cfg = self.cfg
        if not self._goto_search_config():
            return "recover_failed"

        self._status("Searching")
        if not self._navigate_to_confirm():
            return self._recover()
        result = self._press_until(
            "enter", Screen.SEARCH_CONFIG,
            {Screen.RESULTS_HAS_CARS, Screen.RESULTS_EMPTY})
        if result is not Screen.RESULTS_HAS_CARS:
            self._back_to_landing(known=result)
            return "no_cars"

        slot = self.io.first_buyable_slot()
        if slot == 0:
            self._status("All listings sold, skipping")
            self._back_to_landing(known=result)
            return "no_cars"

        self._status("Car found, buying out")
        for _ in range(slot - 1):
            self._press("down")

        if slot > 1 and self.io.first_buyable_slot() != slot:
            self._status("Listing sold during navigation, skipping")
            self._back_to_landing(known=result)
            return "no_cars"

        seen = self._press_until(
            "y", Screen.RESULTS_HAS_CARS,
            {Screen.AUCTION_OPTIONS, Screen.PLAYER_OPTIONS})
        if seen == Screen.PLAYER_OPTIONS:
            return self._escape_player_options()
        if seen is None:
            return self._recover()

        # Don't retry down+enter. A dropped Down leaves Place Bid
        # highlighted, so a retried Enter would bid credits.
        self._press("down")
        self._press("enter")
        seen = self.wait_for({Screen.BUY_OUT, Screen.PLAYER_OPTIONS}, 2.5)
        if seen == Screen.PLAYER_OPTIONS:
            return self._escape_player_options()
        if seen is None:
            return self._recover()

        # Confirm Yes. If the Attempting-Buyout (BUYOUT_PROGRESS) screen
        # doesn't appear within ~0.7s the press was dropped, so retry
        # immediately instead of burning a long timeout. Once we see
        # PROGRESS the request is in flight and we wait the full outcome
        # timeout without re-pressing.
        outcome = None
        for _ in range(4):
            if self._stop:
                return self._recover()
            self._press("enter")
            seen = self.wait_for(
                {Screen.BUYOUT_PROGRESS,
                 Screen.BUYOUT_SUCCESS, Screen.BUYOUT_FAILED}, 0.7)
            if seen in (Screen.BUYOUT_SUCCESS, Screen.BUYOUT_FAILED):
                outcome = seen
                break
            if seen == Screen.BUYOUT_PROGRESS:
                outcome = self.wait_for(
                    {Screen.BUYOUT_SUCCESS, Screen.BUYOUT_FAILED},
                    cfg.timeout_outcome_s)
                break
        if outcome is None:
            return self._recover()

        self._press("enter")            # dismiss the outcome popup

        if outcome == Screen.BUYOUT_FAILED:
            self._back_to_landing()
            return "failed"

        if cfg.collect_after_buyout:
            self._collect()
        self._back_to_landing()
        return "bought"

    def _auto_stop_reached(self) -> bool:
        cfg = self.cfg
        if not cfg.auto_stop_enabled:
            return False
        if self.cars_bought >= cfg.max_cars:
            return True
        elapsed_min = (self.clock() - self.started_at) / 60.0
        return elapsed_min >= cfg.max_minutes

    def run(self) -> str:
        """Loop snipe attempts until stopped or an auto-stop limit hits.

        Returns: stopped | auto_stop | recover_failed.
        """
        self.started_at = self.clock()
        log.info("=== sniper started ===")
        self._status("Running")
        while not self._stop:
            if self._auto_stop_reached():
                self._status("Auto-stop limit reached")
                return "auto_stop"
            self._guard_focus()
            if self._stop:
                break
            t0 = self.clock()
            outcome = self.run_once()
            log.info("run_once outcome: %s", outcome)
            self.searches += 1
            if outcome == "recover_failed":
                self._emit_stats()
                self._status("Stopped: could not recover")
                return "recover_failed"
            if outcome == "failed":
                self.failed_buyouts += 1
            if outcome == "bought":
                self.cars_bought += 1
                loop_s = self.clock() - t0
                self._status(f"Bought {self.cars_bought} car(s)")
                if self.on_purchase:
                    self.on_purchase(loop_s, self.cars_bought)
            self._emit_stats()
            self.sleeper(self.cfg.loop_pace_s)
        self._status("Stopped")
        return "stopped"
