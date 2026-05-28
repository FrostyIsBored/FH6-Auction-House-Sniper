"""Keyboard input with randomized timing."""
from __future__ import annotations
import random
import time
import win32gui
import win32con
from pynput.keyboard import Key, Controller

_DEFAULT_KEYBOARD = Controller()

def get_hwnd(window_title="Forza Horizon 6"):
    """Get the window handle for the Forza Horizon 6 game window."""
    hwnd = win32gui.FindWindow(None, window_title)
    if not hwnd:
        print("Forza Horizon 6 window not found")
    return hwnd

hwnd = get_hwnd()

KEY_MAP = {
    "enter": Key.enter,
    "esc": Key.esc,
    "up": Key.up,
    "down": Key.down,
    "y": "y",
}

VK_CODES = {
    "enter": 0x0D,
    "esc": 0x1B,
    "up": 0x26,
    "down": 0x28,
    "y": 0x59,
}


def _rand_seconds(ms_range) -> float:
    return random.uniform(ms_range[0], ms_range[1]) / 1000.0

def press_key(name, key_hold_ms, between_keys_ms,
              use_win32=False, keyboard=_DEFAULT_KEYBOARD,
              hwnd=hwnd, sleep=time.sleep) -> None:
    if use_win32:
        press_key_vk(name, key_hold_ms, between_keys_ms, hwnd, sleep)
    else:
        press_key_fg(name, key_hold_ms, between_keys_ms, keyboard, sleep)

def press_key_fg(name, key_hold_ms, between_keys_ms,
              keyboard=_DEFAULT_KEYBOARD, sleep=time.sleep) -> None:
    """Press one key with a randomized hold and post-press gap."""
    key = KEY_MAP[name]
    keyboard.press(key)
    sleep(_rand_seconds(key_hold_ms))
    keyboard.release(key)
    sleep(_rand_seconds(between_keys_ms))

def press_key_vk(name, key_hold_ms, between_keys_ms,
                 hwnd=hwnd, sleep=time.sleep) -> None:
    """Press one key with a randomized hold and post-press gap using win32 API."""
    vk_code = VK_CODES[name]
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
    sleep(_rand_seconds(key_hold_ms))
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)
    sleep(_rand_seconds(between_keys_ms))


def tap_key(name, times, key_hold_ms, between_keys_ms,
            use_win32=False, keyboard=_DEFAULT_KEYBOARD,
            hwnd=hwnd, sleep=time.sleep) -> None:
    """Press a key `times` times."""
    for _ in range(times):
        press_key(name, key_hold_ms, between_keys_ms,
                  use_win32, keyboard, hwnd, sleep)
