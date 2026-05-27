"""Local dev: optional per-action frame dumps for diagnosing detection bugs.

Enabled by adding `"debug_screenshots": true` to config.json. The flag stays
out of the shipped dataclass defaults so consumer builds never write here.
"""
from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path

import cv2

from . import paths

_log = logging.getLogger("fh6.debug_dump")


def enabled(cfg) -> bool:
    """True if the bot should write debug frames for this session."""
    return bool(getattr(cfg, "debug_screenshots", False))


def _stamp() -> str:
    now = datetime.now()
    return now.strftime("%Y%m%d-%H%M%S-") + f"{now.microsecond // 1000:03d}"


def dump(cfg, frame, trigger: str, metadata: dict | None = None) -> Path | None:
    """Write frame + JSON sidecar to logs/debug/. Returns the PNG path or None.

    No-op when the flag is off or the frame is missing."""
    if not enabled(cfg) or frame is None:
        return None
    out_dir = paths.app_dir() / "logs" / "debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    png_path = out_dir / f"{stamp}_{trigger}.png"
    json_path = out_dir / f"{stamp}_{trigger}.json"
    try:
        cv2.imwrite(str(png_path), frame)
        body = {"timestamp": stamp, "trigger": trigger}
        if metadata:
            body.update(metadata)
        json_path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    except Exception as exc:
        _log.warning("debug dump failed: %s", exc)
        return None
    return png_path
