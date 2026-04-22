#!/usr/bin/env python3
import glob
import json
import os
import re
from collections import Counter


EXPORT_DIR = "/Users/reify/Classified/minion/d9eced211a2a0b9cd1b2d52f595ee063aea7ff88cddbcaad683ae4aa25df7992-2026-03-21-20-25-15-b54da2dcfb0a4295aae2c768c88d320c"
OUTPUT_PATH = "/Users/reify/Classified/minion/persona_sourcebook.md"
QUOTE_BANK_PATH = "/Users/reify/Classified/minion/persona_quote_bank.md"


def get_linear_path(mapping, current_node):
    path = []
    node_id = current_node
    while node_id:
        node = mapping.get(node_id)
        if not node:
            break
        path.append(node_id)
        node_id = node.get("parent")
    return list(reversed(path))


def extract_text(parts):
    texts = []
    for part in parts:
        if isinstance(part, str):
            part = part.strip()
            if part:
                texts.append(part)
    return "\n".join(texts).strip()


def normalize_text(text):
    text = text.replace("\r\n", "\n").strip()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def split_sentences(text):
    text = text.replace("\n", " ")
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip(" -") for part in parts if part.strip(" -")]


def looks_like_noise(text):
    lowered = text.lower()
    noisy_markers = [
        "traceback",
        "localhost:",
        "request payload",
        "response status",
        "response headers",
        "payload json",
        "memory stats",
        "cli launched successfully",
        "server url:",
        "total tokens:",
        "estimated cost:",
        "api called with tokens",
        "```",
        "~/",
        "╔",
        "════════",
        "[verbose",
        "process exited",
    ]
    if any(marker in lowered for marker in noisy_markers):
        return True
    if len(text) > 4000:
        return True
    line_count = text.count("\n") + 1
    if line_count > 35:
        return True
    return False


def is_first_person_statement(text):
    lowered = text.lower()
    first_person_markers = [
        " i ",
        " i'm",
        "i'm ",
        " i’m",
        "my ",
        "mine ",
        "me ",
        "myself",
    ]
    padded = f" {lowered} "
    return any(marker in padded for marker in first_person_markers)


def sentence_is_persona_candidate(sentence):
    if looks_like_noise(sentence):
        return False
    if len(sentence) < 24 or len(sentence) > 280:
        return False
    if "http" in sentence.lower():
        return False
    if sentence.count(",") > 6:
        return False
    if not is_first_person_statement(sentence):
        return False
    lowered = sentence.lower().strip()
    bad_starts = [
        "can you",
        "could you",
        "please",
        "what ",
        "why ",
        "how ",
        "pull ",
        "make ",
        "update ",
        "use ",
        "help ",
    ]
    if any(lowered.startswith(prefix) for prefix in bad_starts):
        return False
    return True


def load_conversations():
    files = sorted(glob.glob(os.path.join(EXPORT_DIR, "conversations-*.json")))
    conversations = []
    for path in files:
        with open(path) as fh:
            data = json.load(fh)
        if isinstance(data, list):
            conversations.extend(data)
        else:
            conversations.append(data)
    return conversations


def extract_user_messages(conversations):
    messages = []
    for conv in conversations:
        mapping = conv.get("mapping", {})
        current_node = conv.get("current_node")
        if not mapping or not current_node:
            continue

        title = conv.get("title") or "(untitled)"
        conv_id = conv.get("id") or conv.get("conversation_id") or "unknown"
        for node_id in get_linear_path(mapping, current_node):
            node = mapping.get(node_id) or {}
            msg = node.get("message") or {}
            if msg.get("author", {}).get("role") != "user":
                continue
            content = msg.get("content") or {}
            if content.get("content_type") != "text":
                continue
            text = extract_text(content.get("parts") or [])
            text = normalize_text(text)
            if not text:
                continue
            messages.append(
                {
                    "conversation_title": title,
                    "conversation_id": conv_id,
                    "create_time": msg.get("create_time"),
                    "text": text,
                }
            )
    return messages


def bucket_message(text):
    lowered = text.lower()
    if any(word in lowered for word in ["i am", "i'm", "my name", "about me", "who i am"]):
        return "Identity"
    if any(word in lowered for word in ["i want", "my goal", "i'm trying", "i need to", "i hope to"]):
        return "Goals"
    if any(word in lowered for word in ["i like", "i prefer", "i love", "i hate", "i don't like"]):
        return "Preferences"
    if any(word in lowered for word in ["believe", "value", "important to me", "principle", "conviction"]):
        return "Values"
    if any(word in lowered for word in ["project", "business", "company", "client", "dashboard", "build", "working on"]):
        return "Projects"
    if any(word in lowered for word in ["write", "tone", "voice", "style", "wording"]):
        return "Writing Style"
    return "Raw Statements"


def choose_representative_messages(messages, max_per_bucket=80):
    dedup = {}
    counts = Counter()
    for message in messages:
        text = message["text"]
        counts[text] += 1
        if text not in dedup:
            dedup[text] = message

    buckets = {}
    for text, message in dedup.items():
        bucket = bucket_message(text)
        buckets.setdefault(bucket, []).append((counts[text], message))

    for bucket in buckets:
        buckets[bucket].sort(
            key=lambda item: (
                -item[0],
                -len(item[1]["text"]),
                item[1]["conversation_title"].lower(),
            )
        )
        buckets[bucket] = [item[1] for item in buckets[bucket][:max_per_bucket]]
    return buckets, counts


def choose_persona_messages(messages, counts, max_per_bucket=40):
    buckets = {}
    for message in messages:
        text = message["text"]
        if looks_like_noise(text):
            continue
        if not is_first_person_statement(text):
            continue
        bucket = bucket_message(text)
        buckets.setdefault(bucket, []).append((counts[text], message))

    for bucket in buckets:
        buckets[bucket].sort(
            key=lambda item: (
                -item[0],
                -len(item[1]["text"]),
                item[1]["conversation_title"].lower(),
            )
        )
        chosen = []
        seen_titles = set()
        for _, message in buckets[bucket]:
            title = message["conversation_title"]
            if len(chosen) >= max_per_bucket:
                break
            if title in seen_titles and len(chosen) >= max_per_bucket // 2:
                continue
            chosen.append(message)
            seen_titles.add(title)
        buckets[bucket] = chosen
    return buckets


def render_sourcebook(messages, buckets, counts):
    lines = []
    unique_messages = len(counts)
    lines.append("# Persona Sourcebook")
    lines.append("")
    lines.append("This file uses only user-authored text taken from the ChatGPT export.")
    lines.append("It is intended as raw first-person persona material, not a paraphrased summary.")
    lines.append("")
    lines.append(f"- Total user messages extracted: {len(messages)}")
    lines.append(f"- Unique user messages after exact dedupe: {unique_messages}")
    lines.append("")

    preferred_order = [
        "Identity",
        "Goals",
        "Preferences",
        "Values",
        "Projects",
        "Writing Style",
        "Raw Statements",
    ]

    for bucket in preferred_order:
        items = buckets.get(bucket)
        if not items:
            continue
        lines.append(f"## {bucket}")
        lines.append("")
        for item in items:
            title = item["conversation_title"]
            count = counts[item["text"]]
            lines.append(f"> {item['text'].replace(chr(10), chr(10) + '> ')}")
            lines.append("")
            lines.append(f"Source conversation: {title}")
            if count > 1:
                lines.append(f"Repeated exact message count: {count}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_quote_bank(messages):
    seen = set()
    buckets = {}
    for message in messages:
        for sentence in split_sentences(message["text"]):
            sentence = normalize_text(sentence)
            if not sentence_is_persona_candidate(sentence):
                continue
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            bucket = bucket_message(sentence)
            buckets.setdefault(bucket, []).append(
                {
                    "text": sentence,
                    "conversation_title": message["conversation_title"],
                }
            )

    lines = []
    lines.append("# Persona Quote Bank")
    lines.append("")
    lines.append("Short first-person lines pulled verbatim from user messages.")
    lines.append("")
    for bucket in ["Identity", "Goals", "Preferences", "Values", "Projects", "Writing Style", "Raw Statements"]:
        items = buckets.get(bucket, [])
        if not items:
            continue
        lines.append(f"## {bucket}")
        lines.append("")
        for item in items[:120]:
            lines.append(f'- "{item["text"]}"')
            lines.append(f'  Source conversation: {item["conversation_title"]}')
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    conversations = load_conversations()
    messages = extract_user_messages(conversations)
    _, counts = choose_representative_messages(messages)
    buckets = choose_persona_messages(messages, counts)
    content = render_sourcebook(messages, buckets, counts)
    quote_bank = build_quote_bank(messages)
    with open(OUTPUT_PATH, "w") as fh:
        fh.write(content)
    with open(QUOTE_BANK_PATH, "w") as fh:
        fh.write(quote_bank)
    print(OUTPUT_PATH)
    print(QUOTE_BANK_PATH)
    print(f"user_messages={len(messages)} unique_messages={len(counts)}")


if __name__ == "__main__":
    main()
