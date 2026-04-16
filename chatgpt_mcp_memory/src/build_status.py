from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class CoreProfileBuildStatus:
    built: bool
    manifest_path: str
    marker_path: str
    manifest: Optional[Dict[str, Any]]


def _default_derived_dir() -> Path:
    env = os.environ.get("CHATGPT_MCP_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    # chatgpt_mcp_memory/src/build_status.py -> parents[1] is chatgpt_mcp_memory
    return Path(__file__).resolve().parents[1] / "data" / "derived"


def core_profile_status(*, derived_dir: Optional[str] = None) -> CoreProfileBuildStatus:
    d = Path(derived_dir).expanduser().resolve() if derived_dir else _default_derived_dir()
    marker = d / "core_profile.built"
    manifest_path = d / "core_profile_manifest.json"

    if not marker.exists() or not manifest_path.exists():
        return CoreProfileBuildStatus(
            built=False,
            manifest_path=str(manifest_path),
            marker_path=str(marker),
            manifest=None,
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        manifest = None

    return CoreProfileBuildStatus(
        built=True,
        manifest_path=str(manifest_path),
        marker_path=str(marker),
        manifest=manifest if isinstance(manifest, dict) else None,
    )

