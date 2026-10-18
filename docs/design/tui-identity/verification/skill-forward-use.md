# Helix TUI implementation brief — planning only

Use **Cuaderno molecular**: one readable text origin, consistent separation between turns, and small stable labels. Compare a single Bancada instrumental variant with identical data before choosing; do not add a new mode or setting. The distinctive element is the complementary strand beside the established helix. Session identity must also survive removal of that mark and all color.

## Evidence and boundaries

Inspected the installed `helix-tui-art-direction` skill and its three references; the supporting `frontend-design` and `opentui` entries; `docs/tui-identity-plan.md`; the decision block in `docs/tui.md`; landing README/styles/index/glyph field; and current home/session/permission/logo code. OpenTUI remains catalog-pinned to **0.4.3**. The worktree has preexisting untracked files, including `src/ui/identity.tsx`; review their provenance and callers before reuse. Existing comments in `ui/page.ts` describe numbered/timed margins; do not introduce those values for appearance.

This brief does not authorize product edits. Freeze tools, prompts, Nextflow/nf-core, SDK/events, persistence, permissions/defaults, keyboard/mouse behavior, plugins, input/IME, and thesis evidence. Retain English UI and the published `●`/`◦` mark. `docs/tui.md` is a historical proposal: exclude its new signing key, inert Enter, removal of Allow always, and amendments persistence.

## Visual system

- Dark: charcoal `#0a0c10`, sparse secondary surface `#11141a`, primary text `#eceeed`, secondary `#b3babd`, muted `#858c92`, signal `#b9e27f`. Retain separate semantic warning/error/selection roles.
- Light: independently resolve tokens; use forest `#244d3e` as the accent rather than luminous sage on white. Respect system and user-selected themes.
- Two-cell exterior inset, one common body origin across prose/tools/composer; reserve fixed cells for state indicators so pending→complete never shifts text. Use one blank row between logical blocks and occasional quiet rules. No bubble silhouette, decorative timestamps, entry numbers, fabricated progress, or scientific confidence.
- Typography is terminal-controlled: use weight, line length, and spacing, with no new font dependency. Focus needs a shape/weight cue in monochrome, not color alone.
- Normal-size home: retain the five-row helix geometry; place synthetic `ACGTCA` / `TGCAGT` in an 8-cell fixed region. The pair is positionwise complementary, not a run sequence or reverse-complement result. Prototype one brief reveal followed by quiet; cancel decorative scheduling when disabled/unmounted and pause while typing or handling permissions/questions. Never insert it into transcript, copy, storage, or model input.

Reference applications: Gemini informs measured compact logo budgets; Codex stable activity/interruption placement; Pi compact existing metadata; Lazygit one focus rule; K9s a bounded brand region. These are recorded design hypotheses, not claims that we ran those products. Seqera's effect remains user-observed inspiration; Helix's synthetic landing glyphs are the local precedent.

## Surface implementation contracts

| Surface / existing source | Presentation change | Invariant / evidence |
|---|---|---|
| Home, `routes/home.tsx`: Logo, current three paragraphs, Prompt, plugin slots | Reduce empty spacers first; measured logo/strand region; wrap the existing copy; fit composer to available cells | Keep bind/ref, `--prompt` readiness gates and exactly-once submit. Keep slot names/order/modes and destination provider. Compare dispatched submit data and slot fixtures. |
| Session, `routes/session/index.tsx`: actual messages/parts/status | Align UserMessage, AssistantMessage, tool labels and footers; stable state positions; restrained small identity within existing chrome | Preserve order, tool lifecycle, expand/error actions, scroll behavior, undo/redo/export/compaction, callbacks and payloads. Existing auto sidebar threshold remains >120 and width 42; existing manual overlay remains accessible at narrow widths. |
| Prompt, `component/prompt/index.tsx`: current input/model/mode/status | Match session text origin and tidy semantic emphasis | Preserve input, history, attachments, IME, autocomplete, interrupted/retry controls and keymap. Review both existing activity renderers before changing their appearance; retain activity timing/semantics. |
| Permission, `routes/session/permission.tsx`: header/body/options | Use same grid, warning role and clear selected option, reduced padding at short heights, stable action area | Keep ordered Allow once / Allow always / Reject, default once, existing left/right/h/l, Enter and Escape, hover/click, fullscreen command, Always confirmation and subagent reject-message flow. Compare exact `permission.reply` object including requestID/directory/workspace/message. |

Keep all meaningful permission text and choices, even in a small terminal. Treat long titles/paths/diffs as overflow content with full access through current fullscreen/scroll infrastructure; do not silently clip sensitive command details. If current components cannot make all bodies reachable, resolve the layout with existing render primitives and prove unchanged input routing before claiming completion.

## Usable 60×20 target

Reserve columns 1–2 and 59–60 as margins; usable content is 56 cells. These budgets are for bundled fixtures, not a claim that arbitrary plugin output fits. Preserve plugin slots and test realistic replacements separately.

| Screen | Allocation across the 20 terminal rows |
|---|---|
| Home | 5 logo rows, 1 gap, 5 wrapped existing-copy rows, 1 gap, 5 composer/status rows, 1 flexible row, 2 footer/plugin rows. No synthetic strand at this width. Reflow preserves the existing copy; shorter height first removes gaps and ornament. |
| Active session | 14 rows existing scrollable transcript, 1 separator/gap, 5 composer/status rows. Small identity shares existing composer chrome; no newly mandatory header. Latest content remains visible and history stays reachable through existing scroll. Auto sidebar stays absent; manual overlay behavior is retained. |
| Permission shown | 4 transcript/context rows, 1 gap, 15-row existing permission area. Inside permission: 3 header/wrapped-title rows, 6 bounded body rows, 1 separator, 1 action row, 2 hint rows, 2 spacing rows. The three action labels fit within 56 cells with selection marking. Dynamic key hints wrap; reclaim spacing before body. Fullscreen uses the existing toggle. No decoration or underlying composer competes for focus. |

Permission appearance at 56 usable cells (illustrative fixture only):

```text
△ Permission required
  Edit /project/data/samples.csv

  [actual body/diff, 6-row viewport]

────────────────────────────────────────────────────────
[Allow once]   Allow always   Reject
⇆ select    enter confirm
<configured shortcut> fullscreen
```

Square brackets represent a visible selection treatment, not a new control or key. Unknown long key labels/title wrapping require measured rendering, not hardcoded assumptions. When height pressure differs from the fixture, preserve the action region, then meaningful body access; erase ornament/gaps first.

## Verification and delivery gate

Capture baseline and proposed real-terminal output plus `testRender`/`captureCharFrame()` frames from identical fixtures at 60×20, 80×24, 120×40, 160×48. Resize narrow→wide→narrow. Cover home with `--prompt`, long paths, pending/running/completed/failed tools, normal/Always/reject-message permission stages, Unicode/wide/combining characters, IME/paste, autocomplete, selection/copy, subagents and plugin replacements. Use existing SDK/event fixtures to compare action and payload equality, including default Enter and hover-then-click; character snapshots alone do not establish it.

Inspect dark/light/system/user themes, actual supported color fallbacks, monochrome and logo-free active-session crops. Keep `●`/`◦` normal-path constants; any ASCII rendition is a capability-specific fallback, not a brand replacement. Explicitly document unsupported capabilities. With animation off, verify no decorative timers remain, mount/unmount cleanup, and baseline-relative idle render/wakeup cost.

Run `bun run --cwd packages/tui typecheck` and `bun run --cwd packages/tui test`, plus repository-relevant format/lint checks; root `bun test` is explicitly disallowed. Inspect the final diff for frozen paths/contracts and dependency changes. Deliver the visual rules, bounded diff, real before/after captures with environment/state recorded, equivalence evidence, command results and unverified limits.

No product edits, tests, terminal captures, external requests, or implementation validation were performed for this planning brief. The 60×20 row budget and capability handling remain hypotheses to verify in the current renderer.
