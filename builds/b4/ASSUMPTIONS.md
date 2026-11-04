# ASSUMPTIONS.md (build 4)

Built from `SPEC.md` at commit `8aa34b1`. The builder did not stop to ask (Ori asked for a fast build);
every choice below is one the spec did not settle, with what was chosen and why.

| # | Ambiguity | What build 4 chose | Settle in the spec? |
|---|---|---|---|
| 1 | `TaskCreate` has no id in its input | The item gets the next number in the chat (1, 2, 3 …); when the result says "Task #N", that N replaces it. `TaskUpdate` matches `taskId` first, then `subject`. Status `deleted` removes the item. `TodoWrite` still replaces the whole list. | Maybe |
| 2 | Mixing `TodoWrite` and `TaskCreate` in one chat | The last `TodoWrite` replaces the list; `TaskCreate` adds to whatever list is pinned. | No |
| 3 | Where the poll's answer comes from | Claude Code's result text has `"<question>"="<answer>"` pairs; the answer of each question is taken from its pair, and an option is chosen when its label appears in that answer. With one question and no pair, the whole result text is searched. | No |
| 4 | Poll checkbox for `multiSelect` | ☑ before every option of a multi-select question, ☐ for single choice; chosen options get ✅. | No |
| 5 | Reaction placement | A small pill on the bottom-right corner of the call box inside Claude's bubble. A later answer for the same call replaces it. | No |
| 6 | Forwarded label when the sub-agent chat exists but its first message differs from the `prompt` (system reminders) | Match on the exact prompt or the prompt with system reminders stripped. | No |
| 7 | "Started by Main agent" line when the sub-agent's first request arrives before the `Agent` call | Added as soon as the call is seen, at the top of the sub-agent chat. | No |
| 8 | Media list: which card is "the last card" | The latest call box (Write) or the latest answer bubble (Read, Edit, MultiEdit) for that path. Paths are compared as written by Claude (no normalising). | No |
| 9 | What the starred list shows as "first line" | The first text block of the bubble, else the file card name, tool name or error head; cut to 70 characters. Clicking ⭐ again unstars. | No |
| 10 | Dark mode scope | All panels (chat list, header, info panel, modal) go dark, not only the chat area; colors not in the dark table (tags, turn pill, JSON colors) were picked to match. | Maybe: list panel colors. |
| 11 | Turn 1 divider | Shown from the start as "Turn 1", then filled with the summary like the others. | No |

## Questions for the next spec version
1. Should the pinned plan keep separate `TodoWrite` and `TaskCreate` lists, or always one list?
2. Should stars and the theme be the only things kept across reloads, or stars too?
3. Should the dark table also give colors for the side panels, tags and turn dividers?
