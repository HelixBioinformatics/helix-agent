/** @jsxImportSource @opentui/solid */
import { expect, test } from "bun:test"
import { testRender } from "@opentui/solid"
import { createSignal, type Accessor } from "solid-js"
import { PulseProvider, usePulse } from "../../src/context/pulse"

test("animations share one clock and release it on disable and unmount", async () => {
  const schedule = globalThis.setInterval
  const cancel = globalThis.clearInterval
  const active = new Set<ReturnType<typeof setInterval>>()
  globalThis.setInterval = new Proxy(schedule, {
    apply(target, receiver, args) {
      const timer = Reflect.apply(target, receiver, args)
      if (args[1] === 1000) active.add(timer)
      return timer
    },
  })
  globalThis.clearInterval = new Proxy(cancel, {
    apply(target, receiver, args) {
      active.delete(args[0])
      return Reflect.apply(target, receiver, args)
    },
  })
  const [first, setFirst] = createSignal(false)
  const [second, setSecond] = createSignal(false)
  function Animation(props: { enabled: Accessor<boolean> }) {
    const beat = usePulse().follow(props.enabled)
    return <text>{beat()}</text>
  }
  let app: Awaited<ReturnType<typeof testRender>> | undefined
  try {
    app = await testRender(
      () => (
        <PulseProvider>
          <Animation enabled={first} />
          <Animation enabled={second} />
        </PulseProvider>
      ),
      { width: 20, height: 4 },
    )
    await app.renderOnce()
    expect(active.size).toBe(0)
    setFirst(true)
    setSecond(true)
    await app.renderOnce()
    expect(active.size).toBe(1)
    setFirst(false)
    await app.renderOnce()
    expect(active.size).toBe(1)
    setSecond(false)
    await app.renderOnce()
    expect(active.size).toBe(0)
    setFirst(true)
    await app.renderOnce()
    expect(active.size).toBe(1)
    app.renderer.destroy()
    expect(active.size).toBe(0)
  } finally {
    if (app && !app.renderer.isDestroyed) app.renderer.destroy()
    for (const timer of active) cancel(timer)
    globalThis.setInterval = schedule
    globalThis.clearInterval = cancel
  }
})
