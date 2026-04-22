"""Portable export: zip manifest + identity snapshot (+ optional chunk id listing)."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict

import sqlite3

from identity import export_identity_snapshot, snapshot_manifest_hash
from store import count_chunks, count_sources


def write_identity_export_zip(
    conn: sqlite3.Connection,
    *,
    out_path: Path,
    include_chunk_index: bool = True,
) -> Dict[str, Any]:
    """Write a zip with `manifest.json` and `identity.json` (full snapshot).

    `include_chunk_index` adds `chunk_index.json` with chunk_id list only (no text)
    for coarse corpus fingerprinting without bulk export.
    """
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

    return {"path": str(out_path), "manifest": manifest}


def read_identity_export_zip(zip_path: Path) -> Dict[str, Any]:
    """Read bundle from disk (for verification / future import tooling)."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        identity = json.loads(zf.read("identity.json").decode("utf-8"))
    return {"manifest": manifest, "identity": identity}
