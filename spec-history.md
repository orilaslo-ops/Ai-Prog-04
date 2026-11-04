# SPEC.md history (Lab 4)

Source: `git log -p SPEC.md` on `main`. Six commits touch the spec; builds live in `builds/b1`..`b4`.
Where a reason is given, its source is in brackets: **[commit]** = commit message, **[ASSUMPTIONS bN]** =
`builds/bN/ASSUMPTIONS.md`, **[session]** = our agent session in the project thread named.

| # | Commit | What changed in SPEC.md | Why (what came before it showed) |
|---|---|---|---|
| 1 | `0cb9fe9` (Nov 1) | First draft: live dashboard of agent↔model traffic next to the given `proxy.py`. | Pre-lab task. **[commit]** |
| 2 | `dcc5f0c` (Nov 1) | Fixed contradictions (filter vs. out of scope, errors "bubble to top" vs. newest first, "ESS" typo); `proxy.py` stays unchanged and `dashboard.py` chains in front of it; single HTML file, stdlib only; pastel color table, content blocks, streaming reassembly, side requests, diff vs. previous request, cost; 9 acceptance checks. | No build yet. A review of the draft against the lab requirements found the contradictions and that a from-scratch build would have to guess how to run, how to reassemble SSE deltas and how to color messages. **[commit]** + **[session: "Check week 4 spec and lab tips"]** |
| 3 | `79bd482` (Nov 1) | Open Decisions: the builder asks, *and* keeps `ASSUMPTIONS.md` with every choice plus "Questions for the next spec version". | The draft had the agent decide everything silently. Ori wanted it to ask and also record the questions itself. Commit gives no reason. **[session: "Check week 4 spec and lab tips"]** |
| — | build 1 `ce2c940` | `builds/b1`, built from scratch from `79bd482`. | |
| 4 | `d944d82` (Nov 4, PR #2) | Redesign as a WhatsApp group: you on the right, Claude and tools on the left; a tool joins on every call, answers by quoting the call, then leaves; oldest at top; group info panel for system prompt and tools; one chat per sub-agent plus "Side requests"; stats under Claude's bubbles. | Commit says what, not why. Build 1 was a card-per-request list; Ori wanted to follow the work as a conversation and answered 8 design questions (tool joins on every call and leaves, WhatsApp order, quote replies…). **[session: "Revise dashboard spec in new folder"]**. Build 1's open questions (same-conversation detection, where tool results go, side-request numbering) **[ASSUMPTIONS b1]** were superseded by the redesign, not answered one by one. |
| — | build 2 `bec8b0f` | `builds/b2`, from `d944d82`. | |
| 5 | `f22ef13` (Nov 4, PR #4) | Rule for main vs. sub-agent chat (first message = an `Agent`/`Task` call's prompt); forked requests go to Side requests; sub-agent prompts come from "Main agent"; main chat pinned, rest by last activity; tool filter keeps your messages dimmed; final event schema; checks 14-15. New section 12 "WhatsApp touches": ticks, pinned TodoWrite plan, file cards and Edit diffs, turn dividers, context meter, status line, Bash terminal bubbles; checks 16-21. | Build 2 made "main" whichever chat appeared first (wrong when the page opens mid-run), saw Claude Code's forked requests (same history + one message), and showed "You" as the sender of sub-agent prompts. **[commit]** + **[ASSUMPTIONS b2, #2, #3, #14, questions 1-5]**. Section 12 = 7 ideas Ori asked for ("give me original ideas") and accepted all. **[session: "Improve dashboard spec again"]** |
| — | build 3 `f4fb9ec` | `builds/b3`, from `f22ef13`. **← switch to editing (see below)** | |
| 6 | `8aa34b1` (Nov 4, PR #6) | `first_byte` SSE event added to the schema; Edit: short line in the call, full diff in the tool's answer; turn 1 gets a divider; turn time/cost defined; TaskCreate/TaskUpdate feed the plan; color row for "Main agent"; new touches: AskUserQuestion polls, ✅/❌ reactions, forwarded sub-agent answers, media/links/docs list, starred messages, dark mode with its own colors; checks 22-27. | Build 3 had to add a `first_byte` event outside the "final" schema to show live gray ✓✓; section 12 and check 18 disagreed on where the Edit diff goes; turn 1 had no divider; newer Claude Code uses TaskCreate/TaskUpdate, not TodoWrite; "Main agent" had no color. **[commit]** + **[ASSUMPTIONS b3, #1, #3, #4, #9, #15]**. The six new touches were ideas Ori picked "all" of. **[session: "Improve dashboard spec, round 3"]** |
| — | build 4 `73d943c` | `builds/b4`, from `8aa34b1`. Its 3 open questions (one plan list or two, stars across reload, dark colors for side panels) are not in the spec yet. **[ASSUMPTIONS b4]** | |

## Rebuild vs. edit

- **Build 1** was the only true from-scratch build.
- **Build 2** was half and half: the page (`dashboard.html`) was rewritten for the WhatsApp design (≈1300 of its lines differ from b1), but `dashboard.py` is b1's backend unchanged (only the docstring differs; ASSUMPTIONS b2 #1).
- **Switch point: build 3** (`f4fb9ec`, after spec commit `f22ef13`). From here the agent **edited the previous build's code** in a copied `builds/bN` folder: b3 was "built from build 2" **[session: "Build dashboard 3 from latest spec"]** and changes ≈350 of 1100 page lines; b4 changes ≈300 lines and keeps the backend. Build 2 was committed and merged (`bec8b0f`) before the switch.
- **Why:** spec rounds 3-4 were additive (answers + new section-12 touches on the same design), and Ori asked for speed ("don't run tests, I need it faster") **[sessions: builds 2 and 3]**. The cost: later builds no longer test whether the spec alone is enough to build from.

## Findings in the traffic

*Draft, pending Ori's own notes from the live runs.* Builders ran no live tests at Ori's request, so these come from what the builds had to handle **[ASSUMPTIONS b1-b4]**:
- Claude Code sends more than your turns: small-model calls without tools (titles), `count_tokens`, and **forked requests** (same history + one extra message, e.g. prompt suggestions).
- Every request resends the whole history, and `<system-reminder>` text is injected into user messages, so "what's new" must be computed by diffing against the previous request.
- Thinking blocks come back with empty text by default.
- A sub-agent's first request can arrive **before** the `Agent` call that started it (the reply event is published only when the stream ends).
- Newer Claude Code plans with `TaskCreate`/`TaskUpdate` instead of `TodoWrite`; `AskUserQuestion` answers come back as `"question"="answer"` text.
- Context size depends on a `context-1m` beta header, not only the model name.
