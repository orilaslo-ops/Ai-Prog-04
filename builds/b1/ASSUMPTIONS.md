# ASSUMPTIONS.md (build 1)

Built from `SPEC.md` at commit `79bd482`. The builder did not stop to ask (the
build was done ahead of the lab); every choice below is one the spec did not
settle, with what was chosen and why.

| # | Ambiguity | What build 1 chose | Settle in the spec? |
|---|---|---|---|
| 1 | Where the build lives | `builds/b1/` in the repo, so it can be run in the lab right away. `proxy.py` stays untouched at the repo root. | Yes: say if builds are committed or kept out of the repo. |
| 2 | "Single self-contained HTML file" | `dashboard.html` next to `dashboard.py` (inline CSS/JS, no CDN), read on each page load, so it can be edited without restarting the server. | Yes: separate file or embedded string in `dashboard.py`? |
| 3 | What counts as a "side request" | Anything that is not `POST /v1/messages` with a non-empty `tools` list (so `count_tokens`, `HEAD`/`GET`, and small-model calls without tools such as title generation). | Yes: give the rule. |
| 4 | "Previous request of the same conversation" | The most recent earlier main request whose first message is identical (ignoring `cache_control`) and that has no more messages. New messages = everything after the common prefix. If an earlier message changed, the history line says so. | Yes: this heuristic breaks after compaction. |
| 5 | Turn numbering | One number per HTTP request (including side requests), in arrival order. Numbers keep growing after "Clear". | Maybe: number main turns only? |
| 6 | Tool result shown in two places | The result appears under its tool call in the earlier card (where the call was made) and also as a "new message" in the next request's card. | Yes: pick one or both. |
| 7 | Tool filter matches | A turn matches "Only turns using X" when its reply calls tool X. | Maybe |
| 8 | Error counter | Counts distinct errors: each `tool_result` with `is_error: true`, plus each reply with HTTP status ≥ 400 or an `error` SSE event. The button cycles through them. | OK as is |
| 9 | Prices | Hard-coded table in `dashboard.py` (input, output, cache read, cache write 5-minute), matched by model-name prefix. Prices from the Anthropic pricing table as of 2026-10; cache-write price = 1.25 × input. | Yes: put the table in the spec. |
| 10 | Thinking text | Current models return thinking blocks with empty text by default, so the card shows "Thinking (hidden by the API)". | No |
| 11 | Request parameters and HTTP headers | Shown collapsed at the bottom of the request part (headers with `authorization` / `x-api-key` / `cookie` cut to 12 characters + `...`). | Maybe |
| 12 | Long text | Clamped at ~14 lines / 1800 characters with a "Show all (N lines)" button. The full text is always in the page. | OK as is |
| 13 | Python version | Python 3.8+ (WSL Ubuntu 20.04 ships 3.8). | Yes: state the minimum version. |
| 14 | Side request details | The request part of a side card is one collapsed line showing the last user text; the reply is shown small. | OK as is |

## Questions for the next spec version
1. How is "the same conversation" detected, especially after compaction or when sub-agents run in parallel?
2. Should tool results be shown only under their tool call, only in the next request, or both?
3. Should side requests get their own numbering, or no number at all?
4. Should the price table live in the spec?
5. Should there be a way to keep history across a page reload (it is out of scope now, but it hurts when the page is opened late)?
