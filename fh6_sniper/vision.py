"""Screen identification: OpenCV template matching and HSV colour masks."""
from __future__ import annotations
from enum import Enum, auto
from pathlib import Path
import cv2
import numpy as np


class Screen(Enum):
    UNKNOWN = auto()
    SEARCH_CONFIG = auto()
    RESULTS_HAS_CARS = auto()
    RESULTS_EMPTY = auto()
    AUCTION_OPTIONS = auto()
    PLAYER_OPTIONS = auto()
    BUY_OUT = auto()
    BUYOUT_PROGRESS = auto()
    BUYOUT_SUCCESS = auto()
    BUYOUT_FAILED = auto()
    CLAIM_CAR = auto()
    AH_LANDING = auto()


TEMPLATE_SCREENS: dict[str, Screen] = {
    "search.png": Screen.SEARCH_CONFIG,
    "auction_details.png": Screen.RESULTS_HAS_CARS,
    "no_auctions.png": Screen.RESULTS_EMPTY,
    "auction_options.png": Screen.AUCTION_OPTIONS,
    "player_options.png": Screen.PLAYER_OPTIONS,
    "buy_out.png": Screen.BUY_OUT,
    "buy_out_bgoff.png": Screen.BUY_OUT,
    "buy_out_progress.png": Screen.BUYOUT_PROGRESS,
    "buy_out_progress_bgoff.png": Screen.BUYOUT_PROGRESS,
    "buyout_successful.png": Screen.BUYOUT_SUCCESS,
    "buyout_failed.png": Screen.BUYOUT_FAILED,
    "claim_car.png": Screen.CLAIM_CAR,
    "ah_landing.png": Screen.AH_LANDING,
}


def lime_mask(bgr: np.ndarray, lower, upper) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, np.array(lower, np.uint8), np.array(upper, np.uint8))


def largest_lime_bbox(bgr, lower, upper):
    """Bounding box of the largest banner-shaped lime region, or None."""
    mask = lime_mask(bgr, lower, upper)
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_area = 0.0
    for c in contours:
        area = cv2.contourArea(c)
        if area < 2000:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if h <= 0 or w / h < 4.0:        # not banner-shaped
            continue
        if area > best_area:
            best_area = area
            best = (x, y, w, h)
    return best


def _gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def match_template(scene: np.ndarray, template: np.ndarray) -> float:
    """Best NCC score of template inside scene. 0.0 if template is too big."""
    s, t = _gray(scene), _gray(template)
    if t.shape[0] > s.shape[0] or t.shape[1] > s.shape[1]:
        return 0.0
    result = cv2.matchTemplate(s, t, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return float(max_val)


_DOWNSCALED_TEMPLATES: dict[int, np.ndarray] = {}


def _small(tmpl: np.ndarray) -> np.ndarray:
    key = id(tmpl)
    cached = _DOWNSCALED_TEMPLATES.get(key)
    if cached is None:
        cached = _downscale(tmpl)
        _DOWNSCALED_TEMPLATES[key] = cached
    return cached


def load_templates(template_dir) -> dict:
    """Load every detection template as grayscale. Raises if any is missing."""
    out = {}
    for name in TEMPLATE_SCREENS:
        path = Path(template_dir) / name
        img = cv2.imread(str(path))
        if img is None:
            raise FileNotFoundError(f"template missing: {path}")
        gray = _gray(img)
        out[name] = gray
        _DOWNSCALED_TEMPLATES[id(gray)] = _downscale(gray)
    return out


# Distinctive results templates beat ah_landing (whose title also appears
# on the results screens).
_RESULTS_PRIORITY = ("auction_details.png", "no_auctions.png")

_MATCH_SCALE = 0.5


def _downscale(img: np.ndarray) -> np.ndarray:
    return cv2.resize(img, None, fx=_MATCH_SCALE, fy=_MATCH_SCALE,
                      interpolation=cv2.INTER_AREA)


# Where each template appears on a 1920x1080 frame, with padding.
TEMPLATE_REGIONS = {
    "search.png":             (472, 223, 1448, 471),
    "auction_details.png":    (889,  64, 1920, 294),
    "no_auctions.png":        (1113, 434, 1706, 690),
    "auction_options.png":    (546, 276, 1374, 526),
    "player_options.png":     (580, 230, 1340, 486),
    "buy_out.png":               (520, 470, 1400, 620),
    "buy_out_bgoff.png":         (520, 470, 1400, 620),
    "buy_out_progress.png":      (520, 470, 1400, 620),
    "buy_out_progress_bgoff.png":(520, 470, 1400, 620),
    "buyout_successful.png":  (539, 334, 1374, 612),
    "buyout_failed.png":      (546, 378, 1374, 631),
    "claim_car.png":          (538, 359, 1374, 615),
    "ah_landing.png":         (16,   89,  387, 291),
}


# Templates that must be matched at full resolution. The buy_out body and
# buy_out_progress body are short text-band crops; half-res blurs the text
# enough that live frames drop below the 0.80 threshold (~0.78 vs ~0.86).
_FULL_RES_TEMPLATES = {
    "buy_out.png", "buy_out_bgoff.png",
    "buy_out_progress.png", "buy_out_progress_bgoff.png",
}


def screen_scores(scene_bgr, templates: dict, targets=None) -> dict:
    """Match score per template, region-cropped. Most templates run at half
    resolution; a few small text-band templates (see _FULL_RES_TEMPLATES)
    run at full res. If `targets` is a set of Screen, only those templates
    (plus the priority results templates) are scored."""
    if targets is not None:
        wanted = set(_RESULTS_PRIORITY)
        wanted |= {n for n, scr in TEMPLATE_SCREENS.items() if scr in targets}
        templates = {n: t for n, t in templates.items() if n in wanted}
    gray = _gray(scene_bgr)
    h, w = gray.shape[:2]
    scores = {}
    for name, tmpl in templates.items():
        region = TEMPLATE_REGIONS.get(name)
        if region:
            x1, y1, x2, y2 = region
            crop = gray[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        else:
            crop = gray
        if name in _FULL_RES_TEMPLATES:
            scores[name] = match_template(crop, tmpl)
        else:
            scores[name] = match_template(_downscale(crop), _small(tmpl))
    return scores


def identify_screen(scene_bgr, templates: dict, threshold: float,
                    targets=None) -> Screen:
    """Best-matching Screen above `threshold`, or UNKNOWN."""
    scores = screen_scores(scene_bgr, templates, targets=targets)
    for name in _RESULTS_PRIORITY:
        if scores.get(name, 0.0) >= threshold:
            return TEMPLATE_SCREENS[name]
    best_screen, best_score = Screen.UNKNOWN, threshold
    for name, score in scores.items():
        if score >= best_score:
            best_screen, best_score = TEMPLATE_SCREENS[name], score
    return best_screen


# Search-config Confirm button band at 1920x1080.
CONFIRM_ROW = (548, 714, 1372, 772)


def is_confirm_highlighted(scene_bgr, lower, upper, region=CONFIRM_ROW) -> bool:
    """True if the Confirm button shows the lime highlight."""
    x1, y1, x2, y2 = region
    crop = scene_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return False
    mask = lime_mask(crop, lower, upper)
    return int(cv2.countNonZero(mask)) > 300


# Yellow SOLD stamp HSV range and per-slot regions. Cards stack at a 202px
# pitch; regions stop above the live time-left pill and the price-row icons.
SOLD_HSV_LOWER = (20, 120, 120)
SOLD_HSV_UPPER = (34, 255, 255)
SOLD_STAMP_REGION = (90, 185, 300, 295)


def is_card_sold(scene_bgr, region=SOLD_STAMP_REGION) -> bool:
    """True if the top result card shows the yellow SOLD stamp."""
    x1, y1, x2, y2 = region
    crop = scene_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(SOLD_HSV_LOWER, np.uint8),
                       np.array(SOLD_HSV_UPPER, np.uint8))
    return int(cv2.countNonZero(mask)) > 800


SOLD_STAMP_REGIONS = (
    SOLD_STAMP_REGION,
    (90, 387, 300, 497),
    (90, 589, 300, 699),
    (90, 791, 300, 901),
)


def sold_slots(scene_bgr) -> tuple:
    """Per-slot SOLD flags for the four result slots."""
    hsv = cv2.cvtColor(scene_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv,
                       np.array(SOLD_HSV_LOWER, np.uint8),
                       np.array(SOLD_HSV_UPPER, np.uint8))
    return tuple(int(cv2.countNonZero(mask[y1:y2, x1:x2])) > 800
                 for (x1, y1, x2, y2) in SOLD_STAMP_REGIONS)


def first_buyable_slot(scene_bgr) -> int:
    """1-indexed first non-sold slot, or 0 if all four are sold."""
    for i, sold in enumerate(sold_slots(scene_bgr), start=1):
        if not sold:
            return i
    return 0
