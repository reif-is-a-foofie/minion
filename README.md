# What the heck is this thing and why should I care about it?

Well, like me, you are probably realizing by now that you have wasted a lot of your life reading slop from ChatGPT when you could have been making progress with Claude.

I made my move to Claude recently and I realized, well, I have my whole life on GPT. That thing knows more about me than my doctor, my shrink, and Siri combined times 6. And Claude doesn't know me from Adam other than it knows I'm not Adam. At least, most likely not Adam.

OpenAI lets you export all of your chats (takes a few days). Then I needed to push that context back into Claude. But how?? I can't just load 30 million messages into Claude (real message count BTW, wild). And given Claude spends more tokens than a kid at nickel-mania who just drank his first Red Bull, loading the whole thing was off the table.

So we go the encoding + semantic search route. Hook it up to an MCP that runs locally, so at run time Claude can query my personal data and ONLY take in the context that matters.

It's alpha. Stretch alpha hard enough and bad things could happen. But at least I am committed to using my own software on my own personal setup.

Ping me with questions,

Reif

-reif@thegoodproject.net

## What Claude actually gets

Two things, automatically, on every session:

1. **Retrieval**. An MCP server (this repo) that lets Claude search your chat history and any file you drop into the inbox. It exposes 8 tools: `ask_minion` (semantic, keyword, and temporal search), `get_chunk`, `browse_conversations`, `conversation_chunks`, `list_sources`, `index_info`, plus the voice tools below. Claude decides when to call them.
2. **Voice**. A durable `voice.md` profile (preferences, nevers, style rules, writers you want emulated) that gets injected into Claude's system prompt every session. You don't write it. On first run, Claude reads your chat history, figures out how you actually write, and commits the profile. From then on, if you state a new rule mid-conversation ("actually, I hate bullet lists"), Claude confirms and appends it via `append_to_voice`. The profile evolves from the chats, not from a text editor.

The voice tool (`commit_voice` on first run, `append_to_voice` after) is what turns "Claude knows me" from a one-time paste into something that actually stays current.

## Install

Mac, Homebrew:

```bash
brew tap reif-is-a-foofie/minion
brew install minion
minion doctor
```

Prereqs: Ollama running, with whatever model you want for the profile generator (default `mistral:7b`).

## Run it

Open a terminal, type `minion`, hit enter. That's the whole interface. It asks you for the path to your ChatGPT export zip, unpacks it, builds the index, pulls persona evidence, writes `core_profile.md`, and merges the MCP entry into Claude Desktop's config (with a backup). One command, one pipeline.

Non-interactive version for scripts:

```bash
minion setup /path/to/chatgpt-export.zip
```

After it finishes: **quit and reopen Claude Desktop** so it picks up the MCP server. First session with the new config does the voice bootstrap silently in the background. Ask Claude something like "what do you know about me?" and it will call `ask_minion` and tell you.

Paste `core_profile.md` and `retrieval_policy.md` from your run folder into Claude's Custom Instructions if you want the strategic layer pinned. Optional but recommended.

## Drop stuff in

There's a desktop app (Tauri + SvelteKit, same SQLite + sqlite-vec store as the CLI). Drop any file onto the window, PDF, image, audio, markdown, code, and every MCP-speaking agent (Claude Desktop, Cursor, whatever) can read it.

```bash
cd desktop
npm install
npm run tauri dev
```

Without the app, drop files into `data/inbox/`. The watcher inside `minion mcp` reconciles on startup and then live-watches. CRUD commands: `minion add`, `minion ls`, `minion rm`, `minion watch`.

See [`desktop/README.md`](./desktop/README.md) for the app, [`chatgpt_mcp_memory/README.md`](./chatgpt_mcp_memory/README.md) for everything else (parsers, tool surface table, voice internals, env knobs).

## Privacy

Nothing leaves the machine. The index is a single SQLite file (`memory.db`) with sqlite-vec for KNN. MCP runs over stdio, no network ports. The only network-adjacent thing is optional Ollama image captioning, off unless `MINION_VISION_MODEL` is set. Keep your raw export and derived artifacts outside the repo (I use a sibling `minion_private/` folder).

## What you actually get out of this

A useful "you" profile rebuilt from your own writing, not a personality you hand-authored. An assistant that stays consistent over time without you restuffing history into every chat. Real "how you said it" evidence when you're writing or deciding or delegating. A voice that sharpens itself session over session instead of drifting.

Auditable all the way down: every profile is generated from quotes, every voice directive ties back to a chunk, every build writes a manifest.
