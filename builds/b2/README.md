# Build 2: Agent Traffic Dashboard as a WhatsApp group

Second build, from `SPEC.md` at commit `d944d82` (the WhatsApp-style group chat spec).
Python 3.8+ standard library only, nothing to install.

```bash
# from the repo root, three terminals:
python3 proxy.py --port 8041                                                # 1. the given proxy, unchanged
python3 builds/b2/dashboard.py --port 8042 --upstream http://localhost:8041  # 2. the dashboard
ANTHROPIC_BASE_URL=http://localhost:8042 claude                             # 3. the agent
# open http://localhost:8042/dashboard
```

What you see:
- Left: the chat list (main chat, one chat per sub-agent, one "Side requests" chat) with previews, times, unread counters and ⚠️ for chats with errors.
- Center: the group chat. You on the right, Claude and the tools on the left. Every tool call: Claude's bubble shows the call, "🔧 X joined the group", "X is typing...", X's reply quoting the call, "🔧 X left the group".
- Right (click the chat header): group info with the system prompt, the tools, totals, and tool-call counts.

Files:
- `dashboard.py`: pass-through proxy + SSE event stream + reply reassembly + price table (same backend as build 1).
- `dashboard.html`: the page (inline CSS and JS, no external resources).
- `ASSUMPTIONS.md`: every choice the spec did not settle, and questions for the next spec version.
