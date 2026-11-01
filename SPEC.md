# Agent Traffic Dashboard

## Overview
A live, read-only browser dashboard that displays messages flowing between an agent (Claude Code) and the Claude API in real time. As the agent works, the user watches the full back-and-forth: their prompts, Claude's responses, tool calls, and tool results, formatted to be scannable at a glance.

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
The dashboard shows every request sent and every reply received, **newest first**.

**Exchange card.** Each request and its reply are shown together as one card ("Turn #12"), so they never get separated in the newest-first list.

**Request part displays:**
- System instructions (in full, collapsible if long). Note: `system` is an array of blocks, not a string.
- Tool definitions (available to the model)
- Conversation so far (all prior messages)
- New message being sent to the model

**Reply part displays:**
- Model's text response
- Tool calls requested
- Each tool call shown beside its result (when the result arrives in the next request)

**Global features:**
- Page updates live as messages arrive
- Long text collapsible for readability
- JSON formatted legibly (indented, syntax highlighted)
- Parts of a request clearly separated
- Statistics welcome (tokens, cost, latency, tool usage) but secondary to message content

---

## Design Decisions

### 1. Request Layout
Each request shows: system instructions → tool definitions → conversation history → new message.

**Collapse strategy:**
- **System instructions:** Collapsed by default. Heading "System Prompt" + line count. Click to expand.
- **Tool definitions:** Collapsed by default. Heading "Tools Available: N" with tool names as a comma-separated list. Click to see full schemas.
- **Conversation history:** Shown as a diff against the previous request (see section 5): "History: same as Turn #11 + 2 new messages". Only the new messages are shown expanded; the full history is one click away.
- **New message:** Always visible (it's what's being sent now).

### 2. Tool Call ↔ Result Correlation
Tool calls appear in the reply; results come in the next request. They are matched by `tool_use.id` ↔ `tool_result.tool_use_id`, and each tool call shows its result below it when available.

**Format:**
```
🔧 Tool Call: Read
  Input: { "file_path": "..." }
  ↩ Result (from Turn #13): "..."
```

**States:**
- Tool call with result: shown together
- Tool call still pending (no result yet): shown with "⏳ Result pending"
- Tool call that errored (`is_error: true`): result highlighted in red with the error message prominent

### 3. Visual Encoding (colors)
Every message type has its own soft, pleasant color and icon, so types can be told apart without a legend. Colors are muted pastels with a stronger left border of the same hue; text stays dark and readable.

| Type | Background | Left border | Icon |
|---|---|---|---|
| User prompt (user text) | `#EAF2FB` soft blue | `#5B8DEF` | 👤 |
| Model text (assistant) | `#EAF7EE` soft green | `#4CAF7A` | 🤖 |
| Tool call (`tool_use`) | `#FFF4E5` soft peach | `#F0A35E` | 🔧 (tool name in bold) |
| Tool result (`tool_result`) | `#EEF6F7` soft teal | `#5FA8B0` | ↩ |
| Tool result with error | `#FDECEC` soft rose | `#E06C6C` | ⚠️ |
| Thinking (`thinking`) | `#F3EEFA` soft lavender | `#9B7FD1` | 💭 (collapsed) |
| System prompt / tool definitions | `#F5F5F4` warm gray | `#B0ACA6` | ⚙️ (collapsed) |
| `<system-reminder>` text inside user messages | dimmed, smaller font | none | collapsed |

Page background is an off-white (`#FAFAF8`). Whitespace between cards is generous.

### 4. Content Blocks
Messages contain arrays of content blocks. The dashboard must handle at least: `text`, `tool_use`, `tool_result`, `thinking`, and `image` (shown as a placeholder). `<system-reminder>...</system-reminder>` sections that Claude Code injects into user messages are noise for the reader: show them dimmed and collapsed (see table above).

### 5. What Changed Since the Previous Request
Every request resends the whole conversation, so the useful information is the difference. Each request card marks which messages are new compared to the previous request of the same conversation, and highlights only those. If the system prompt or tool list changed from the previous request, show a small "changed" badge on that section.

### 6. Streaming Replies
Claude Code sends `"stream": true`, so replies arrive as SSE events (`message_start`, `content_block_start`, `content_block_delta` with `text_delta` / `input_json_delta` / `thinking_delta`, `content_block_stop`, `message_delta`, `message_stop`). `dashboard.py` reassembles them into a complete reply: full text blocks and tool calls with their complete parsed JSON input. Raw `data:` lines are never shown as the reply. Non-streamed (plain JSON) replies are also supported.

### 7. Side Requests
Besides the main conversation, Claude Code sends side requests (to a small model for titles or classification, `count_tokens`, `HEAD`/`GET` checks). Every card shows the model name as a tag. Side requests are shown in a compact, dimmed form, and a "Hide side requests" toggle at the top hides them.

### 8. Included Features
- **Tool filter:** Dropdown at the top. "All" (default) or "Only turns using tool X". Updates the view in real time.
- **Error highlighting:** Tool results with `is_error: true` and HTTP errors (status ≥ 400) are shown in rose with an error icon. A counter in the header ("⚠️ 3 errors") jumps to the next error when clicked. Errors do **not** change the newest-first order.
- **Stats:** Per-card footer: input tokens | cache read tokens | cache creation tokens | output tokens | latency (time to first byte and total) | cost. Muted gray, secondary to the content. Header shows totals and tool usage counts per tool.
- **Cost:** Computed from a hard-coded per-model price table in `dashboard.py` (input, output, cache read, cache write per million tokens). Unknown model: show tokens only, cost "n/a".

### 9. Data Persistence & Lifecycle
Transcript lives in browser memory only. Page reload clears everything; the page shows only traffic that arrives after it was opened.

- Messages accumulate as the agent runs
- No auto-clear; transcript grows until reload
- A "Clear" button resets the view mid-run

### 10. Live Update Strategy
`dashboard.py` pushes events via **Server-Sent Events (SSE)**. The page opens one SSE stream to `/dashboard/events`; each request and each completed reply is sent as a JSON event and added to its exchange card.

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
1. **Readability at a glance:** Opening the dashboard, the user instantly tells each message type apart by color and icon. Newest is on top.
2. **Drill down works:** Every part of a request (system, tools, history, message) is reachable, but nothing forces the user to read it all; collapse/expand is natural.
3. **Tool calls + results are paired:** The user can follow "I called tool X with input Y" → "tool X returned Z" without confusion.
4. **Volume doesn't degrade the view:** After 50 exchanges (a 10-minute agent run), the page is still responsive and readable; no content is lost.
5. **No guessing:** The user doesn't need a legend or tutorial to understand what they're looking at.

## Acceptance Checks
Run all three terminals from "How to Run", open the page, then in the agent:
1. Ask "read README.md": within 2 seconds of the request, a new card appears at the top.
2. The `Read` tool call is shown with its result in the same place once the next request arrives.
3. The system prompt is collapsed; expanded, it shows the full text (search for a phrase you know is in it).
4. The reply text appears as clean, assembled text, not raw SSE `data:` lines.
5. Ask the agent to read a file that does not exist: the tool result is shown in rose and the error counter goes up.
6. In the second request of a conversation, only the new messages are highlighted as new.
7. After 50 exchanges, scrolling is smooth and no card is missing.
8. The agent behaves exactly as it does without the dashboard (no broken or delayed streaming).
9. No authorization token is visible anywhere on the page.

## Out of Scope (for v1)
- Free-text search or jumping to a specific message
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
- Exchange cards with request and reply parts, collapsible sections
- Color and icon encoding per message type (section 3)
- Diff against previous request (section 5)
- Tool filter, side-request toggle, error counter, Clear button
- Stats footer per card and totals in the header

**Event schema** (rough; will be refined):
- `{ "type": "request", "id": ..., "data": { model, system, tools, messages, params, started_at } }`
- `{ "type": "reply", "id": ..., "data": { status, content (text, tool_use, thinking), usage, ttfb_ms, total_ms } }`
