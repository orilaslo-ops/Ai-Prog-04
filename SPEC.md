# Agent Traffic Dashboard

## Overview
A live, read-only browser dashboard that displays messages flowing between an agent and Claude API in real time. As the agent works, the user watches the full back-and-forth: their prompts, Claude's responses, tool calls, and tool results, formatted to be scannable at a glance.

## Design Constraints
**Readability is the primary goal.** The dashboard is useless if the user cannot distinguish message types in a crowded transcript as the conversation grows. Every UI choice must serve legibility.

## Core Requirement
Proxy captures and streams agent-model traffic. Dashboard shows every request sent and every reply received, **newest first**.

**Request card displays:**
- System instructions (in full, collapsible if long)
- Tool definitions (available to the model)
- Conversation so far (all prior messages)
- New message being sent to the model

**Reply card displays:**
- Model's text response
- Tool calls requested
- Each tool call shown beside its result (when the result arrives in the next request)

**Global features:**
- Page updates live as messages arrive
- Long text collapsible for readability
- JSON formatted legibly (indented, syntax highlighting)
- Parts of a request clearly separated
- Statistics welcome (tokens, cost, latency, tool usage) but secondary to message content

**Optional enhancements (if they aid reading):**
- What changed since the previous request
- Filter by tool name
- Errors highlighted distinctly

---

## Design Decisions

### 1. **Request Card Layout**
Each request card shows: system instructions → tool definitions → conversation history → new message.

**Collapse strategy:**
- **System instructions:** Collapsible by default. Show heading "System Prompt" + line count. User clicks to expand.
- **Tool definitions:** Collapsible by default. Show heading "Tools Available: N" with tool names as a comma-separated list. User clicks to see full schemas.
- **Conversation history:** Show last 3 messages inline; older messages collapsed under "Earlier messages (N)". User clicks to expand all.
- **New message:** Always visible (it's what's being sent now).

Result: Request cards are ~200px tall by default, full transcript legible without constant scrolling.

### 2. **Tool Call ↔ Result Correlation**
Tool calls appear in the reply card; results come in the next request. They are nested: each tool call shows its result below it when available.

**Format:**
```
Tool Call: fetch_url
  Input: { url: "..." }
  Result (from next request): { status: 200, body: "..." }
```

**States:**
- Tool call with result: shown together
- Tool call still pending (no result yet): shown with "⏳ Result pending" status
- Tool call that errored: result highlighted in red with error message prominent

### 3. **Readability of Long Content**
System instructions, tool definitions, results, and conversation history are formatted for skimmability.

- **JSON:** Syntax highlighted, indented, monospace font
- **Long text (>200 chars):** Shown in a <pre> or code block, monospace
- **Truncation:** Never truncate; show full content but rely on collapse for viewport control
- **Whitespace:** Generous padding between sections and cards

### 4. **Included Features**
- **Tool filter:** Dropdown at the top. "Show all tools" (default) or filter to "Only requests using X". Updates the view in real time.
- **Error highlighting:** Tool results with status ≠ success are shown with a red left border and error icon. Errors bubble to the top of the viewport.
- **Stats:** Per-request card footer showing: input tokens | output tokens | latency | cost (if available). Muted gray, secondary to the content.

*Not included:* "What changed since last request" diff (adds noise without much value for a dev reading in real time).

### 5. **Data Persistence & Lifecycle**
Transcript lives in memory only. No localStorage, no disk. Page reload clears everything.

**Lifecycle:**
- Messages accumulate as the agent runs
- No auto-clear; transcript grows until reload
- User can click "Clear" to manually reset if they want to start fresh mid-run

### 6. **Live Update Strategy**
Proxy pushes new messages via **Server-Sent Events (SSE)** to the dashboard. One-way, simple, good enough for ~100 messages.

**Connection:** Dashboard opens a single SSE stream to `/api/events`; new request/reply messages are streamed as JSON events and appended to the transcript.

---

## Success Criteria
1. **Readability at a glance:** Opening the dashboard, the user instantly recognizes a request card vs. a reply card. Newest is on top.
2. **Drill down works:** A request card shows all its parts (system, tools, history, message) but doesn't force the user to read them all; collapse/expand is natural.
3. **Tool calls + results are paired:** The user can follow "I called tool X with input Y" → "tool X returned Z" without confusion.
4. **Volume doesn't degrade the view:** After 50 messages (a 10-minute agent run), the page is still responsive and readable; no content is lost.
5. **No guessing:** The user doesn't need a legend or tutorial to understand what they're looking at.

## Out of Scope (for v1)
- Search, filtering, or jumping to a specific message
- Exporting or re-playing transcripts
- Agent control (pause/resume/kill/rewind)
- Multi-request metrics or analytics (e.g., "tools called per request")
- Comparison between two runs

---

## Implementation Scope

**Dashboard (browser):**
- Single HTML/CSS/JS page (or React SPA if existing infrastructure exists)
- ESS client to listen for events on `/api/events`
- Request and Reply card components
- Tool filter dropdown
- Request/reply rendering with collapsible sections
- Error highlighting for failed tool calls
- Stats footer per request

**Proxy integration:**
- Intercept every request sent to Claude API (messages.create call)
- Intercept every response
- Format as JSON events and push to SSE stream at `/api/events`
- Event format: `{ type: "request", data: { ... } }` or `{ type: "reply", data: { ... } }`

**Event schema** (rough; will be refined):
- **Request:** system, tools, messages (conversation history), new message, model params
- **Reply:** content (text + tool calls), usage (tokens), latency
