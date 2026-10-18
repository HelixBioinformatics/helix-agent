/** @jsxImportSource @opentui/solid */
import { afterEach, expect, test } from "bun:test"
import { type BoxRenderable, CliRenderEvents, RGBA } from "@opentui/core"
import { setRendererCapabilities } from "@opentui/core/testing"
import { testRender } from "@opentui/solid"
import { createSignal } from "solid-js"
import { type GenomeClock, genomeLayout, useGenomeField } from "../../src/ui/genome-field"

type Timer = ReturnType<GenomeClock["setTimeout"]>

function manualClock() {
  let time = 0
  let nextID = 0
  const timers = new Map<Timer, { at: number; callback: () => void }>()
  const clock: GenomeClock = {
    now: () => time,
    setTimeout(callback, delay) {
      const timer = ++nextID
      timers.set(timer, { at: time + delay, callback })
      return timer
    },
    clearTimeout(timer) {
      timers.delete(timer)
    },
  }
  return {
    clock,
    pending: () => timers.size,
    advance(milliseconds: number) {
      const until = time + milliseconds
      for (let count = 0; count < 1000; count++) {
        const due = [...timers].filter(([, item]) => item.at <= until).sort((a, b) => a[1].at - b[1].at)[0]
        if (!due) {
          time = until
          return
        }
        time = due[1].at
        timers.delete(due[0])
        due[1].callback()
      }
      throw new Error("Decorative animation did not yield to the manual clock")
    },
  }
}

const colors = {
  background: RGBA.fromHex("#0a0c10"),
  textMuted: RGBA.fromHex("#b3babd"),
  primary: RGBA.fromHex("#b9e27f"),
}

let app: Awaited<ReturnType<typeof testRender>> | undefined
afterEach(() => {
  app?.renderer.destroy()
  app = undefined
})

async function fixture(options: { width?: number; height?: number; rgb?: boolean; ansi256?: boolean } = {}) {
  const [enabled, setEnabled] = createSignal(false)
  const clock = manualClock()
  let root!: BoxRenderable
  let protectedArea!: BoxRenderable
  function Home() {
    const field = useGenomeField({ enabled, colors: () => colors, clock: clock.clock })
    return (
      <box ref={root} width="100%" height="100%" renderBefore={field}>
        <box id="home-top-space" height={8} flexShrink={0} />
        <box ref={protectedArea} height={5} flexShrink={0} paddingX={2}>
          <text selectable={true}>Scientific context Δ: liver_01</text>
          <textarea initialValue="Inspect RNA-seq samples" height={3} focused={true} />
        </box>
        <box id="home-open-space" flexGrow={1} />
      </box>
    )
  }
  app = await testRender(Home, { width: options.width ?? 80, height: options.height ?? 30 })
  const capabilities = setRendererCapabilities(app.renderer, {
    rgb: options.rgb ?? true,
    ansi256: options.ansi256 ?? true,
  })
  app.renderer.emit(CliRenderEvents.CAPABILITIES, capabilities)
  await app.renderOnce()
  await app.renderOnce()
  return { app, clock, root, protectedArea, setEnabled }
}

function hitGrid(setup: Awaited<ReturnType<typeof testRender>>) {
  return Array.from({ length: setup.renderer.height }, (_, y) =>
    Array.from({ length: setup.renderer.width }, (_, x) => setup.renderer.hitTest(x, y)),
  )
}

function protectedCharacters(setup: Awaited<ReturnType<typeof testRender>>, area: BoxRenderable) {
  return setup
    .captureCharFrame()
    .split("\n")
    .slice(area.screenY, area.screenY + area.height)
    .map((row) => row.slice(area.screenX, area.screenX + area.width))
}

test("genome field reveals in empty cells without changing content or mouse targets", async () => {
  const { app: setup, clock, root, protectedArea, setEnabled } = await fixture()
  const baseline = setup.captureCharFrame()
  const content = protectedCharacters(setup, protectedArea)
  const hits = hitGrid(setup)
  expect(clock.pending()).toBe(0)

  setEnabled(true)
  await setup.renderOnce()
  const resting = setup.captureSpans()
  expect(setup.captureCharFrame()).not.toBe(baseline)
  expect(clock.pending()).toBe(1)
  expect(root.selectable).toBe(false)

  clock.advance(1500)
  await setup.renderOnce()
  expect(setup.captureSpans()).not.toEqual(resting)
  expect(protectedCharacters(setup, protectedArea)).toEqual(content)
  expect(hitGrid(setup)).toEqual(hits)

  const rows = setup.captureCharFrame().split("\n")
  const field = [...rows.slice(0, protectedArea.screenY), ...rows.slice(protectedArea.screenY + protectedArea.height)]
  expect(field.join("")).toMatch(/[ACGT]/)
  expect(field.join("")).toMatch(/^[ACGT\s]*$/)

  await setup.mockMouse.drag(2, 1, 15, 1)
  expect(setup.renderer.getSelection()?.getSelectedText() ?? "").toBe("")
})

test("quiet mode clears decoration and releases its timer through repeated pauses and destruction", async () => {
  const { app: setup, clock, setEnabled } = await fixture()
  const plain = setup.captureCharFrame()
  for (let cycle = 0; cycle < 3; cycle++) {
    setEnabled(true)
    await setup.renderOnce()
    expect(clock.pending()).toBe(1)
    clock.advance(1200)
    await setup.renderOnce()
    setEnabled(false)
    await setup.renderOnce()
    expect(clock.pending()).toBe(0)
    expect(setup.captureCharFrame()).toBe(plain)
    clock.advance(20_000)
    await setup.renderOnce()
    expect(setup.captureCharFrame()).toBe(plain)
    expect(clock.pending()).toBe(0)
  }
  setEnabled(true)
  await setup.renderOnce()
  expect(clock.pending()).toBe(1)
  setup.renderer.destroy()
  expect(clock.pending()).toBe(0)
})

test("capability and size fallback keep constrained terminals still", async () => {
  const { app: setup, clock, setEnabled } = await fixture({ rgb: false, ansi256: false })
  const plain = setup.captureCharFrame()
  setEnabled(true)
  await setup.renderOnce()
  expect(setup.captureCharFrame()).toBe(plain)
  expect(clock.pending()).toBe(0)

  const capabilities = setRendererCapabilities(setup.renderer, { rgb: false, ansi256: true })
  setup.renderer.emit(CliRenderEvents.CAPABILITIES, capabilities)
  await setup.renderOnce()
  expect(clock.pending()).toBe(1)
  expect(setup.captureCharFrame()).not.toBe(plain)
  clock.advance(1500)
  await setup.renderOnce()
  expect(setup.captureCharFrame()).not.toBe(plain)

  const limited = setRendererCapabilities(setup.renderer, { rgb: false, ansi256: false })
  setup.renderer.emit(CliRenderEvents.CAPABILITIES, limited)
  await setup.renderOnce()
  expect(clock.pending()).toBe(0)
  expect(setup.captureCharFrame()).toBe(plain)

  const rgb = setRendererCapabilities(setup.renderer, { rgb: true, ansi256: false })
  setup.renderer.emit(CliRenderEvents.CAPABILITIES, rgb)
  await setup.renderOnce()
  expect(clock.pending()).toBe(1)
  setup.resize(39, 21)
  await setup.renderOnce()
  expect(clock.pending()).toBe(0)
  expect(setup.captureCharFrame().split("\n").slice(0, 8).join("").trim()).toBe("")
})

test("resize repositions the field while preserving protected content", async () => {
  const { app: setup, clock, protectedArea, setEnabled } = await fixture({ width: 120, height: 40 })
  setEnabled(true)
  await setup.renderOnce()
  clock.advance(1800)
  await setup.renderOnce()
  setup.resize(60, 24)
  await setup.renderOnce()
  const frame = setup.captureSpans()
  expect(frame.cols).toBe(60)
  expect(frame.rows).toBe(24)
  expect(protectedCharacters(setup, protectedArea).join("\n")).toContain("Scientific context Δ: liver_01")
  expect(protectedCharacters(setup, protectedArea).join("\n")).toContain("Inspect RNA-seq samples")
  expect(clock.pending()).toBe(1)
  setup.resize(120, 40)
  await setup.renderOnce()
  expect(protectedCharacters(setup, protectedArea).join("\n")).toContain("Scientific context Δ: liver_01")
  expect(clock.pending()).toBe(1)
})

test("unfocused terminals release the animation clock and recover on focus", async () => {
  const { app: setup, clock, setEnabled } = await fixture()
  const plain = setup.captureCharFrame()
  setEnabled(true)
  await setup.renderOnce()
  clock.advance(1500)
  await setup.renderOnce()
  expect(clock.pending()).toBe(1)

  setup.renderer.emit(CliRenderEvents.BLUR)
  await setup.renderOnce()
  expect(clock.pending()).toBe(0)
  expect(setup.captureCharFrame()).toBe(plain)
  setup.renderer.emit(CliRenderEvents.FOCUS)
  await setup.renderOnce()
  expect(clock.pending()).toBe(1)
  expect(setup.captureCharFrame()).not.toBe(plain)
})

test("eight-base fragments remain complementary and inside the free viewport", () => {
  const complements: Record<string, string> = { A: "T", T: "A", C: "G", G: "C" }
  for (const [width, height] of [
    [40, 22],
    [61, 25],
    [120, 40],
  ]) {
    const blocked = [
      { x: 0, y: 6, width: Math.min(width, 75), height: 7 },
      { x: width - 9, y: height - 4, width: 9, height: 4 },
    ]
    const field = genomeLayout(width, height, blocked)
    const obstructed = (x: number, y: number) =>
      blocked.some(
        (area) => x >= area.x - 1 && x < area.x + area.width + 1 && y >= area.y - 1 && y < area.y + area.height + 1,
      )
    const runsSafe = field.runs.every(
      (run) =>
        run.x >= 4 &&
        run.y >= 0 &&
        run.y < height &&
        run.x + run.text.length <= width - 2 &&
        Array.from(run.text).every((base, i) => base === " " || !obstructed(run.x + i, run.y)),
    )
    const fragmentsSafe = field.fragments.every((fragment) => {
      const inside = fragment.x >= 4 && fragment.x + 14 < width - 2 && fragment.y >= 0 && fragment.y < height
      const unobstructed = Array.from({ length: 8 }, (_, i) => !obstructed(fragment.x + i * 2, fragment.y)).every(
        Boolean,
      )
      const pairedY = (fragment.y / 2) % 2 === 0 ? fragment.y + 2 : fragment.y - 2
      const partner = field.fragments.find((other) => other.x === fragment.x && other.y === pairedY)
      const complementary =
        !partner || partner.sequence === Array.from(fragment.sequence, (base) => complements[base]).join("")
      return /^[ACGT]{8}$/.test(fragment.sequence) && inside && unobstructed && complementary
    })
    expect({ runsSafe, fragmentsSafe, nonempty: field.fragments.length > 0 }).toEqual({
      runsSafe: true,
      fragmentsSafe: true,
      nonempty: true,
    })
  }
})
