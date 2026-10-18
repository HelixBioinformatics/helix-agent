import { CliRenderEvents, RGBA, type OptimizedBuffer, type Renderable } from "@opentui/core"
import { useRenderer, useTerminalDimensions } from "@opentui/solid"
import { createEffect, createMemo, createSignal, onCleanup, type Accessor } from "solid-js"

type Rect = { x: number; y: number; width: number; height: number }
type Fragment = { x: number; y: number; sequence: string }
type Field = { runs: { x: number; y: number; text: string }[]; fragments: Fragment[] }
type Frame = { cycle: number; elapsed: number }
type Colors = { background: RGBA; textMuted: RGBA; primary: RGBA }

export type GenomeClock = {
  now(): number
  setTimeout(callback: () => void, delay: number): ReturnType<typeof setTimeout> | number
  clearTimeout(timer: ReturnType<typeof setTimeout> | number): void
}

const clock: GenomeClock = {
  now: () => performance.now(),
  setTimeout: (callback, delay) => {
    const timer = setTimeout(callback, delay)
    timer.unref?.()
    return timer
  },
  clearTimeout: (timer) => clearTimeout(timer),
}

/** Coordinate-derived decoration. Adjacent field rows are complementary, never user data. */
export function genomeAt(column: number, row: number) {
  let hash = Math.imul(column + 31, 0x45d9f3b) ^ Math.imul(Math.floor(row / 2) + 17, 0x27d4eb2d)
  hash = Math.imul(hash ^ (hash >>> 16), 0x45d9f3b)
  const base = (hash ^ (hash >>> 16)) & 3
  return (row % 2 ? "TGCA" : "ACGT")[base]
}

/** Reserve every foreground rectangle, including blank space inside interactive controls. */
export function genomeLayout(width: number, height: number, blocked: Rect[]): Field {
  const field: Field = { runs: [], fragments: [] }
  for (let y = 0; y < height; y += 2) {
    let run = ""
    let start = 0
    const flush = () => {
      if (run) field.runs.push({ x: start, y, text: run.trimEnd() })
      run = ""
    }
    for (let x = 4; x < width - 2; x += 2) {
      if (blocked.some((r) => x >= r.x - 1 && x < r.x + r.width + 1 && y >= r.y - 1 && y < r.y + r.height + 1)) {
        flush()
        continue
      }
      if (!run) start = x
      run += genomeAt(x / 2, y / 2) + (x + 1 < width ? " " : "")
      if (run.length >= 15) {
        const begin = x - 14
        field.fragments.push({
          x: begin,
          y,
          sequence: Array.from({ length: 8 }, (_, i) => genomeAt(begin / 2 + i, y / 2)).join(""),
        })
      }
    }
    flush()
  }
  return field
}

/** A soft travelling reveal: eight stable letters, each brightening and settling in place. */
export function fieldIntensity(elapsed: number, index: number, reverse = false) {
  const time = (elapsed - (reverse ? 7 - index : index) * 90) / 1600
  return time <= 0 || time >= 1 ? 0 : Math.sin(Math.PI * time) ** 2
}

/** One pending timeout; only a short reveal runs at 10fps. Rest periods do not render. */
export function createGenomeAnimation(paint: (frame: Frame | undefined) => void, source = clock) {
  let timer: ReturnType<GenomeClock["setTimeout"]>
  let cycle = 0
  let stopped = false
  const schedule = (callback: () => void, delay: number) => {
    timer = source.setTimeout(callback, delay)
  }
  const begin = () => {
    const started = source.now()
    const step = () => {
      if (stopped) return
      const elapsed = source.now() - started
      if (elapsed < 2600) {
        paint({ cycle, elapsed })
        schedule(step, 100)
      } else {
        paint(undefined)
        cycle++
        schedule(begin, 7500 + (cycle % 3) * 900)
      }
    }
    step()
  }
  schedule(begin, 900)
  return () => {
    stopped = true
    source.clearTimeout(timer)
  }
}

function mix(background: RGBA, foreground: RGBA, amount: number) {
  return RGBA.fromValues(
    background.r + (foreground.r - background.r) * amount,
    background.g + (foreground.g - background.g) * amount,
    background.b + (foreground.b - background.b) * amount,
    1,
  )
}

/** Paint into Home's existing box, adding no layout nodes, hit targets or selectable text. */
export function useGenomeField(options: { enabled: Accessor<boolean>; colors: Accessor<Colors>; clock?: GenomeClock }) {
  const renderer = useRenderer()
  const dimensions = useTerminalDimensions()
  const color = () => Boolean(renderer.capabilities?.rgb || renderer.capabilities?.ansi256)
  const [colorCapable, setColorCapable] = createSignal(color())
  const [focused, setFocused] = createSignal(true)
  const capabilities = () => setColorCapable(color())
  const focus = () => setFocused(true)
  const blur = () => setFocused(false)
  renderer.on(CliRenderEvents.CAPABILITIES, capabilities)
  renderer.on(CliRenderEvents.FOCUS, focus)
  renderer.on(CliRenderEvents.BLUR, blur)
  onCleanup(() => {
    renderer.off(CliRenderEvents.CAPABILITIES, capabilities)
    renderer.off(CliRenderEvents.FOCUS, focus)
    renderer.off(CliRenderEvents.BLUR, blur)
  })
  const enabled = createMemo(
    () => options.enabled() && colorCapable() && focused() && dimensions().width >= 40 && dimensions().height >= 22,
  )
  const palette = createMemo(() => {
    const { background, textMuted, primary } = options.colors()
    return Array.from({ length: 32 }, (_, i) => {
      const energy = i / 31
      const ink = mix(textMuted, primary, Math.min(1, energy * 2))
      return mix(background, ink, 0.045 + energy * 0.69)
    })
  })
  let frame: Frame | undefined
  createEffect(() => {
    frame = undefined
    renderer.requestRender()
    if (!enabled()) return
    const stop = createGenomeAnimation((next) => {
      frame = next
      renderer.requestRender()
    }, options.clock)
    onCleanup(stop)
  })
  let key = ""
  let field: Field
  return function (this: Renderable, buffer: OptimizedBuffer) {
    if (!enabled()) return
    const blocked = this.getChildren()
      .filter((child) => child.visible && child.id !== "home-top-space" && child.id !== "home-open-space")
      .map((child) => ({
        x: child.screenX - this.screenX,
        y: child.screenY - this.screenY,
        width: child.width,
        height: child.height,
      }))
    const layoutKey = JSON.stringify([this.width, this.height, blocked])
    if (key !== layoutKey) {
      key = layoutKey
      field = genomeLayout(this.width, this.height, blocked)
    }
    const colors = palette()
    for (const run of field.runs) buffer.drawText(run.text, this.screenX + run.x, this.screenY + run.y, colors[0])
    if (!frame || field.fragments.length === 0) return
    const chosen = (Math.imul(frame.cycle + 7, 7919) >>> 0) % field.fragments.length
    const fragment = field.fragments[chosen]
    const complement = field.fragments.find(
      (other) => other.x === fragment.x && other.y === ((fragment.y / 2) % 2 ? fragment.y - 2 : fragment.y + 2),
    )
    for (const [index, current] of [fragment, complement].entries()) {
      if (!current) continue
      for (let i = 0; i < 8; i++) {
        const intensity = fieldIntensity(frame.elapsed - index * 220, i, index === 1)
        buffer.drawText(
          current.sequence[i],
          this.screenX + current.x + i * 2,
          this.screenY + current.y,
          colors[Math.round(intensity * 31)],
        )
      }
    }
  }
}
