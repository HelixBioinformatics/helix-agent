/** @jsxImportSource @opentui/solid */
import { expect, mock, test } from "bun:test"
import { mkdir } from "node:fs/promises"
import { resolve } from "node:path"
import { Effect } from "effect"
import { createTestRenderer } from "@opentui/core/testing"
import { Global } from "@helix/core/global"
import { createEventSource, createFetch, directory, json } from "../../packages/tui/test/fixture/tui-sdk"
const root = resolve(import.meta.dir, "../..")
const workspace = resolve(root, "tmp/tui-identity")
const base = resolve(root, process.env.VERIFY_SOURCE ?? "tmp/tui-identity/baseline/source")
const output = resolve(workspace, "verification", process.env.VERIFY_PHASE ?? "before")
const state = resolve(
  workspace,
  "state",
  `${process.env.VERIFY_PHASE ?? "before"}-${process.env.VERIFY_FLOW ?? "home"}-${process.env.VERIFY_WIDTH ?? 120}-${process.env.VERIFY_HEIGHT ?? 40}-dark`,
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
const flow = process.env.VERIFY_FLOW ?? "permission-once"
const width = Number(process.env.VERIFY_WIDTH ?? 120)
const height = Number(process.env.VERIFY_HEIGHT ?? 40)
test(`verify ${flow} ${width}x${height}`, async () => {
  await mkdir(output, { recursive: true })
  await mkdir(state, { recursive: true })
  await Bun.write(
    `${state}/kv.json`,
    JSON.stringify({
      animations_enabled: false,
      theme: "helix",
      theme_mode_lock: "dark",
      sidebar: "auto",
      home_tips: false,
      tool_details: true,
    }),
  )
  const setup = await createTestRenderer({ width, height, useThread: false, kittyKeyboard: true })
  const core = await import("@opentui/core")
  mock.module("@opentui/core", () => ({ ...core, createCliRenderer: async () => setup.renderer }))
  setup.renderer.waitForThemeMode = async () => "dark"
  const events = createEventSource()
  const effects: any[] = []
  const callbacks: any[] = []
  const observations: any[] = []
  const fixture = createFetch((url) => {
    if (url.pathname === "/session") return json([session])
    if (url.pathname === `/session/${sessionID}`) return json(session)
    if (url.pathname === `/session/${sessionID}/message`) return json(messages)
    if (url.pathname === `/session/${sessionID}/todo`) return json([])
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
  }, events)
  const fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = input instanceof Request ? input : new Request(input, init)
    if (request.method !== "GET") {
      const text = await request.clone().text()
      const url = new URL(request.url)
      effects.push({
        method: request.method,
        path: url.pathname,
        query: [...url.searchParams.entries()].sort(),
        body: text ? JSON.parse(text) : null,
      })
      if (url.pathname.includes("/message")) return json(messages[1])
      return json(true)
    }
    return fixture.fetch(request)
  }) as typeof globalThis.fetch
  let api: any
  let started!: () => void
  const ready = new Promise<void>((r) => (started = r))
  let task: Promise<unknown> | undefined
  async function settle(n = 6) {
    for (let i = 0; i < n; i++) {
      await Bun.sleep(15)
      if (setup.renderer.isDestroyed) throw new Error("renderer destroyed")
      await setup.renderOnce()
    }
  }
  function emit(type: string, properties: any) {
    events.emit({ directory, project: "proj_test", payload: { id: `evt_${type}`, type, properties } } as any)
  }
  function record(label: string) {
    observations.push({ label, frame: setup.captureCharFrame() })
  }
  async function key(name: string) {
    setup.mockInput.pressKey(name)
    await settle(2)
  }
  const result: any = { flow, width, height, source: base, effects, callbacks, observations, passed: false }
  try {
    if (flow === "copy-selection") {
      const clipboard = await import(`${base}/src/clipboard.ts`)
      mock.module(`${base}/src/clipboard.ts`, () => ({
        ...clipboard,
        read: async () => undefined,
        write: async (text: string) => {
          callbacks.push({ clipboard: text })
          return "copied"
        },
      }))
    }
    const { run } = await import(`${base}/src/app.tsx`)
    const { createTuiResolvedConfig } = await import(`${base}/test/fixture/tui-runtime.ts`)
    const { createBuiltinPlugins } = await import(`${base}/src/feature-plugins/builtins.ts`)
    task = Effect.runPromise(
      run({
        url: "http://test",
        directory,
        config: createTuiResolvedConfig({ theme: "helix", plugin_enabled: {} }),
        fetch,
        events: events.source,
        args: { sessionID },
        pluginHost: {
          async start(input: any) {
            api = input.api
            const hostSlots = input.runtime.setupSlots(api)
            for (const p of createBuiltinPlugins({ experimentalEventSystem: false })) {
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
    await settle(20)
    api.route.navigate("session", { sessionID })
    await settle(20)
    if (flow.startsWith("permission-")) {
      emit("permission.asked", {
        id: "per_fixture",
        sessionID,
        permission: "bash",
        patterns: ["find data"],
        always: ["find *"],
        metadata: { command: "find data" },
        tool: { messageID: "msg_02_assistant", callID: "call_read" },
      })
      await settle()
      record("before-action")
      expect(setup.captureCharFrame()).toContain("Allow once")
      if (flow === "permission-once") await key("RETURN")
      if (flow === "permission-always") {
        await key("ARROW_RIGHT")
        await key("RETURN")
        record("always-confirm")
        expect(effects.length).toBe(0)
        await key("RETURN")
      }
      if (flow === "permission-reject") await key("ESCAPE")
      if (flow === "permission-mouse") {
        const rows = setup.captureCharFrame().split("\n")
        const row = rows.findIndex((row) => row.includes("Allow once"))
        const col = rows[row].indexOf("Allow once")
        await setup.mockMouse.moveTo(col + 2, row)
        await setup.mockMouse.click(col + 2, row)
        await settle()
      }
      await settle()
      expect(effects.length).toBe(1)
      expect(effects[0].body.reply).toBe(
        flow === "permission-always" ? "always" : flow === "permission-reject" ? "reject" : "once",
      )
    } else if (flow.startsWith("question-")) {
      emit("question.asked", {
        id: "q_fixture",
        sessionID,
        questions: [
          {
            question: "Which reference genome?",
            header: "Reference",
            options: [
              { label: "GRCm39", description: "Current mouse reference" },
              { label: "GRCm38", description: "Earlier campaign" },
            ],
          },
        ],
      })
      await settle()
      record("before-action")
      expect(setup.captureCharFrame()).toContain("GRCm39")
      if (flow === "question-select") {
        await key("ARROW_DOWN")
        await key("RETURN")
      }
      if (flow === "question-custom") {
        await key("3")
        await setup.mockInput.pasteBracketedText("ref_α_日本語")
        await settle()
        record("custom-edit")
        await key("RETURN")
      }
      if (flow === "question-reject") await key("ESCAPE")
      await settle()
      expect(effects.length).toBe(1)
      if (flow !== "question-reject")
        expect(effects[0].body.answers).toEqual([[flow === "question-custom" ? "ref_α_日本語" : "GRCm38"]])
    } else if (flow === "dialog-select" || flow === "dialog-mouse") {
      api.ui.dialog.replace(() =>
        api.ui.DialogSelect({
          title: "Choose reference",
          current: "GRCm39",
          options: [
            { title: "GRCm39", value: "GRCm39", description: "Current reference" },
            { title: "GRCm38", value: "GRCm38", description: "Earlier campaign" },
          ],
          onSelect: (option: any) => callbacks.push({ selected: option.value }),
        }),
      )
      await settle()
      record("before-action")
      if (flow === "dialog-select") {
        await key("ARROW_DOWN")
        await key("RETURN")
      } else {
        const rows = setup.captureCharFrame().split("\n")
        const row = rows.findIndex((row) => row.includes("GRCm38"))
        const col = rows[row].indexOf("GRCm38")
        await setup.mockMouse.moveTo(col + 2, row)
        await setup.mockMouse.click(col + 2, row)
        await settle()
      }
      expect(callbacks).toEqual([{ selected: "GRCm38" }])
      expect(effects).toEqual([])
    } else if (flow === "dialog-prompt") {
      api.ui.dialog.replace(() =>
        api.ui.DialogPrompt({
          title: "Rename session",
          value: "RNA-seq α",
          onConfirm: (value: string) => callbacks.push({ value }),
        }),
      )
      await settle()
      record("before-action")
      await key("RETURN")
      expect(callbacks).toEqual([{ value: "RNA-seq α" }])
      expect(effects).toEqual([])
    } else if (flow.startsWith("prompt-")) {
      process.stderr.write(`PROMPT ${flow}: mounted\n`)
      const editor = setup.renderer.currentFocusedEditor as any
      expect(editor).toBeDefined()
      const text =
        flow === "prompt-ime-flush"
          ? "Inspect 한글"
          : flow === "prompt-paste"
            ? "Inspect α 日本語 é 🧬 ./data"
            : "Inspect α 日本語 é 🧬 ./data"
      if (flow === "prompt-ime-flush") {
        await setup.mockInput.pressKeys(Array.from("Inspect 한"))
        await settle()
        record("before-delayed-flush")
        setup.mockInput.pressEnter()
        setup.mockInput.pressEnter()
        await new Promise<void>((resolve) =>
          setTimeout(() => {
            editor.insertText("글")
            callbacks.push({ lateFlush: "글" })
            resolve()
          }, 0),
        )
        await settle()
        record("after-delayed-flush")
        expect(effects.length).toBe(1)
        expect(effects[0].body.parts.some((p: any) => p.type === "text" && p.text === text)).toBe(true)
        expect(editor.plainText).toBe("")
      } else {
        process.stderr.write(`PROMPT ${flow}: input-start\n`)
        if (flow === "prompt-paste") await setup.mockInput.pasteBracketedText(text)
        else await setup.mockInput.pressKeys(Array.from(text))
        process.stderr.write(`PROMPT ${flow}: input-sent\n`)
        await settle()
        record("typed-input")
        expect(editor.plainText).toBe(text)
        process.stderr.write(`PROMPT ${flow}: submit-start\n`)
        await key("RETURN")
        await settle()
        expect(effects.length).toBe(1)
        expect(effects[0].body.parts.some((p: any) => p.type === "text" && p.text === text)).toBe(true)
        expect(editor.plainText).toBe("")
      }
    } else if (flow === "copy-selection") {
      record("before-selection")
      const rows = setup.captureCharFrame().split("\n")
      const row = rows.findIndex((line) => line.includes("liver_01"))
      expect(row).toBeGreaterThanOrEqual(0)
      const col = rows[row].indexOf("liver_01")
      await setup.mockMouse.drag(col, row, col + "liver_01".length, row)
      await settle()
      expect(callbacks).toEqual([{ clipboard: "liver_01" }])
      expect(effects).toEqual([])
      expect(setup.renderer.getSelection()).toBeNull()
    } else if (flow === "interrupt") {
      emit("session.status", { sessionID, status: { type: "busy" } })
      await settle()
      record("busy")
      await key("ESCAPE")
      expect(effects.length).toBe(0)
      await key("ESCAPE")
      expect(effects.length).toBe(1)
      expect(effects[0].path).toContain("/abort")
    } else throw new Error(`Unknown flow ${flow}`)
    record("after-action")
    result.passed = true
  } catch (error) {
    result.error = String(error)
    record("failure")
    throw error
  } finally {
    await Bun.write(`${output}/${flow}-${width}x${height}.json`, JSON.stringify(result, null, 2))
    if (!setup.renderer.isDestroyed) setup.renderer.destroy()
    if (task) await task
    mock.restore()
  }
}, 60000)
