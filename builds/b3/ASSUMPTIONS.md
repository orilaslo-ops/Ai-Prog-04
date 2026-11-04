# ASSUMPTIONS.md (build 3)

Built from `SPEC.md` at commit `f22ef13`. The builder did not stop to ask (Ori asked for a fast build);
every choice below is one the spec did not settle, with what was chosen and why.

| # | Ambiguity | What build 3 chose | Settle in the spec? |
|---|---|---|---|
| 1 | ✓✓ gray needs "first byte arrived" live, but the event schema is "final" (request + reply only) | Added one extra SSE event `{"type": "first_byte", "id": N, "data": {"ttfb_ms": ...}}`, sent after the first chunk was written to the agent. Request and reply events are unchanged. | Yes: add `first_byte` to the schema, or say ✓✓ gray may come with the reply. |
| 2 | Which request "carries" your message (for ticks) | The request where the message is the last one. Ticks are also shown on "Main agent" bubbles in sub-agent chats. | No |
| 3 | Edit diff: Claude's call box or the tool's bubble? (section 12 says the tool's bubble, check 18 says "the Edit call shows") | The diff is in Edit's answer bubble (above its result text). Claude's call box shows "✏️ path · −N +M lines". | Yes |
| 4 | Turn 1 has no divider ("after the first one"), so where does its summary go? | Turn 1's divider is hidden until the turn ends, then appears above the first prompt with the summary. | Yes |
| 5 | Turn time | From the prompt's request start to the end of the final reply (no tool calls). Cost = sum of the turn's replies. A failed reply does not end the turn. | Maybe |
| 6 | Bash exit code "when it can be read" | `Exit code N` in the result text → that code. A non-error result with no code → "exit 0" (Claude Code reports non-zero exits as errors). Error result with no code → no tag. A failed Bash keeps the terminal look with a rose border and counts as an error. | Maybe |
| 7 | Context meter | (input + cache read + cache creation) of the last reply ÷ table value. All current Claude models = 200 000; a request with the `context-1m` beta header = 1 000 000. "–" before the first reply, "?" for an unknown model. | Maybe: list the 1M case. |
| 8 | Status line priorities | typing > waiting for <tool> > idle (60 s with no event) > waiting for you. In sub-agent chats "waiting for Main agent". Refreshed every 5 s. | No |
| 9 | Pinned plan source | Only `TodoWrite` (newer Claude Code versions use `TaskCreate`/`TaskUpdate` instead, which are not pinned). | Yes: should Task* tools also feed the pin? |
| 10 | Read card line count and preview | Lines of the result text (system reminders stripped); the `N→` line-number prefix is removed from the 3-line preview and kept in the full view. | No |
| 11 | Write card | Shown in Claude's call box (the content is in the call), marked "new file" even when the file existed (the call does not say). | Maybe |
| 12 | Fork detection | The last request of the chat had the same history + one extra non-tool-result user message, and the new request continues without it. Its bubbles, its turn divider and its reply are removed and become a "fork of <chat>" card in Side requests; its tokens move to Side requests' totals. | No |
| 13 | Sub-agent call seen after the sub-agent's first request (race: the reply event is published after the stream ends) | The chat starts as "🤖 Sub-agent (?)" and becomes "🤖 Sub-agent" when the matching `Agent` call arrives. | No |
| 14 | Chat list re-sort vs clicks | Rows open on mouse press, so a re-sort between press and release cannot lose the click. | No |
| 15 | Main agent bubble style | Left side, gray bubble, name "🤖 Main agent" (no color in the table for it). | Yes: add a color row. |

## Questions for the next spec version
1. Add the `first_byte` event to the event schema (or drop live ✓✓ gray)?
2. Edit diff: in Claude's call, in the tool's answer, or both?
3. Should turn 1 also get a divider before the first prompt?
4. Should `TaskCreate` / `TaskUpdate` (the newer todo tools) feed the pinned plan?
5. What color does "🤖 Main agent" get in sub-agent chats?
