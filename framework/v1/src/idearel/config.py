"""Configuration loading. Defaults live in config/default.json."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "default.json"


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> dict:
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.pop("_comment", None)
    for key, value in (overrides or {}).items():
        set_value(cfg, key, value)
    return cfg


def set_value(cfg: dict, dotted_key: str, value: Any) -> None:
    """Set e.g. 'thresholds.content' = 0.8 or 'cascade.order' = 'linguistic,content'."""
    parts = dotted_key.split(".")
    node = cfg
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    last = parts[-1]
    if isinstance(value, str):
        old = node.get(last)
        if isinstance(old, list):
            value = [v.strip() for v in value.split(",") if v.strip()]
        elif isinstance(old, bool):
            value = value.lower() in ("1", "true", "yes", "on")
        elif isinstance(old, (int, float)) and not isinstance(old, bool):
            value = float(value)
    node[last] = value


def parse_set_args(items: list[str] | None) -> dict[str, Any]:
    out = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"--set expects key=value, got {item!r}")
        k, v = item.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def copy_config(cfg: dict) -> dict:
    return copy.deepcopy(cfg)
