"""
User-defined file extension → parser mappings (data-dir manifest).

Drop ``<MINION_DATA_DIR>/parser_extensions.json`` to map new suffixes onto
existing in-tree parser modules (``parsers.*`` only). Restart or call
``POST /extensions/reload`` to apply without restarting the process.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

log = logging.getLogger("minion.parser_extensions")

FILENAME = "parser_extensions.json"
_ALLOWED_MODULE_PREFIX = "parsers."
_SUFFIX_RE = re.compile(r"^\.?[a-zA-Z0-9._+-]{1,32}$")


def manifest_path(data_dir: Path) -> Path:
    return Path(data_dir) / FILENAME


def _norm_suffix(raw: str) -> str:
    s = raw.strip().lower()
    if not s.startswith("."):
        s = "." + s
    return s


def parse_manifest(raw: Dict[str, Any]) -> Dict[str, Tuple[str, str, str]]:
    """Return extension → (kind, module, function) for valid entries."""
    out: Dict[str, Tuple[str, str, str]] = {}
    exts = raw.get("extensions")
    if not isinstance(exts, list):
        return out
    for i, row in enumerate(exts):
        if not isinstance(row, dict):
            continue
        suf = row.get("suffix") or row.get("extension")
        kind = row.get("kind")
        module = row.get("module")
        fn = row.get("function") or "parse"
        if not isinstance(suf, str) or not isinstance(kind, str):
            log.warning("parser_extensions: skip row %s (bad types)", i)
            continue
        if not isinstance(module, str) or not module.startswith(_ALLOWED_MODULE_PREFIX):
            log.warning(
                "parser_extensions: skip %s — module must start with %r",
                suf,
                _ALLOWED_MODULE_PREFIX,
            )
            continue
        if not isinstance(fn, str) or not fn.isidentifier():
            log.warning("parser_extensions: skip %s — bad function name", suf)
            continue
        norm = _norm_suffix(suf)
        if not _SUFFIX_RE.match(norm):
            log.warning("parser_extensions: skip unsafe suffix %r", suf)
            continue
        out[norm] = (kind.strip(), module, fn)
    return out


def load_manifest_file(path: Path) -> Dict[str, Tuple[str, str, str]]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("parser_extensions: invalid JSON in %s: %s", path, e)
        return {}
    if not isinstance(raw, dict):
        return {}
    return parse_manifest(raw)
