"""Sniper state machine and the GameIO wrapper used by tests."""
from __future__ import annotations
import logging
import random
import time
from . import actions, capture, paths, vision
from .config import save_config
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
        lo, hi = self.cfg.effective_lime_bounds()
        return vision.is_confirm_highlighted(frame, lo, hi)

    def card_sold(self) -> bool:
        frame = capture.grab_screen(self.cfg.window_title)
        return vision.is_card_sold(frame)

    def first_buyable_slot(self) -> int:
        frame = capture.grab_screen(self.cfg.window_title)
        return vision.first_buyable_slot(frame)

    def slot_states(self) -> tuple:
        """Per-slot (sold, populated) flags. Used by the render-wait gate."""
        frame = capture.grab_screen(self.cfg.window_title)
        return vision.slot_states(frame)

    def press(self, name: str, times: int = 1) -> None:
        log.info("press %s%s", name, f" x{times}" if times > 1 else "")
        actions.tap_key(name, times,
                        self.cfg.key_hold_ms, self.cfg.between_keys_ms,
                        use_win32=self.cfg.win32_api_input)


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
        # One-shot guard for the auto BG-toggle recovery. The buy_out and
        # buy_out_progress templates are the only BG-sensitive ones; when
        # the wait for the confirm dialog times out we flip the flag,
        # reload templates, retry once, and never auto-toggle again this
        # session even if the second attempt also fails.
        self._auto_bg_toggled = False
        # True once we have identified ANY known screen this session.
        # A recover_failed while still False usually means the game
        # language isn't English (templates only match the English UI).
        self._oriented = False

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
        if self.cfg.win32_api_input:
            return
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

    def _wait_for_populated_slots(self, timeout: float) -> bool:
        """Block up to `timeout` for FH6 to render at least one card.

        The RESULTS_HAS_CARS lime banner appears a frame or two before the
        card UI is fully drawn. first_buyable_slot called on that earlier
        frame finds zero populated slots and falsely reports 'all sold'.
        Polls slot_states tightly between iterations (5ms breather, not
        the global poll cadence) since the wait only runs on the results
        page and is short-lived. Returns True once a populated slot is
        seen, False on timeout (caller should still proceed)."""
        deadline = self.clock() + timeout
        while self.clock() < deadline:
            if self._stop:
                return False
            for _sold, populated in self.io.slot_states():
                if populated:
                    return True
            # 5ms breather: keeps capture work from saturating one core in
            # the tight loop, and gives the FakeClock-based tests a way to
            # advance their virtual clock so the timeout fires deterministically.
            self.sleeper(0.005)
        log.info("populated wait timed out after %.1fs", timeout)
        return False

    def _try_toggle_moving_background(self) -> bool:
        """Auto-toggle moving_background and reload templates in place.

        Fires when the buy_out wait_for has timed out - that template pair
        is the only BG-sensitive one, so a stuck confirm dialog is almost
        always a flag mismatch. Returns True if the toggle ran (caller
        should retry the screen check); False if already attempted this
        session, in which case the caller should fall through to the
        normal recovery path."""
        if self._auto_bg_toggled:
            return False
        cfg = self.cfg
        new_value = not cfg.moving_background
        try:
            new_templates = vision.load_templates(
                paths.app_dir() / cfg.template_dir,
                moving_background=new_value)
            self.io.templates = new_templates
            cfg.moving_background = new_value
            save_config(cfg, paths.app_dir() / "config.json")
        except Exception:
            log.exception("auto-toggle moving_background failed")
            return False
        self._auto_bg_toggled = True
        log.info("auto-toggle moving_background -> %s "
                 "(buy_out wait timed out; templates reloaded, "
                 "saved to config.json)", new_value)
        self._status(f"Auto-toggled moving background -> {new_value}")
        return True

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
                self._oriented = True
                return True
            if s == Screen.AH_LANDING:
                self._oriented = True
                return self._enter_search_from_landing(known=s)
            if s == Screen.UNKNOWN:
                self.sleeper(0.3)
                s = self.io.screen()
                continue
            self._oriented = True
            self._press("esc")
            s = self._await_settle(prev=s)
        if self._oriented:
            self._status("Lost: start the bot in the Auction House")
        else:
            self._status("Lost: set game language to English")
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
        """ESC out toward Search config or AH landing.

        Avoids ESCing from a single UNKNOWN frame (could be a mid-transition
        flicker), but ESCs after the screen has been persistently UNKNOWN.
        Persistent UNKNOWN usually means we're on a popup with no template
        (e.g. the Place Bid dialog) and need to back out. ESC only ever
        closes popups, never confirms anything.
        """
        self._status("Recovering")
        s = self.io.screen()
        unknown_streak = 0
        for _ in range(10):
            if self._stop:
                return "recover_failed"
            if s in (Screen.SEARCH_CONFIG, Screen.AH_LANDING):
                return "recovered"
            if s == Screen.UNKNOWN:
                unknown_streak += 1
                if unknown_streak >= 4:           # ~1.2s of stuck UNKNOWN
                    self._press("esc")
                    unknown_streak = 0
                    s = self._await_settle(prev=s)
                    continue
                self.sleeper(0.3)
                s = self.io.screen()
                continue
            unknown_streak = 0
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

    def _confirm_yes(self):
        """Press Yes on the BUY_OUT confirm dialog and observe the screen.

        State machine:
        - **BUY_OUT** (confirm still showing): Enter was dropped, re-press.
        - **BUYOUT_PROGRESS**: request in flight, slow polling, wait outcome.
        - **BUYOUT_SUCCESS / BUYOUT_FAILED**: done.
        - **UNKNOWN**: keep polling briefly, then bail (likely a popup we
          don't have a template for, e.g. Place Bid from a dropped Down).

        Initial budget is 5s - keeps polling bounded if we never see any
        recognisable buyout screen. Bumps to `cfg.timeout_outcome_s` once
        we know the request is in flight (BUYOUT_PROGRESS).
        """
        cfg = self.cfg
        self._press("enter")
        deadline = self.clock() + 5.0          # initial: 5s to see something
        in_flight = False
        enter_attempts = 1
        targets = {Screen.BUY_OUT, Screen.BUYOUT_PROGRESS,
                   Screen.BUYOUT_SUCCESS, Screen.BUYOUT_FAILED}
        while self.clock() < deadline:
            if self._stop:
                return None
            before = self.clock()
            self._guard_focus()
            if self._stop:
                return None
            deadline += self.clock() - before
            s = self.io.screen(targets=targets)
            if s in (Screen.BUYOUT_SUCCESS, Screen.BUYOUT_FAILED):
                return s
            if s == Screen.BUY_OUT and enter_attempts < 4:
                self._press("enter")
                enter_attempts += 1
            elif s == Screen.BUYOUT_PROGRESS and not in_flight:
                in_flight = True
                deadline = self.clock() + cfg.timeout_outcome_s
            if in_flight:
                self.sleeper(0.2)              # 5 Hz - request is in flight, calm
            else:
                self._poll_delay()             # ~15 Hz - still figuring out state
        return None

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
            {Screen.RESULTS_HAS_CARS, Screen.RESULTS_EMPTY},
            reach=cfg.timeout_results_s)
        if result is not Screen.RESULTS_HAS_CARS:
            self._back_to_landing(known=result)
            return "no_cars"

        # The RESULTS_HAS_CARS banner renders before the card UI itself.
        # Wait for at least one populated card before checking slot state,
        # otherwise first_buyable_slot returns 0 on an unrendered frame and
        # the bot falsely reports 'all sold'.
        self._wait_for_populated_slots(1.5)

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
        if cfg.buyout_select_delay_ms:
            self.sleeper(cfg.buyout_select_delay_ms / 1000.0)
        self._press("enter")
        # Tight 1.0s wait: typical BUY_OUT dialog render is 200-400ms so
        # 1.0s is ~3x margin while shaving 1.5s off the wasted time
        # whenever the moving_background flag is wrong and the templates
        # never match.
        seen = self.wait_for({Screen.BUY_OUT, Screen.PLAYER_OPTIONS}, 1.0)
        if seen == Screen.PLAYER_OPTIONS:
            return self._escape_player_options()
        if seen is None and self._try_toggle_moving_background():
            seen = self.wait_for(
                {Screen.BUY_OUT, Screen.PLAYER_OPTIONS}, 1.0)
            if seen == Screen.PLAYER_OPTIONS:
                return self._escape_player_options()
        if seen is None:
            return self._recover()

        outcome = self._confirm_yes()
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
                if self._oriented:
                    self._status("Stopped: could not recover")
                else:
                    self._status("Stopped: set game language to English")
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
