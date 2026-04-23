from __future__ import annotations

import json

import pytest

from telemetry_feed import iter_telemetry_sse_events, read_telemetry_tail, redact_event


def test_redact_event_masks_sensitive_keys():
    raw = {"kind": "search", "query": "secret", "path": "/p", "top_path": "/t", "returned": 1}
    r = redact_event(raw)
    assert r["query"] == "[redacted]"
    assert r["path"] == "[redacted]"
    assert r["top_path"] == "[redacted]"
    assert r["returned"] == 1


def test_read_telemetry_tail_empty_dir(tmp_path):
    out = read_telemetry_tail(tmp_path, max_lines=50, max_bytes=10_000, redacted=False)
    assert out["events"] == []
    assert out["count"] == 0
    assert out["telemetry_file_hint"] is not None


def test_read_telemetry_tail_parses_and_redacts(tmp_path):
    p = tmp_path / "telemetry.jsonl"
    p.write_text(
        '{"kind":"search","query":"q1","returned":1}\n'
        '{"kind":"ingest","path":"/x","result":"ok"}\n',
        encoding="utf-8",
    )
    full = read_telemetry_tail(tmp_path, max_lines=10, max_bytes=50_000, redacted=False)
    assert full["count"] == 2
    assert full["events"][0]["query"] == "q1"
    red = read_telemetry_tail(tmp_path, max_lines=10, max_bytes=50_000, redacted=True)
    assert red["events"][0]["query"] == "[redacted]"
    assert red["events"][1]["path"] == "[redacted]"


def test_read_telemetry_tail_skips_bad_json(tmp_path):
    p = tmp_path / "telemetry.jsonl"
    p.write_text('not-json\n{"kind":"x"}\n', encoding="utf-8")
    out = read_telemetry_tail(tmp_path, max_lines=10, max_bytes=50_000, redacted=False)
    assert len(out["events"]) == 1
    assert out["events"][0]["kind"] == "x"


def test_sse_initial_window_redacted(tmp_path, monkeypatch):
    monkeypatch.setattr("telemetry_feed.time.sleep", lambda _s: None)
    p = tmp_path / "telemetry.jsonl"
    p.write_text('{"kind":"search","query":"secret"}\n', encoding="utf-8")
    gen = iter_telemetry_sse_events(tmp_path, redacted=True)
    line = next(gen)
    assert line.startswith("data: ")
    payload = json.loads(line[len("data: ") :].strip())
    assert payload["event"]["query"] == "[redacted]"


def test_sse_truncation_follows_new_file(tmp_path, monkeypatch):
    monkeypatch.setattr("telemetry_feed.time.sleep", lambda _s: None)
    p = tmp_path / "telemetry.jsonl"
    p.write_text('{"a": 1}' + (" " * 120) + "\n", encoding="utf-8")
    gen = iter_telemetry_sse_events(tmp_path, redacted=False)
    first = next(gen)
    assert json.loads(first[len("data: ") :].strip())["event"]["a"] == 1

    p.write_text('{"b": 2}\n', encoding="utf-8")
    second = next(gen)
    ev = json.loads(second[len("data: ") :].strip())
    assert "event" in ev
    assert ev["event"]["b"] == 2


def test_http_diagnostics_telemetry(sidecar):
    tel = sidecar.data_dir / "telemetry.jsonl"
    tel.write_text('{"kind":"search","query":"hi","returned":1}\n', encoding="utf-8")
    r = sidecar.get("/diagnostics/telemetry?lines=10")
    r.raise_for_status()
    body = r.json()
    assert body["count"] == 1
    assert body["events"][0]["query"] == "hi"
    r2 = sidecar.get("/diagnostics/telemetry?lines=10&redacted=true")
    r2.raise_for_status()
    assert r2.json()["events"][0]["query"] == "[redacted]"
