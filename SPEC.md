# Agent Traffic Dashboard

## Overview
A live, read-only browser dashboard that displays messages flowing between an agent (Claude Code) and the Claude API in real time. As the agent works, the user watches the full back-and-forth: their prompts, Claude's responses, tool calls, and tool results, shown as a WhatsApp-style group chat so it is scannable at a glance.

## Design Constraints
**Readability is the primary goal.** The dashboard is useless if the user cannot distinguish message types in a crowded transcript as the conversation grows. Every UI choice must serve legibility.

**Technical constraints:**
- `proxy.py` is given and **must not be modified**. The dashboard is built around it, in a new file (`dashboard.py`).
- Python 3 standard library only. No pip, no npm, no build step.
- The page is a single self-contained HTML file (inline CSS and JS), served by `dashboard.py`. No CDN or external resources.
- v1 supports **Claude Code / Anthropic Messages API traffic only** (not Codex / OpenAI formats).

## How to Run
```
python3 proxy.py --port 8041                                   # terminal 1: the given proxy, unchanged
python3 dashboard.py --port 8042 --upstream http://localhost:8041   # terminal 2
ANTHROPIC_BASE_URL=http://localhost:8042 claude                # terminal 3: the agent
# open http://localhost:8042/dashboard in a browser
```
- `dashboard.py` is itself a pass-through reverse proxy: it forwards every request to `--upstream` unchanged and streams the reply back byte for byte, while recording a copy for the dashboard. The agent must behave exactly as it does without the dashboard.
- `--port` (default 8042) and `--upstream` (default `http://localhost:8041`) are command-line flags, so several builds can run side by side on different ports.
- The UI lives under `/dashboard` (page) and `/dashboard/events` (SSE stream). Every other path is forwarded upstream.
- Listen on `127.0.0.1` only.

## Core Requirement
The dashboard looks and works like a **WhatsApp group chat**. The agent's work is shown as a conversation in a group: you, Claude, and the tools Claude calls are the members, and every message flowing between the agent and the API appears as a chat message, **oldest at the top, newest at the bottom**, like any chat app.

The dashboard is read-only: there is no message input box.

**Members of the group:**
- **👤 You:** the user's text (prompts typed into Claude Code).
- **🤖 Claude:** the model. Its text replies, its thinking, and its tool calls.
- **🔧 Each tool** (`Read`, `Bash`, `Edit`, ...): a temporary member. It joins the group when Claude calls it, answers with its result, and leaves (see section 2).

Claude Code itself (the agent) is **not** a member: it is the group.

**What the chat shows:**
- Each message from the user, from Claude, and from each tool, as a bubble from its sender
- Tools joining and leaving, as centered system lines
- Each tool result as a reply that quotes the tool call it answers
- The system prompt and tool definitions in the group info panel (section 1)

**Global features:**
- Page updates live as messages arrive
- Long text collapsible for readability
- JSON formatted legibly (indented, syntax highlighted)
- Statistics welcome (tokens, cost, latency, tool usage) but secondary to message content

---

## Design Decisions

### 1. Layout
The page has the shape of WhatsApp Web:

- **Chat list (left sidebar):** one row per chat (section 7). Each row shows the chat name, the last message preview, its time, and an unread counter. The main conversation is open by default.
- **Chat header (top):** the group name ("Claude Code"), the model name as a tag, and the members currently in the group ("You, Claude, Read"). Clicking the header opens the group info panel.
- **Group info panel (right side, closed by default):**
  - **System Prompt** (collapsed, heading + line count; click to expand the full text). Note: `system` is an array of blocks, not a string.
  - **Tools Available: N** with the tool names as a comma-separated list; click to see the full schemas.
  - Totals for this chat (tokens, cost) and how many times each tool was called.
- **Chat area (center):** the messages, oldest at the top, newest at the bottom.

**Scrolling:** when the user is at the bottom, new messages scroll into view automatically. When the user has scrolled up to read, the view stays where it is and a "↓ N new messages" button appears at the bottom; clicking it jumps down.

### 2. Tools Join, Answer, and Leave
Tool calls appear in Claude's reply; results come in the next request. They are matched by `tool_use.id` ↔ `tool_result.tool_use_id`.

For **every** tool call (not only the first time a tool is used):
1. Claude's bubble shows the call: tool name in bold and its input.
2. A centered system line: "🔧 Read joined the group".
3. While the result has not arrived: "Read is typing..." at the bottom of the chat.
4. The tool's own bubble with the result, as a **reply that quotes the call** (a small quoted box at the top of the bubble with the tool name and a one-line summary of the input; clicking it scrolls to the call).
5. A centered system line: "🔧 Read left the group".

If Claude calls several tools in one reply, each one joins, answers, and leaves on its own. The header's member list shows the tools that are currently in the group.

**Format:**
```
🤖 Claude
   🔧 Read  { "file_path": "README.md" }
        ── 🔧 Read joined the group ──
🔧 Read
   ┃ Claude: Read README.md
   # Project title ...
        ── 🔧 Read left the group ──
```

**Error result** (`is_error: true`): the tool's bubble is rose with the error message prominent (section 3), and it still leaves the group afterwards.

### 3. Visual Encoding (colors)
Every message type has its own soft, pleasant color and icon, so types can be told apart without a legend. Bubbles have rounded corners, muted pastel backgrounds, and a thin border of the same hue; text stays dark and readable.

**Alignment:** your messages are on the **right**, like your own messages in WhatsApp. Messages from Claude and from tools are on the **left**, with the sender name in bold above the bubble. Each tool name gets its own name color (chosen from a fixed list by the tool name, so `Read` always has the same color).

| Type | Background | Border | Icon |
|---|---|---|---|
| Your prompt (user text) | `#EAF2FB` soft blue | `#5B8DEF` | 👤 |
| Claude text (assistant) | `#EAF7EE` soft green | `#4CAF7A` | 🤖 |
| Tool call (`tool_use`, inside Claude's bubble) | `#FFF4E5` soft peach | `#F0A35E` | 🔧 (tool name in bold) |
| Tool result (tool's own bubble) | `#EEF6F7` soft teal | `#5FA8B0` | ↩ |
| Tool result with error | `#FDECEC` soft rose | `#E06C6C` | ⚠️ |
| Thinking (`thinking`, inside Claude's bubble) | `#F3EEFA` soft lavender | `#9B7FD1` | 💭 (collapsed) |
| System lines (joined / left / changes) | none, centered gray pill | none | small gray text |
| `<system-reminder>` text inside your messages | dimmed, smaller font | none | collapsed |

Chat background is an off-white (`#FAFAF8`). Whitespace between bubbles is generous.

### 4. Content Blocks
Messages contain arrays of content blocks. The dashboard must handle at least: `text`, `tool_use`, `tool_result`, `thinking`, and `image` (shown as a placeholder). `<system-reminder>...</system-reminder>` sections that Claude Code injects into user messages are noise for the reader: show them dimmed and collapsed (see table above). A user message that contains only `tool_result` blocks is not shown as your bubble: its results are shown as the tools' bubbles (section 2).

### 5. Show Each Message Once
Every request resends the whole conversation. The chat shows each message **only once**: when a request arrives, only the messages that are new compared to the previous request of the same chat are added to the chat.

- If the system prompt or the tool list changed from the previous request, add a centered system line ("⚙️ System prompt changed" / "⚙️ Tools changed") and mark the section in the group info panel with a "changed" badge.
- If earlier messages changed (for example after compaction), add a centered system line "⚙️ History was rewritten" and continue from there.

### 6. Streaming Replies
Claude Code sends `"stream": true`, so replies arrive as SSE events (`message_start`, `content_block_start`, `content_block_delta` with `text_delta` / `input_json_delta` / `thinking_delta`, `content_block_stop`, `message_delta`, `message_stop`). `dashboard.py` reassembles them into a complete reply: full text blocks and tool calls with their complete parsed JSON input. Raw `data:` lines are never shown as the reply. Non-streamed (plain JSON) replies are also supported.

While a reply is streaming, the chat shows "Claude is typing..." at the bottom. When the reply is complete, Claude's bubble replaces it.

### 7. Chats: Main, Sub-agents, and Side Requests
Besides the main conversation, Claude Code runs sub-agents and sends side requests. Each one gets its own chat in the chat list, like separate groups in WhatsApp:

- **Main chat:** the conversation with you. Open by default.
- **Sub-agent chats:** each sub-agent is its own chat, named after its first message (cut to ~40 characters), with "🤖 Sub-agent" as its tag.
- **Side requests chat:** one chat that collects all side requests, shown compact and dimmed. A side request is anything that is not `POST /v1/messages` with a non-empty `tools` list (small-model calls for titles or classification, `count_tokens`, `HEAD`/`GET` checks).

A request belongs to an existing chat when its first message is identical to that chat's first message (ignoring `cache_control`). Otherwise it starts a new chat.

### 8. Included Features
- **Message details:** every Claude bubble has a small ⓘ button that opens the full request behind it (model, parameters, HTTP headers, full JSON), collapsed by default. Nothing forces the user to read it, but every part of a request stays reachable.
- **Tool filter:** Dropdown in the chat header. "All" (default) or "Only tool X": shows only Claude's calls to tool X and tool X's answers (with their join/leave lines). Updates the view in real time.
- **Error highlighting:** Tool results with `is_error: true` are rose tool bubbles. HTTP errors (status ≥ 400) or an `error` SSE event appear as a rose bubble from Claude with the status and error message. A counter in the header ("⚠️ 3 errors") jumps to the next error when clicked. Errors do **not** change the order of the chat. Chats with errors show a ⚠️ in the chat list.
- **Stats:** under each Claude bubble, in small muted gray text where WhatsApp shows the time: clock time | input tokens | cache read | cache creation | output tokens | latency (time to first byte and total) | cost. Tool bubbles show only the clock time. Totals and tool usage counts per tool are in the group info panel.
- **Cost:** Computed from a hard-coded per-model price table in `dashboard.py` (input, output, cache read, cache write per million tokens). Unknown model: show tokens only, cost "n/a".

### 9. Data Persistence & Lifecycle
Transcript lives in browser memory only. Page reload clears everything; the page shows only traffic that arrives after it was opened.

- Messages accumulate as the agent runs
- No auto-clear; the chats grow until reload
- A "Clear" button empties all chats mid-run

### 10. Live Update Strategy
`dashboard.py` pushes events via **Server-Sent Events (SSE)**. The page opens one SSE stream to `/dashboard/events`; each request and each completed reply is sent as a JSON event, and the page adds the new messages to their chat.

### 11. Security
Never show `authorization` or `x-api-key` header values on the page (show the first few characters followed by `...`, as `proxy.py` does).

---

## Open Decisions
Where this spec is silent or ambiguous, the building agent must **stop and ask the user** before deciding, instead of silently picking an answer.

The building agent also keeps an `ASSUMPTIONS.md` file in the build folder. For every question it asked, and every other place where it had to choose something the spec did not state, it records:
- the question or ambiguity,
- the answer it got (or what it chose, and why),
- whether the spec should settle this next time.

At the end of the build it adds a short section "Questions for the next spec version" listing the open points worth addressing in the next revision of this spec. The user then writes the decisions back into this spec, so the next build does not need to ask again.

---

## Success Criteria
1. **It feels like a WhatsApp group:** Opening the dashboard, the user recognizes a group chat right away: who said what, in order, newest at the bottom.
2. **Readability at a glance:** The user instantly tells each message type and sender apart by side, color, icon, and name.
3. **Tools are visible members:** The user sees each tool join, answer (quoting the call), and leave, and can follow "Claude called tool X with input Y" → "tool X returned Z" without confusion.
4. **Drill down works:** System prompt, tool definitions, and full request details are reachable, but nothing forces the user to read them; collapse/expand is natural.
5. **Volume doesn't degrade the view:** After 50 exchanges (a 10-minute agent run), the page is still responsive and readable; no message is lost or shown twice.
6. **No guessing:** The user doesn't need a legend or tutorial to understand what they're looking at.

## Acceptance Checks
Run all three terminals from "How to Run", open the page, then in the agent:
1. Ask "read README.md": within 2 seconds your message appears on the right at the bottom of the main chat, then "Claude is typing...".
2. Claude's bubble shows the `Read` call, followed by "🔧 Read joined the group" and "Read is typing...".
3. When the next request arrives, Read's bubble shows the file content as a reply quoting the call, followed by "🔧 Read left the group".
4. Ask for a second file: `Read` joins and leaves again (it joins on every call).
5. The system prompt is in the group info panel, collapsed; expanded, it shows the full text (search for a phrase you know is in it).
6. The reply text appears as clean, assembled text, not raw SSE `data:` lines.
7. Ask the agent to read a file that does not exist: the tool's bubble is rose and the error counter goes up.
8. Each message appears once: after several requests, earlier messages are not repeated.
9. Side requests appear only in the "Side requests" chat, not in the main chat.
10. Scroll up while the agent works: the view does not jump, and a "↓ N new messages" button appears.
11. After 50 exchanges, scrolling is smooth and no message is missing.
12. The agent behaves exactly as it does without the dashboard (no broken or delayed streaming).
13. No authorization token is visible anywhere on the page.

## Out of Scope (for v1)
- Free-text search or jumping to a specific message
- Sending messages from the dashboard (no input box, read-only)
- History that survives a page reload
- Exporting or re-playing transcripts
- Agent control (pause/resume/kill/rewind)
- Analytics across runs, or comparison between two runs
- Codex / OpenAI traffic

---

## Implementation Scope

**`dashboard.py` (new file, stdlib only):**
- Pass-through reverse proxy to `--upstream`, streaming replies back byte for byte
- Records each request and reassembles each streamed reply (section 6)
- Serves the page at `/dashboard` and the SSE stream at `/dashboard/events`
- Hard-coded price table for cost

**Page (single HTML file served by `dashboard.py`):**
- SSE client for `/dashboard/events`
- WhatsApp-style layout: chat list, chat header, group info panel, chat area (section 1)
- Bubbles per sender, tool join/leave lines, reply quotes, typing indicators (sections 2, 6)
- Color and icon encoding per message type (section 3)
- Show each message once, split traffic into chats (sections 5, 7)
- Tool filter, error counter, Clear button, "new messages" button
- Stats under Claude's bubbles and totals in the group info panel

**Event schema** (rough; will be refined):
- `{ "type": "request", "id": ..., "data": { model, system, tools, messages, params, started_at } }`
- `{ "type": "reply", "id": ..., "data": { status, content (text, tool_use, thinking), usage, ttfb_ms, total_ms } }`
