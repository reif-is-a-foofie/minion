"""Loopback read/stream of ``telemetry.jsonl`` for in-app analytics (Support pane).

Same trust model as ``diagnostics``: 127.0.0.1 only; payloads can include queries
and paths unless ``redacted=true``.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Generator, Iterator, List, Optional

from telemetry import TELEMETRY_FILENAME

_REDACT_KEYS = ("query", "path", "top_path")


def redact_event(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Strip screenshot-sensitive fields (aligned with remote analytics sanitize)."""
    out = dict(obj)
    for k in _REDACT_KEYS:
        if k in out and out[k] is not None:
            out[k] = "[redacted]"
    return out


def _hint_path(p: Optional[Path]) -> Optional[str]:
    if p is None:
        return None
    hint = str(p)
    try:
        home = os.path.expanduser("~")
        if home and len(home) > 2:
            hint = hint.replace(home, "~")
    except Exception:
        pass
    return hint


def _parse_jsonl_lines(text: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            out.append(json.loads(s))
        except json.JSONDecodeError:
            continue
    return out


def read_telemetry_tail(
    data_dir: Path,
    *,
    max_lines: int = 200,
    max_bytes: int = 256_000,
    redacted: bool = False,
) -> Dict[str, Any]:
    """Return newest-last tail of ``<data_dir>/telemetry.jsonl`` as parsed objects."""
    path = Path(data_dir) / TELEMETRY_FILENAME
    rolled = Path(data_dir) / (TELEMETRY_FILENAME + ".1")
    if not path.is_file():
        return {
            "telemetry_file_hint": _hint_path(path),
            "rolled_file_hint": _hint_path(rolled) if rolled.is_file() else None,
            "events": [],
            "count": 0,
        }
    try:
        data = path.read_bytes()
    except OSError:
        return {
            "telemetry_file_hint": _hint_path(path),
            "rolled_file_hint": _hint_path(rolled) if rolled.is_file() else None,
            "events": [],
            "count": 0,
        }
    if len(data) > max_bytes:
        data = data[-max_bytes:]
        nl = data.find(b"\n")
        if nl != -1:
            data = data[nl + 1 :]
    text = data.decode("utf-8", errors="replace")
    events = _parse_jsonl_lines(text)
    if len(events) > max_lines:
        events = events[-max_lines:]
    if redacted:
        events = [redact_event(e) for e in events]
    return {
        "telemetry_file_hint": _hint_path(path),
        "rolled_file_hint": _hint_path(rolled) if rolled.is_file() else None,
        "events": events,
        "count": len(events),
    }


def iter_telemetry_sse_events(data_dir: Path, *, redacted: bool = False) -> Iterator[str]:
    """SSE ``data:`` lines: ``{\"event\": {...}}``, ``{\"heartbeat\": true}``, or parse skips."""
    path = Path(data_dir) / TELEMETRY_FILENAME
    pos: int = 0

    def emit_initial_window() -> Generator[str, None, None]:
        nonlocal pos
        if not path.is_file():
            return
        try:
            sz = path.stat().st_size
        except OSError:
            return
        # Snapshot byte length at window start so a late `pos = stat()` cannot
        # jump to a smaller rotated file while this generator is still draining
        # the initial chunk (see tests/test_telemetry_feed.py truncation case).
        end_at_open = sz
        start = max(0, sz - 48_000)
        try:
            with path.open("rb") as f:
                f.seek(start)
                chunk = f.read().decode("utf-8", errors="replace")
        except OSError:
            return
        if start > 0 and "\n" in chunk:
            chunk = chunk.split("\n", 1)[1]
        for line in chunk.splitlines():
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if redacted:
                obj = redact_event(obj)
            yield f"data: {json.dumps({'event': obj})}\n\n"
        pos = end_at_open

    yield from emit_initial_window()

    while True:
        time.sleep(0.85)
        if not path.is_file():
            yield f"data: {json.dumps({'heartbeat': True})}\n\n"
            pos = 0
            continue
        try:
            st = path.stat()
        except OSError:
            yield f"data: {json.dumps({'heartbeat': True})}\n\n"
            continue
        sz = st.st_size
        if sz < pos:
            # Truncation or log rotation: follow from start of the new file.
            pos = 0
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                f.seek(pos)
                new = f.read()
                pos = f.tell()
        except OSError:
            yield f"data: {json.dumps({'heartbeat': True})}\n\n"
            continue
        if not new.strip():
            yield f"data: {json.dumps({'heartbeat': True})}\n\n"
            continue
        for line in new.splitlines():
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if redacted:
                obj = redact_event(obj)
            yield f"data: {json.dumps({'event': obj})}\n\n"
