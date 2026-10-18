# TUI identity: baseline capture protocol

Captured 17 October 2026 against the pre-redesign source snapshot at revision
`1de7c76718b19125b3d8598f73c11f25305714b6`.

## Evidence and reproduction

The capture harness starts the actual TUI application with OpenTUI 0.4.3's native
test renderer, the actual Solid context providers and builtin visual slots, and a local SDK/event
fixture. It runs no model, shell command, Nextflow process or external service.
The displayed tool output is fixed illustrative fixture data. All captures use
the same fixture after redesign; the harness only selects the source directory.

- Harness: [`capture.test.tsx`](../../script/tui-identity/capture.test.tsx).
- Matrix runner: [`run-captures.py`](../../script/tui-identity/run-captures.py).
- Extra cases: [`run-extras.py`](../../script/tui-identity/run-extras.py).
- Rasterizer: [`render-captures.py`](../../script/tui-identity/render-captures.py).
- Frozen sources: `tmp/tui-identity/baseline/source/`; the original source files match the recorded Git revision.
- Complete generated outputs: `tmp/tui-identity/captures/`.
- Durable selection: [`tui-identity/captures/`](./tui-identity/captures/).

From the repository root, using Bun from `PATH` or `~/.bun/bin/bun`:

```sh
# Only when the frozen baseline is missing; never overwrites an existing one.
python3 script/tui-identity/run-captures.py --prepare-baseline 1de7c76718b19125b3d8598f73c11f25305714b6
python3 script/tui-identity/run-captures.py both --plugins stress
python3 script/tui-identity/run-captures.py both --scenes home,session --sizes 120x40 --themes dark --plugins default
python3 script/tui-identity/run-extras.py
python3 script/tui-identity/render-captures.py before
python3 script/tui-identity/render-captures.py after
python3 script/tui-identity/render-captures.py before-default
python3 script/tui-identity/render-captures.py after-default
python3 script/tui-identity/render-captures.py after-extras
# After the behavior comparison and package checks are complete:
python3 script/tui-identity/package-evidence.py
```

The rasterizer requires Pillow. It uses Menlo on macOS, DejaVu Sans Mono when
available elsewhere, or the regular monospace TrueType file selected through
`TUI_CAPTURE_FONT`. Font choice affects only exported evidence, not the product.
All state and generated captures remain under `tmp/tui-identity/`. The runners
reuse the portable baseline/dependency helpers from `run-verification.py`.
The packager requires the complete successful matrices, the 30-case interaction
report and saved package-check logs. It verifies the report's source hashes,
preserves 41 representative native frames in `docs/design/tui-identity`, and
exports grayscale session copies and body crops. Each body crop retains 37
native rows; the after crop omits its three identity-header rows. No cells are
scaled or recomposed. `manifest.json` records the preserved files and hashes.

The runner invokes Bun from `packages/tui`, with `--conditions=browser` and the
OpenTUI Solid preload. The browser condition selects Solid's reactive build;
without it Solid resolves the server build and the fixture does not hydrate.
The harness redirects Global state and XDG paths to disposable capture folders.

Each case produces:

- `.txt`: native `captureCharFrame()` content, preserving terminal rows.
- `.json`: native `captureSpans()` with cell widths, foreground/background RGBA and attributes.
- `.svg`: a direct drawing of those spans and backgrounds on a fixed cell grid.
- `.png`: a rasterization of the recorded spans using Menlo; this is an image of
  real rendered cell data, not a manually composed mockup or a terminal emulator
  screenshot. Font rasterization can differ from the user's terminal.
- `.meta.json`: source directory, fixture request paths, dimensions and native renderer statistics.
- `.log`: process output and assertions. `capture-results.json` records the matrix result.

## Matrix

| Surface | Fixture and existing data | Presentational change to assess | Identical action contract |
|---|---|---|---|
| Home | Existing helix mark, product subtitle, explanatory copy, empty prompt, provider/model metadata, tips and footer | Mark budget, complementary synthetic fragment, shared grid, short-terminal degradation | Prompt submit, history, attachments, plugins and keymap |
| Session | One user instruction; completed shell fixture with four filenames; assistant Markdown summary; existing mode/model/duration and token/cost metadata | User/assistant hierarchy, common origin, tool presentation, prompt and compact identity | Message selection, copy, tool expansion, prompt and interruption |
| Context | Existing session title/ID, context tokens/percent/cost, MCP/LSP status, two todos and directory | Sidebar hierarchy and alignment within the existing 42-column budget | Same data, ordering, slots and automatic visibility breakpoint |
| Permission | Existing shell permission, Allow once / Allow always / Reject | Focus, emphasis and spacing | Same option order, keys and reply payloads |
| Question | Existing reference question, two options and custom-answer entry | Header, options and focus | Same selection, custom answer, submit and reject payloads |
| Command menu | Existing command palette | Search, category hierarchy, selection gutter and panel edges | Same filtering, selection and command dispatch |
| Theme menu | Existing theme picker and theme state | Current-versus-focused indicator and list geometry | Same themes, selection, preview and persistence |
| Selector | Existing DialogSelect API with three local fixture options | Current versus focused option, text origin and compact panel | Same options and callback value |
| Confirm | Existing DialogConfirm API | Visible focus and panel hierarchy | Same default confirm, left/right movement, Enter and cancel callbacks |
| Prompt dialog | Existing DialogPrompt API and session title value | Input boundary and spacing | Same text editing and confirm/cancel callbacks |
| Error | Existing session.error event and local fixture message | Error distinction and toast readability | Same error handling, dismissal and content |

The recorded 52-case stress matrix covers 80×24, 120×40, 160×48 and 60×20 in dark mode;
all listed surfaces at 120×40 in light mode, plus home/session at 80×24 light.
This stress fixture explicitly enables the optional `which-key` builtin, which
is disabled in the default product configuration. The separate `before-default`
and `after-default` home/session captures respect every builtin `enabled: false`
flag. The stress matrix therefore also exercises optional plugin composition; it
should not be captioned as the default installation.

A separate verification harness checks interaction payloads; pictures alone do
not prove behavior equivalence.

## Observed baseline

- A 120×40 session has no compact Helix identity in its conversation region. Its
  user message, tool output and assistant text have different left edges.
- The wide session uses the familiar chat/sidebar silhouette and green-tinted
  background. The 42-column sidebar contains existing context data, so it must
  keep that budget and those data after restyling.
- The native 60×20 home buffer exhibits overlap: the three-line explanatory copy
  compresses onto the same row, and tips can collide with the footer. The new
  layout must give content and actions precedence as height decreases.
- Permission and question requests already replace the prompt region. Their
  selection and response semantics are existing behavior, not design additions.
- A completed shell fixture provides a visible command and four output rows;
  narrow session captures naturally scroll earlier rows away. No output is
  synthesized by the renderer or interpreted as a scientific result.

Native cell captures test layout and colors at the renderer boundary. They do
not independently prove physical terminal glyph coverage, external IME behavior,
clipboard integration, 16-color output negotiation, CPU idleness or scientific
correctness; those require their corresponding checks.

## Recorded validation

- Before: 52/52 native capture fixtures passed. After: 52/52 passed, with the final
  short-terminal cases refreshed after the last spacing change.
- Default builtin configuration: home/session at 120×40 before and after, 4/4.
- Extra fixtures: 19/19, including ASCII identity, declared 256/16-color
  capabilities, `wcwidth`, a supplied system palette, resize, Unicode input,
  multiline paste, movement/quiet states, six-line draft at 60×20, and idle
  measurements for before/after.
- The final six-line 60×20 draft retains all six rows, provider/model metadata,
  command shortcut, tip, keyboard helper and readable MCP footer. At 80×24 the
  permission choices and `enter confirm` hint now occupy two complete rows.
- Motion after 11 seconds lights the synthetic `TGCAGT` complement in sage. The
  same delay with a typed draft leaves both strands muted.
- With animation disabled, native frame counts stayed unchanged over the
  approximately 1.2-second idle probe in both source versions: home 33→33 and
  session 60→60. Single concurrent-process CPU samples were 26.8/27.6 ms for
  home before/after and 19.5/23.4 ms for session; they are observational samples,
  not a statistical performance benchmark.

The 256/16-color cases set the native test renderer's declared JavaScript
capabilities; native span capture retains semantic RGB values and does not prove
wire-level ANSI quantization in a physical terminal. System-theme captures use a
fixed terminal palette and assert that the selected theme remains `system`.
Unicode input sends complete code points through mock key events; it does not
certify an operating system's IME. The mock's `typeText` helper splits UTF-16
surrogates, so the harness uses `pressKeys(Array.from(text))` for this case.

The ASCII identity case applies to the introduced mark/rules. Existing tools,
MCP indicators, permission arrows and other inherited glyphs can still be
Unicode. No broad claim of an entirely ASCII product is made.
