# Minion

Minion is a local-first “memory + assistant” setup.

It helps you turn your ChatGPT export into:
- a small, stable profile you can paste into an assistant
- an on-demand memory search you can query when you need real past context

Nothing needs to be uploaded. The point is to keep your data on your machine and still get leverage from it.

## What you do with it

- Rebuild a usable “you” profile from your own writing (not hand-authored personality)
- Look up how you previously described something (projects, priorities, preferences) when you’re writing or deciding
- Keep an assistant consistent over time without stuffing long history into every chat

## Privacy

This repo is set up to avoid committing raw exports, derived embeddings, or personal quote banks.
You generate those locally when you need them.

## Quick start (high level)

1) Download your ChatGPT data export
2) Run the local tools to ingest + build memory
3) Generate the core profile from evidence
4) Use the profile + memory search in your assistant

Technical instructions live in `chatgpt_mcp_memory/README.md`.

