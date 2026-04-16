# ChatGPT Export → Claude Desktop MCP (Local)

This turns a freshly-downloaded ChatGPT export **ZIP** into:

- a few **pasteable persona** files (`core_profile.md`, `retrieval_policy.md`)
- an **on-demand semantic memory** MCP server (Claude Desktop calls tools like `search_memory`)

Nothing is uploaded. The index lives on local disk.

## 0) Prereqs (Intel macOS)

- Python 3.10+ recommended (`python3 --version`)
- Ollama installed + running (`ollama serve`)
- Pull the default model once: `ollama pull mistral:7b`
- Claude Desktop installed

## 1) Create a virtualenv + install deps

From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Ingest a ChatGPT export ZIP

Put the ChatGPT export zip somewhere (example: `~/Downloads/chatgpt-export.zip`), then:

```bash
source .venv/bin/activate
python src/ingest_chatgpt_export.py ~/Downloads/chatgpt-export.zip
```

This prints the **export root directory** it found (contains `conversations-*.json`).

## 3) Build the semantic index

Use the printed export root:

```bash
source .venv/bin/activate
python src/build_index.py --export "/path/printed/by/ingest"
```

Outputs:

- `data/derived/chunks.jsonl`
- `data/derived/embeddings.npy`
- `data/derived/manifest.json`

Optional: include assistant messages too:

```bash
python src/build_index.py --export "/path/to/export" --include-assistant
```

## 4) Build persona artifacts (optional but recommended)

```bash
source .venv/bin/activate
python src/persona_extract.py --export "/path/to/export"
```

Outputs:

- `data/derived/persona_sourcebook.md`
- `data/derived/persona_quote_bank.md`

## 5) Generate `core_profile.md` (recommended)

This produces a **derived** `core_profile.md` from the export-backed persona evidence (no hardcoded personality).

```bash
source .venv/bin/activate
python src/generate_core_profile.py --model mistral:7b
```

Outputs:

- `core_profile.md` (generated)
- `data/derived/core_profile_manifest.json` + `data/derived/core_profile.built` (build marker + metadata)

## 6) Pasteable persona for Claude

In Claude, paste content from:

- `core_profile.md`
- `retrieval_policy.md`

Optionally also attach / paste selected sections from:

- `data/derived/persona_sourcebook.md`
- `data/derived/persona_quote_bank.md`

## 7) Wire it into Claude Desktop (MCP)

Claude Desktop reads:

- `~/Library/Application Support/Claude/claude_desktop_config.json`

Copy `claude_desktop_config.example.json` to that location (or merge it) and replace paths:

- `command`: point to this project’s venv python: `.../chatgpt_mcp_memory/.venv/bin/python`
- `args[0]`: path to `.../chatgpt_mcp_memory/src/mcp_server.py`
- `CHATGPT_MCP_DATA_DIR`: path to `.../chatgpt_mcp_memory/data/derived`

Restart Claude Desktop after editing the config.

## 8) Verify inside Claude

Ask Claude:

- “Call `index_info`.”
- “Call `search_memory` for `Good Capital` with `top_k=6`.”
- “Take the top hit `chunk_id` and call `get_chunk`.”

## Privacy + token discipline (how this stays cheap)

- The full index stays on disk (`embeddings.npy`, `chunks.jsonl`).
- Claude only receives **top-k short snippets** (default `top_k=8`, `max_chars=900`).

## Future sources (extensibility)

Add new `ingest_*.py` scripts that convert a source into the same internal message/chunk format, then reuse `build_index.py`.

