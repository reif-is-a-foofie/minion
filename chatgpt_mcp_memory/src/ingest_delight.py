"""Optional upbeat one-liner after a successful ingest (tiny local Ollama model).

Set ``MINION_DELIGHT_MODEL`` to a small pulled model (default ``qwen2.5:0.5b``).
Disable with ``MINION_DELIGHT_MODEL=off`` or ``none``.

Env:
  MINION_OWNER_NAME      First name used naturally in the line (optional).
  MINION_DELIGHT_MAX_BATCH_TOTAL   Skip delights when batch > this (default 40).
  MINION_DELIGHT_TIMEOUT   Seconds for the Ollama call (default 12).
  MINION_DELIGHT_PREVIEW_CHARS   Max chars of embedded chunk text sent to the model (default 1800).
"""
from __future__ import annotations

import logging
import os
import random
from pathlib import Path
from typing import Optional

log = logging.getLogger("minion.ingest_delight")


def max_batch_total() -> int:
    try:
        return max(1, int(os.environ.get("MINION_DELIGHT_MAX_BATCH_TOTAL", "40")))
    except ValueError:
        return 40


def should_run_delight(batch_total: int) -> bool:
    """Avoid hammering Ollama during huge watcher reconciles."""
    return batch_total <= max_batch_total()


def _preview_chars() -> int:
    try:
        return max(200, min(8000, int(os.environ.get("MINION_DELIGHT_PREVIEW_CHARS", "1800"))))
    except ValueError:
        return 1800


def _indexed_excerpt(db_path: Path, source_id: str) -> str:
    """First chunk(s) of text we literally just stored — grounds the model in real content."""
    from store import connect

    conn = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT text FROM chunks WHERE source_id=? ORDER BY seq ASC LIMIT 12",
            (source_id,),
        ).fetchall()
    finally:
        conn.close()

    max_chars = _preview_chars()
    blob = ""
    for row in rows:
        t = (row["text"] or "").strip()
        if not t:
            continue
        sep = "\n\n" if blob else ""
        addition = sep + t
        if len(blob) + len(addition) <= max_chars:
            blob += addition
        else:
            room = max_chars - len(blob) - len(sep)
            if room > 120:
                blob += sep + t[:room] + "…"
            break
    return blob


def generate_delight_line(
    path: Path,
    kind: str,
    chunk_count: int,
    *,
    db_path: Path,
    source_id: str,
) -> Optional[str]:
    raw = os.environ.get("MINION_DELIGHT_MODEL", "qwen2.5:0.5b").strip()
    if not raw or raw.lower() in ("0", "off", "false", "none"):
        return None

    owner = os.environ.get("MINION_OWNER_NAME", "").strip()
    try:
        timeout = float(os.environ.get("MINION_DELIGHT_TIMEOUT", "12"))
    except ValueError:
        timeout = 12.0

    first = owner.split()[0] if owner else ""
    excerpt = _indexed_excerpt(db_path, source_id)

    system = (
        "You reply with exactly one short sentence (max 22 words). Warm, witty, genuinely pleased. "
        "Minion literally just embedded this file — the excerpt below is real indexed text from it, "
        "not a guess. Say something specific about what this document actually is or covers; "
        "avoid generic filler. Plain text only: no markdown, no quotation marks wrapping the reply."
    )
    user_parts = [
        f"Filename: {path.name}",
        f"Kind: {kind}",
        f"Chunks indexed: {chunk_count}",
    ]
    if excerpt.strip():
        user_parts.append(
            "Indexed text preview (first chunk(s), verbatim — this is what was embedded):\n"
            + excerpt.strip()
        )
    else:
        user_parts.append(
            "(No text preview available yet — infer lightly from filename/kind only.)"
        )
    if first:
        user_parts.append(
            f"If it feels natural, address them by this first name once: {first}. "
            "Otherwise use 'you'."
        )
    user = "\n".join(user_parts)

    try:
        from llm import chat

        temp = 0.82 + random.random() * 0.15
        out = chat(
            model=raw,
            system=system,
            user=user,
            options={"temperature": temp},
            timeout_seconds=timeout,
        )
        line = out.content.strip().replace("\n", " ")
        line = " ".join(line.split())
        if len(line) > 180:
            line = line[:177] + "…"
        return line or None
    except Exception as e:
        log.debug("ingest delight skipped: %s", e)
        return None
