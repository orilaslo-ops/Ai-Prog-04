# Build 3: Agent Traffic Dashboard as a WhatsApp group, with WhatsApp touches

Third build, from `SPEC.md` at commit `f22ef13` (spec round 3: answers to build 2's questions + section 12).
Python 3.8+ standard library only, nothing to install.

```bash
# from the repo root, three terminals:
python3 proxy.py --port 8041                                                # 1. the given proxy, unchanged
python3 builds/b3/dashboard.py --port 8042 --upstream http://localhost:8041  # 2. the dashboard
ANTHROPIC_BASE_URL=http://localhost:8042 claude                             # 3. the agent
# open http://localhost:8042/dashboard
```

New since build 2:
- Main chat vs sub-agent: a chat is a sub-agent when its first message is the `prompt` of an `Agent`/`Task` call. Its prompts come from "🤖 Main agent".
- Chat list: main pinned on top, the rest sorted by last activity.
- Forked requests (same history + one extra message) are moved to "Side requests" as "fork of <chat>".
- Tool filter keeps your messages visible, dimmed.
- Section 12: ✓ / ✓✓ / blue ✓✓ ticks, 📌 pinned TodoWrite plan, 📄 file cards for Read/Write, red/green Edit diffs, turn dividers with a summary, 🔋 context meter, status line, dark terminal bubbles for Bash.

Files:
- `dashboard.py`: build 2 backend + a context-window table (`context_window` in the reply event) + a `first_byte` event for the ticks.
- `dashboard.html`: the page (inline CSS and JS, no external resources).
- `ASSUMPTIONS.md`: choices the spec did not settle, and questions for the next spec version.
