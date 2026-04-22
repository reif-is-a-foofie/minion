"""Portable export: zip manifest + identity snapshot + optional voice/brief files."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

import sqlite3

from identity import export_identity_snapshot, snapshot_manifest_hash
from store import count_chunks, count_sources


def _maybe_read(path: Path) -> Optional[str]:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    except OSError:
        pass
    return None


def write_identity_export_zip(
    conn: sqlite3.Connection,
    *,
    out_path: Path,
    data_dir: Optional[Path] = None,
    include_chunk_index: bool = True,
    include_voice_files: bool = True,
) -> Dict[str, Any]:
    """Write zip: manifest.json, identity.json, optional chunk_index, voice.md, brief files."""
    out_path = Path(out_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    snapshot = export_identity_snapshot(conn)
    digest = snapshot_manifest_hash(snapshot)
    manifest: Dict[str, Any] = {
        "format": "minion-export",
        "version": 1,
        "integrity_sha256_16": digest,
        "sources": count_sources(conn),
        "chunks": count_chunks(conn),
        "claims": len(snapshot.get("claims", [])),
        "edges": len(snapshot.get("edges", [])),
        "preference_clusters": len(snapshot.get("preference_clusters", [])),
    }

    dd = Path(data_dir).expanduser().resolve() if data_dir else None
    voice_files: Dict[str, str] = {}

    if include_voice_files and dd is not None:
        voice = _maybe_read(dd / "voice.md")
        if voice is not None:
            voice_files["voice.md"] = voice
            manifest["includes_voice_md"] = True
        for name in ("brief.md", "core_profile.md", "identity_profile.md"):
            txt = _maybe_read(dd / name)
            if txt is not None:
                voice_files[name] = txt
                manifest[f"includes_{name.replace('.', '_')}"] = True

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "manifest.json",
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        )
        zf.writestr(
            "identity.json",
            json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        )
        if include_chunk_index:
            rows = conn.execute("SELECT chunk_id FROM chunks ORDER BY chunk_id").fetchall()
            index = {"chunk_ids": [r["chunk_id"] for r in rows]}
            zf.writestr(
                "chunk_index.json",
                json.dumps(index, indent=2, ensure_ascii=False) + "\n",
            )
        for arcname, content in voice_files.items():
            zf.writestr(arcname, content)

    return {"path": str(out_path), "manifest": manifest}


def read_identity_export_zip(zip_path: Path) -> Dict[str, Any]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        identity = json.loads(zf.read("identity.json").decode("utf-8"))
    return {"manifest": manifest, "identity": identity}
