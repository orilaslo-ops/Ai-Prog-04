# ASSUMPTIONS.md (build 2)

Built from `SPEC.md` at commit `d944d82`. The builder did not stop to ask (the
build was done ahead of the lab); every choice below is one the spec did not
settle, with what was chosen and why.

| # | Ambiguity | What build 2 chose | Settle in the spec? |
|---|---|---|---|
| 1 | Backend changes | None needed: `dashboard.py` is the build 1 backend (same event schema). All the WhatsApp behavior lives in the page. | No |
| 2 | Which chat is "main" | The first chat seen with tools is the main chat; any later request with a different first message is a sub-agent chat. If the page is opened while a sub-agent is running, that sub-agent becomes "main". | Yes: give a rule that tells main from sub-agent (e.g. system prompt or the `Agent` tool call). |
| 3 | "Previous request of the same chat" | The earlier request in the chat that shares the longest prefix of messages. Messages are compared ignoring `cache_control` and thinking blocks, tool calls by id. This avoids false "History was rewritten" lines when Claude Code sends a forked request (same history + one extra message). | Yes |
| 4 | Claude's reply shown twice | The reply is drawn when it arrives; when the next request resends it as history it is skipped (matched by text and tool-call ids). | No |
| 5 | Assistant messages seen only in history (page opened mid-run) | Drawn as Claude bubbles with "from history" instead of stats; their tool calls join the group normally. | Maybe |
| 6 | Tool result whose call was never seen | Shown from "🔧 Tool" with the quote "(call not seen)". | No |
| 7 | Order when Claude calls several tools at once | Claude's bubble, then one "joined" line per tool; then for each result in order: the tool's bubble and its "left" line. "X is typing..." is shown for every tool still in the group. | Maybe |
| 8 | User message that has tool results and text | Tool bubbles first, then your bubble on the right with the text. A message whose only text is `<system-reminder>` is still shown, dimmed, so nothing is lost. | Maybe |
| 9 | Chat list order | Main chat first, then sub-agents in the order they appeared, "Side requests" last (not re-sorted by activity, so rows do not jump while you click). | Maybe |
| 10 | Tool filter "Only tool X" | Shows Claude bubbles that call X (with all their content), X's bubbles and X's join/leave lines. Your messages are hidden. Per chat; switching chats keeps each chat's filter. | Maybe |
| 11 | Error counter | Per chat: tool results with `is_error`, HTTP ≥ 400 and `error` SSE events. Clicking clears the filter and cycles through the errors. | OK as is |
| 12 | Unread counter / "N new messages" | Count bubbles only (not join/leave lines). | No |
| 13 | Request details (ⓘ) | A modal with parameters, masked headers, system, tools, messages and the reassembled reply. Esc or clicking outside closes it. | No |
| 14 | Group name and members for a sub-agent chat | Group name = first message cut to 40 characters; members "You, Claude, ...", although "You" there is really Claude Code. | Yes |
| 15 | Long text | Clamped at ~14 lines / 1800 characters with "Show all (N lines)". | OK as is |
| 16 | Side request layout | One compact dimmed card per request: method + path + model, the last user text, and a one-line answer. | OK as is |

## Questions for the next spec version
1. How should the dashboard tell the main chat from a sub-agent chat when the page is opened mid-run?
2. Claude Code sends forked requests (same history plus one extra message, e.g. prompt suggestions) that also carry tools: should those count as side requests?
3. In a sub-agent chat, who is "You"? Should the sub-agent's prompt be shown as coming from Claude (the main agent)?
4. Should the chat list be sorted by last activity like WhatsApp, or stay fixed?
5. Should the tool filter keep your messages visible for context?
