# Build 4: Agent Traffic Dashboard as a WhatsApp group, round 4

Fourth build, from `SPEC.md` at commit `8aa34b1` (spec round 4: answers to build 3's questions + polls, reactions, forwards, media list, stars, dark mode).
Python 3.8+ standard library only, nothing to install.

```bash
# from the repo root, three terminals:
python3 proxy.py --port 8041                                                # 1. the given proxy, unchanged
python3 builds/b4/dashboard.py --port 8042 --upstream http://localhost:8041  # 2. the dashboard
ANTHROPIC_BASE_URL=http://localhost:8042 claude                             # 3. the agent
# open http://localhost:8042/dashboard
```

New since build 3:
- `first_byte` is now part of the schema (build 3 already sent it; backend unchanged apart from its header).
- Turn 1 gets a divider before the first prompt, like every other turn.
- 📌 pinned plan is also fed by `TaskCreate` (adds an item) and `TaskUpdate` (changes status), matched by task id or subject.
- "🤖 Main agent" bubbles in sub-agent chats use the soft slate color.
- 📊 `AskUserQuestion` is a poll card; after the answer the chosen option gets ✅ and "You voted" (or "Other: …").
- ✅ / ❌ reaction on each tool call when its answer arrives; click it to jump to the answer.
- `Agent`/`Task` answers are "↪ Forwarded from <sub-agent chat>" (click opens it); the sub-agent chat starts with "↪ Started by Main agent in …" (click goes back).
- Group info: "Media, links and docs" (files with 📄 reads / ✏️ edits, WebFetch links) and "Starred messages".
- ☆ on hover stars a bubble (⭐); stars are in memory only and go away with Clear.
- 🌙 / ☀️ dark mode, starts from `prefers-color-scheme`, kept in `localStorage`.

Files:
- `dashboard.py`: same as build 3 (context-window table, `first_byte` event).
- `dashboard.html`: the page (inline CSS and JS, no external resources).
- `ASSUMPTIONS.md`: choices the spec did not settle, and questions for the next spec version.
