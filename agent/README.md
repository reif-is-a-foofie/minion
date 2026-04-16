# Reif Agent Bundle

This directory contains a hybrid persona setup:

- `core_profile.md`: short structured profile for stable high-signal context
- `retrieval_policy.md`: rules for when to trust profile vs semantic memory
- `build_semantic_memory.py`: builds a sentence-transformer index from the ChatGPT export
- `query_memory.py`: semantic search over the built index

After building, this directory will also contain:

- `memory_chunks.jsonl`
- `memory_embeddings.npy`
- `memory_manifest.json`

Recommended usage:

1. Load `core_profile.md` first.
2. Follow `retrieval_policy.md`.
3. Query the semantic index when task-specific personal context is needed.

Notes:

- The semantic index can be built locally from the export with:
  - `python3 build_semantic_memory.py /path/to/export`
- `query_memory.py` requires `sentence-transformers` and `numpy`.
- If those libraries are not installed on the VM, the bundle still transfers cleanly, but semantic querying on the VM will require a small Python environment there.
