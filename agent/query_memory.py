#!/usr/bin/env python3
import json
import os
import sys

import numpy as np
from sentence_transformers import SentenceTransformer


AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
CHUNKS_PATH = f"{AGENT_DIR}/memory_chunks.jsonl"
EMBEDDINGS_PATH = f"{AGENT_DIR}/memory_embeddings.npy"
MANIFEST_PATH = f"{AGENT_DIR}/memory_manifest.json"


def load_manifest():
    with open(MANIFEST_PATH) as fh:
        return json.load(fh)


def load_chunks():
    chunks = []
    with open(CHUNKS_PATH) as fh:
        for line in fh:
            chunks.append(json.loads(line))
    return chunks


def search(query, top_k=8, role=None):
    manifest = load_manifest()
    model = SentenceTransformer(manifest["model_name"])
    chunks = load_chunks()
    embeddings = np.load(EMBEDDINGS_PATH)

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0]

    scores = embeddings @ query_embedding
    ranked = np.argsort(-scores)

    results = []
    for idx in ranked:
        chunk = chunks[idx]
        if role and chunk["role"] != role:
            continue
        results.append(
            {
                "score": float(scores[idx]),
                "chunk_id": chunk["chunk_id"],
                "role": chunk["role"],
                "conversation_title": chunk["conversation_title"],
                "text": chunk["text"],
            }
        )
        if len(results) >= top_k:
            break
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: query_memory.py 'query text' [top_k] [role]")
        sys.exit(1)

    query = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    role = sys.argv[3] if len(sys.argv) > 3 else None

    results = search(query, top_k=top_k, role=role)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
