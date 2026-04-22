"""Tests for parser_extensions.json loading."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from parser_extensions import parse_manifest  # noqa: E402


def test_parse_manifest_accepts_proto_mapping() -> None:
    raw = {
        "extensions": [
            {"suffix": ".proto", "kind": "code", "module": "parsers.code", "function": "parse"},
        ]
    }
    out = parse_manifest(raw)
    assert out[".proto"] == ("code", "parsers.code", "parse")


def test_parse_manifest_rejects_non_parsers_module() -> None:
    raw = {
        "extensions": [
            {"suffix": ".evil", "kind": "text", "module": "os", "function": "system"},
        ]
    }
    assert parse_manifest(raw) == {}


def test_parse_manifest_rejects_builtin_override_duplicate_handled_in_loader() -> None:
    """Manifest may list .md; loader (parsers.load_user_extensions) skips if built-in."""
    raw = {
        "extensions": [
            {"suffix": ".md", "kind": "text", "module": "parsers.text", "function": "parse"},
        ]
    }
    out = parse_manifest(raw)
    assert ".md" in out
