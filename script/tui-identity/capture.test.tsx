/** @jsxImportSource @opentui/solid */
import { expect, mock, test } from "bun:test"
import { mkdir } from "node:fs/promises"
import { resolve } from "node:path"
import { Effect } from "effect"
import { createTestRenderer, setRendererCapabilities } from "@opentui/core/testing"
import { Global } from "@helix/core/global"
import { createEventSource, createFetch, directory, json } from "../../packages/tui/test/fixture/tui-sdk"
const base = resolve(import.meta.dir, process.env.CAPTURE_SOURCE ?? "baseline/source")
const output = resolve(import.meta.dir, "captures", process.env.CAPTURE_PHASE ?? "before")
const state = resolve(
  import.meta.dir,
  "state",
  `${process.env.CAPTURE_PHASE ?? "before"}-${process.env.CAPTURE_SCENARIO ?? "home"}-${process.env.CAPTURE_WIDTH ?? 120}-${process.env.CAPTURE_HEIGHT ?? 40}-${process.env.CAPTURE_THEME ?? "dark"}`,
)
let seed = 1731
Math.random = () => {
  seed = (seed * 1664525 + 1013904223) >>> 0
  return seed / 4294967296
}
const sessionID = "ses_fixture_molecular"
const session = {
  id: sessionID,
  slug: "molecular-notebook",
  title: "Inspect paired RNA-seq inputs",
  projectID: "proj_test",
  directory,
  version: "1.17.18",
  time: { created: 1781625600000, updated: 1781625640000 },
  cost: 0.034,
}
const model = {
  id: "fixture-model",
  name: "Fixture Model",
  providerID: "fixture",
  api: { id: "fixture-model", url: "http://test", npm: "@ai-sdk/openai-compatible" },
  capabilities: {
    temperature: true,
    reasoning: false,
    attachment: false,
    toolcall: true,
    input: { text: true, image: false, audio: false, video: false, pdf: false },
    output: { text: true, image: false, audio: false, video: false, pdf: false },
  },
  cost: { input: 0, output: 0, cache: { read: 0, write: 0 } },
  limit: { context: 128000, input: 120000, output: 8000 },
  status: "active",
  options: {},
  headers: {},
  release_date: "2026-06-01",
}
const provider = {
  id: "fixture",
  name: "Local fixture",
  source: "config",
  env: [],
  options: {},
  models: { "fixture-model": model },
}
const messages = [
  {
    info: {
      id: "msg_01_user",
      sessionID,
      role: "user",
      agent: "build",
      model: { providerID: "fixture", modelID: "fixture-model" },
      time: { created: 1781625600000 },
    },
    parts: [
      {
        id: "prt_01_user",
        messageID: "msg_01_user",
        sessionID,
        type: "text",
        text: "Inspect the paired FASTQ files in ./data and summarize the inputs. Do not run a pipeline.",
      },
    ],
  },
  {
    info: {
      id: "msg_02_assistant",
      sessionID,
      role: "assistant",
      parentID: "msg_01_user",
      agent: "build",
      mode: "build",
      providerID: "fixture",
      modelID: "fixture-model",
      path: { cwd: directory, root: "/tmp/helix" },
      cost: 0.034,
      tokens: { input: 1600, output: 230, reasoning: 0, cache: { read: 0, write: 0 } },
      time: { created: 1781625610000, completed: 1781625640000 },
      finish: "stop",
    },
    parts: [
      {
        id: "prt_02_tool",
        messageID: "msg_02_assistant",
        sessionID,
        type: "tool",
        callID: "call_read",
        tool: "bash",
        state: {
          status: "completed",
          input: { command: "find data -name '*.fastq.gz' -maxdepth 1", description: "List paired FASTQ inputs" },
          output:
            "data/liver_01_R1.fastq.gz\ndata/liver_01_R2.fastq.gz\ndata/liver_02_R1.fastq.gz\ndata/liver_02_R2.fastq.gz",
          title: "List paired FASTQ inputs",
          metadata: {
            output:
              "data/liver_01_R1.fastq.gz\ndata/liver_01_R2.fastq.gz\ndata/liver_02_R1.fastq.gz\ndata/liver_02_R2.fastq.gz",
          },
          time: { start: 1781625610000, end: 1781625620000 },
        },
      },
      {
        id: "prt_03_text",
        messageID: "msg_02_assistant",
        sessionID,
        type: "text",
        text: "Found **2 paired samples** in `./data`:\n\n- `liver_01` — R1 and R2 present\n- `liver_02` — R1 and R2 present\n\nThe filenames form complete pairs. File contents and quality have not been checked. No pipeline was run.",
      },
    ],
  },
]
function color(c: any) {
  const v = c.toInts()
  return `rgb(${v[0]},${v[1]},${v[2]})`
}
function esc(s: string) {
  return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;")
}
function frameSVG(frame: any) {
  const cw = 9.6,
    ch = 20,
    pad = 16
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${frame.cols * cw + pad * 2}" height="${frame.rows * ch + pad * 2}" viewBox="0 0 ${frame.cols * cw + pad * 2} ${frame.rows * ch + pad * 2}"><rect width="100%" height="100%" fill="${color(frame.lines[0].spans[0].bg)}"/><g font-family="Menlo,Monaco,monospace" font-size="16" xml:space="preserve">`
  frame.lines.forEach((line: any, row: number) => {
    let x = pad
    for (const span of line.spans) {
      const w = span.width * cw
      svg += `<rect x="${x}" y="${pad + row * ch}" width="${w}" height="${ch}" fill="${color(span.bg)}"/>`
      if (span.text.trim())
        svg += `<text x="${x}" y="${pad + row * ch + 15}" fill="${color(span.fg)}"${span.attributes & 1 ? ' font-weight="bold"' : ""}>${esc(span.text)}</text>`
      x += w
    }
  })
  return svg + "</g></svg>"
}
const scenario = process.env.CAPTURE_SCENARIO ?? "home"
const width = Number(process.env.CAPTURE_WIDTH ?? 120)
const height = Number(process.env.CAPTURE_HEIGHT ?? 40)
test(`capture ${scenario} ${width}x${height}`, async () => {
  await mkdir(output, { recursive: true })
  await mkdir(state, { recursive: true })
  await Bun.write(
    `${state}/kv.json`,
    JSON.stringify({
      animations_enabled: process.env.CAPTURE_ANIMATIONS === "1",
      theme: process.env.CAPTURE_THEME_NAME ?? "helix",
      theme_mode_lock: process.env.CAPTURE_THEME ?? "dark",
      sidebar: "auto",
      home_tips: false,
      tool_details: true,
      paste_summary_enabled: process.env.CAPTURE_PASTE_SUMMARY !== "0",
    }),
  )
  const setup = await createTestRenderer({
    width: Number(process.env.CAPTURE_FROM_WIDTH ?? width),
    height: Number(process.env.CAPTURE_FROM_HEIGHT ?? height),
    useThread: false,
  })
  const capabilities = setRendererCapabilities(setup.renderer, {
    rgb: process.env.CAPTURE_COLOR !== "256" && process.env.CAPTURE_COLOR !== "16",
    ansi256: process.env.CAPTURE_COLOR !== "16",
    unicode: process.env.CAPTURE_WIDTH_METHOD === "wcwidth" ? "wcwidth" : "unicode",
    bracketed_paste: true,
  })
  const core = await import("@opentui/core")
  mock.module("@opentui/core", () => ({ ...core, createCliRenderer: async () => setup.renderer }))
  setup.renderer.waitForThemeMode = async () => (process.env.CAPTURE_THEME === "light" ? "light" : "dark")
  if (process.env.CAPTURE_THEME_NAME === "system")
    setup.renderer.getPalette = async () => ({
      palette: [
        "#0a0c10",
        "#dc2626",
        "#244d3e",
        "#9a5700",
        "#226878",
        "#7c5aa5",
        "#9fc6cf",
        "#b3babd",
        "#858c92",
        "#f87171",
        "#b9e27f",
        "#fbbf24",
        "#6f9cbc",
        "#b18ac9",
        "#a5d8df",
        "#eceeed",
      ],
      defaultForeground: "#eceeed",
      defaultBackground: "#0a0c10",
      cursorColor: "#b9e27f",
      mouseForeground: null,
      mouseBackground: null,
      tekForeground: null,
      tekBackground: null,
      highlightBackground: "#244d3e",
      highlightForeground: "#eceeed",
    })
  const events = createEventSource()
  const calls: string[] = []
  const fixture = createFetch((url) => {
    calls.push(url.pathname)
    if (url.pathname === "/session") return json([session])
    if (url.pathname === `/session/${sessionID}`) return json(session)
    if (url.pathname === `/session/${sessionID}/message`) return json(messages)
    if (url.pathname === `/session/${sessionID}/todo`)
      return json([
        { id: "todo_1", content: "Inspect input filenames", status: "completed", priority: "medium" },
        { id: "todo_2", content: "Check read quality after approval", status: "pending", priority: "medium" },
      ])
    if (url.pathname === `/session/${sessionID}/diff`) return json([])
    if (url.pathname === "/config/providers")
      return json({ providers: [provider], default: { fixture: "fixture-model" } })
    if (url.pathname === "/provider")
      return json({ all: [provider], default: { fixture: "fixture-model" }, connected: ["fixture"] })
    if (url.pathname === "/agent")
      return json([
        {
          name: "build",
          mode: "primary",
          native: true,
          permission: [],
          options: {},
          model: { providerID: "fixture", modelID: "fixture-model" },
        },
      ])
    if (url.pathname === "/lsp")
      return json([{ id: "typescript", name: "TypeScript", root: directory, status: "connected" }])
    if (url.pathname === "/mcp") return json({ documentation: { status: "connected" } })
  }, events)
  let api: any
  let started!: () => void
  const ready = new Promise<void>((r) => (started = r))
  try {
    const { run } = await import(`${base}/src/app.tsx`)
    const { createTuiResolvedConfig } = await import(`${base}/test/fixture/tui-runtime.ts`)
    const { createBuiltinPlugins } = await import(`${base}/src/feature-plugins/builtins.ts`)
    const task = Effect.runPromise(
      run({
        url: "http://test",
        directory,
        config: createTuiResolvedConfig({ theme: process.env.CAPTURE_THEME_NAME ?? "helix", plugin_enabled: {} }),
        fetch: fixture.fetch,
        events: events.source,
        args: scenario === "home" ? {} : { sessionID },
        pluginHost: {
          async start(input: any) {
            api = input.api
            const hostSlots = input.runtime.setupSlots(api)
            for (const p of createBuiltinPlugins({ experimentalEventSystem: false })) {
              if (process.env.CAPTURE_OPTIONAL_PLUGINS === "0" && p.enabled === false) continue
              if (
                ["internal:notifications", "internal:plugins", "internal:which-key", "internal:diff-viewer"].includes(
                  p.id,
                )
              )
                continue
              await p.tui({ ...api, slots: { register: (slot: any) => hostSlots.register({ id: p.id, ...slot }) } })
            }
            started()
          },
          async dispose() {},
        },
      }).pipe(Effect.provide(Global.layerWith({ state, data: state, config: state }))),
    )
    await Promise.race([ready, task])
    for (let i = 0; i < 25; i++) {
      await Bun.sleep(20)
      if (setup.renderer.isDestroyed) throw new Error("renderer destroyed")
      await setup.renderOnce()
    }
    if (scenario !== "home" && process.env.CAPTURE_HOME_DIALOG !== "1") {
      api.route.navigate("session", { sessionID })
      for (let i = 0; i < 25; i++) {
        await Bun.sleep(20)
        await setup.renderOnce()
      }
    }
    if (process.env.CAPTURE_FROM_WIDTH || process.env.CAPTURE_FROM_HEIGHT) {
      setup.resize(width, height)
      for (let i = 0; i < 3; i++) await setup.renderOnce()
    }
    if (process.env.CAPTURE_INPUT) await setup.mockInput.pressKeys(Array.from(process.env.CAPTURE_INPUT))
    if (process.env.CAPTURE_PASTE) await setup.mockInput.pasteBracketedText(process.env.CAPTURE_PASTE)
    if (process.env.CAPTURE_FRAME_SERIES === "1") {
      const frames = []
      const started = performance.now()
      for (let index = 0; index < 34; index++) {
        await setup.renderOnce()
        frames.push({ elapsed: performance.now() - started, frame: setup.captureSpans() })
        await Bun.sleep(100)
      }
      await Bun.write(
        `${output}/motion-series.json`,
        JSON.stringify(frames, (_, v) => (v?.toInts ? { rgba: v.toInts(), intent: v.intent, slot: v.slot } : v)),
      )
    }
    if (process.env.CAPTURE_MOTION_SECONDS) await Bun.sleep(Number(process.env.CAPTURE_MOTION_SECONDS) * 1000)
    const emit = (type: string, properties: any) =>
      events.emit({ directory, project: "proj_test", payload: { id: `evt_${type}`, type, properties } } as any)
    if (scenario === "permission")
      emit("permission.asked", {
        id: "per_fixture",
        sessionID,
        permission: "bash",
        patterns: ["fastqc data/*.fastq.gz"],
        always: ["fastqc *"],
        metadata: { command: "fastqc data/*.fastq.gz", description: "Check read quality" },
        tool: { messageID: "msg_02_assistant", callID: "call_read" },
      })
    if (scenario === "question")
      emit("question.asked", {
        id: "q_fixture",
        sessionID,
        questions: [
          {
            question: "Which reference genome should be used?",
            header: "Reference",
            options: [
              { label: "GRCm39", description: "Current mouse reference" },
              { label: "GRCm38", description: "Match the earlier campaign" },
            ],
          },
        ],
      })
    if (scenario === "selector")
      api.ui.dialog.replace(() =>
        api.ui.DialogSelect({
          title: "Choose reference",
          current: "GRCm39",
          options: [
            { title: "GRCm39", value: "GRCm39", description: "Current mouse reference" },
            { title: "GRCm38", value: "GRCm38", description: "Match earlier campaign" },
            { title: "Custom reference", value: "custom", description: "Existing local FASTA" },
          ],
        }),
      )
    if (scenario === "confirm")
      api.ui.dialog.replace(() =>
        api.ui.DialogConfirm({
          title: "Confirm export",
          message: "Export this session to the existing output location?",
        }),
      )
    if (scenario === "prompt")
      api.ui.dialog.replace(() =>
        api.ui.DialogPrompt({
          title: "Rename session",
          value: "Inspect paired RNA-seq inputs",
          placeholder: "Session title",
        }),
      )
    if (scenario === "menu") api.keymap.dispatchCommand("command.palette.show")
    if (scenario === "theme-menu") api.keymap.dispatchCommand("theme.switch")
    if (scenario === "error")
      emit("session.error", {
        sessionID,
        error: {
          name: "UnknownError",
          data: { message: "Fixture: input directory is unavailable. Check the path and try again." },
        },
      })
    for (let i = 0; i < 5; i++) {
      await Bun.sleep(20)
      await setup.renderOnce()
    }
    let idleProbe: any
    if (process.env.CAPTURE_IDLE_PROBE) {
      const startStats = setup.getNativeStats()
      const cpu = process.cpuUsage()
      const startedAt = performance.now()
      await Bun.sleep(1200)
      idleProbe = {
        ms: performance.now() - startedAt,
        cpu: process.cpuUsage(cpu),
        before: startStats,
        after: setup.getNativeStats(),
        scheduler: setup.renderer.getSchedulerState(),
      }
    }
    if (process.env.CAPTURE_THEME_NAME) expect(api.theme.selected).toBe(process.env.CAPTURE_THEME_NAME)
    const chars = setup.captureCharFrame()
    expect(chars.trim().length).toBeGreaterThan(10)
    if (scenario === "permission") expect(chars).toContain("Allow once")
    if (scenario === "question") expect(chars).toContain("GRCm39")
    if (scenario === "menu") expect(chars).toContain("Commands")
    if (scenario === "selector") expect(chars).toContain("Choose reference")
    if (scenario === "confirm") expect(chars).toContain("Confirm export")
    if (scenario === "prompt") expect(chars).toContain("Rename session")
    if (scenario === "home") expect(chars).toContain("helix")
    if (process.env.CAPTURE_PASTE_SUMMARY === "0") {
      expect(chars).toContain("six")
      expect(chars).toContain("ctrl+p commands")
      expect(chars).toContain("MCP /status")
    }
    if (scenario === "permission" && width === 80 && !base.includes("/baseline/source"))
      expect(chars).toContain("enter confirm")
    if (scenario === "session") expect(chars).toContain("filenames")
    expect(chars).not.toContain("helix crashed")
    const frame = setup.captureSpans()
    const stem = `${output}/${scenario}-${width}x${height}-${process.env.CAPTURE_THEME ?? "dark"}`
    await Bun.write(`${stem}.txt`, chars)
    await Bun.write(
      `${stem}.json`,
      JSON.stringify(frame, (_, v) => (v?.toInts ? { rgba: v.toInts(), intent: v.intent, slot: v.slot } : v), 2),
    )
    await Bun.write(`${stem}.svg`, frameSVG(frame))
    await Bun.write(
      `${stem}.meta.json`,
      JSON.stringify(
        {
          scenario,
          width,
          height,
          base,
          calls,
          capabilities,
          terminal: { TERM: process.env.TERM, COLORTERM: process.env.COLORTERM, HELIX_ASCII: process.env.HELIX_ASCII },
          options: {
            optionalPlugins: process.env.CAPTURE_OPTIONAL_PLUGINS !== "0",
            input: process.env.CAPTURE_INPUT,
            paste: process.env.CAPTURE_PASTE,
            from: [process.env.CAPTURE_FROM_WIDTH, process.env.CAPTURE_FROM_HEIGHT],
            theme: process.env.CAPTURE_THEME_NAME,
            animations: process.env.CAPTURE_ANIMATIONS,
            motionSeconds: process.env.CAPTURE_MOTION_SECONDS,
            homeDialog: process.env.CAPTURE_HOME_DIALOG,
            frameSeries: process.env.CAPTURE_FRAME_SERIES,
          },
          idleProbe,
          nativeStats: setup.getNativeStats(),
          meaningful: chars.trim(),
        },
        null,
        2,
      ),
    )
    process.stderr.write(`Saved ${stem}.{txt,json,svg,meta.json}\n`)
    setup.renderer.destroy()
    await task
  } finally {
    if (!setup.renderer.isDestroyed) setup.renderer.destroy()
    mock.restore()
  }
}, 45000)
