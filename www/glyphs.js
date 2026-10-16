// Campo de secuencias y texto que se decodifica: el brillo verde de Helix.
// Las letras de ADN y proteína se encienden bajo el cursor y se apagan dejando una estela.
"use strict"
;(() => {
  const DNA = "ACGT"
  const PROTEIN = "ACDEFGHIKLMNPQRSTVWY"
  const pick = (alphabet) => alphabet[(Math.random() * alphabet.length) | 0]
  const reduced = matchMedia("(prefers-reduced-motion: reduce)")

  // Del verde hoja al salvia luminoso de Helix según la energía de cada letra.
  const RAMP = [
    [126, 150, 98],
    [185, 226, 127],
    [236, 250, 214],
  ]
  function rampColor(e) {
    const t = Math.min(e, 1) * 2
    const [a, b] = t < 1 ? [RAMP[0], RAMP[1]] : [RAMP[1], RAMP[2]]
    const k = t < 1 ? t : t - 1
    return `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * k)).join(" ")})`
  }

  function field(canvas, host, options = {}) {
    const ctx = canvas.getContext("2d")
    const cfg = { cell: 15, row: 22, radius: 130, base: 0.065, intensity: 1, sparks: 5, ...options }
    const baseLayer = document.createElement("canvas")
    const baseCtx = baseLayer.getContext("2d")
    let width = 0,
      height = 0,
      dpr = 1,
      cols = 0,
      rows = 0
    let letters = [],
      original = [],
      energy = new Float32Array(0),
      alphabets = []
    const active = new Set()
    const pointer = { x: 0, y: 0, inside: false, speed: 0, lastX: 0, lastY: 0 }
    const wave = { x: -1, wait: 4 }
    let raf = 0,
      last = 0,
      visible = false

    const font = () => `500 ${12}px ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace`

    function build() {
      const rect = canvas.getBoundingClientRect()
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      width = rect.width
      height = rect.height
      for (const c of [canvas, baseLayer]) {
        c.width = Math.round(width * dpr)
        c.height = Math.round(height * dpr)
      }
      cols = Math.ceil(width / cfg.cell)
      rows = Math.ceil(height / cfg.row)
      alphabets = Array.from({ length: rows }, (_, r) => (r % 3 === 2 ? PROTEIN : DNA))
      original = Array.from({ length: cols * rows }, (_, i) =>
        Math.random() < 0.07 ? " " : pick(alphabets[(i / cols) | 0]),
      )
      letters = original.slice()
      energy = new Float32Array(cols * rows)
      active.clear()
      baseCtx.setTransform(dpr, 0, 0, dpr, 0, 0)
      baseCtx.clearRect(0, 0, width, height)
      baseCtx.font = font()
      baseCtx.textAlign = "center"
      baseCtx.textBaseline = "middle"
      baseCtx.fillStyle = `rgb(196 210 200 / ${cfg.base})`
      for (let i = 0; i < original.length; i++) {
        const x = (i % cols) * cfg.cell + cfg.cell / 2
        const y = ((i / cols) | 0) * cfg.row + cfg.row / 2
        baseCtx.fillText(original[i], x, y)
      }
      draw()
    }

    function excite(i, amount) {
      if (original[i] === " ") return
      energy[i] = Math.min(1, energy[i] + amount)
      active.add(i)
    }

    // Una lectura corta que se enciende de golpe, como un k-mer al alinearse.
    function spark() {
      const r = (Math.random() * rows) | 0
      const c = (Math.random() * cols) | 0
      const length = 3 + ((Math.random() * 7) | 0)
      const peak = 0.35 + Math.random() * 0.45
      for (let k = 0; k < length && c + k < cols; k++) excite(r * cols + c + k, peak * (1 - k / (length + 2)))
    }

    function step(dt) {
      const intensity = cfg.intensity
      for (const i of active) {
        energy[i] *= Math.exp(-dt * 1.7)
        if (energy[i] < 0.012) {
          energy[i] = 0
          letters[i] = original[i]
          active.delete(i)
        } else if (Math.random() < energy[i] * dt * 16) letters[i] = pick(alphabets[(i / cols) | 0])
      }
      if (pointer.inside) {
        const radius = cfg.radius
        const c0 = Math.max(0, Math.floor((pointer.x - radius) / cfg.cell))
        const c1 = Math.min(cols - 1, Math.ceil((pointer.x + radius) / cfg.cell))
        const r0 = Math.max(0, Math.floor((pointer.y - radius) / cfg.row))
        const r1 = Math.min(rows - 1, Math.ceil((pointer.y + radius) / cfg.row))
        const boost = (2.2 + Math.min(pointer.speed, 1600) / 260) * intensity
        for (let r = r0; r <= r1; r++)
          for (let c = c0; c <= c1; c++) {
            const dx = c * cfg.cell + cfg.cell / 2 - pointer.x
            const dy = r * cfg.row + cfg.row / 2 - pointer.y
            const d = Math.hypot(dx, dy) / radius
            if (d < 1 && Math.random() < 0.85) excite(r * cols + c, (1 - d) * (1 - d) * boost * dt)
          }
        pointer.speed *= Math.exp(-dt * 6)
      }
      if (Math.random() < cfg.sparks * intensity * dt) spark()
      // Una onda de transcripción cruza el campo de vez en cuando.
      wave.wait -= dt
      if (wave.wait <= 0 && wave.x < 0) wave.x = 0
      if (wave.x >= 0) {
        const c = Math.floor(wave.x / cfg.cell)
        if (c < cols)
          for (let r = 0; r < rows; r++) if (Math.random() < 0.35) excite(r * cols + c, 0.22 * intensity)
        wave.x += dt * 520
        if (wave.x > width) {
          wave.x = -1
          wave.wait = 9 + Math.random() * 5
        }
      }
    }

    function draw() {
      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(baseLayer, 0, 0)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.font = font()
      ctx.textAlign = "center"
      ctx.textBaseline = "middle"
      for (const i of active) {
        const e = energy[i]
        const x = (i % cols) * cfg.cell
        const y = ((i / cols) | 0) * cfg.row
        ctx.clearRect(x, y, cfg.cell, cfg.row)
        const flicker = 0.75 + Math.random() * 0.25
        ctx.globalAlpha = Math.min(1, cfg.base + e * 1.15 * flicker)
        ctx.fillStyle = rampColor(e)
        if (e > 0.6) {
          ctx.shadowColor = "rgb(185 226 127 / 0.9)"
          ctx.shadowBlur = 10
        }
        ctx.fillText(letters[i], x + cfg.cell / 2, y + cfg.row / 2)
        ctx.shadowBlur = 0
      }
      ctx.globalAlpha = 1
    }

    function frame(now) {
      raf = 0
      const dt = Math.min((now - (last || now)) / 1000, 0.05)
      last = now
      step(dt)
      draw()
      if (visible) raf = requestAnimationFrame(frame)
    }
    function start() {
      if (!raf && visible && !reduced.matches) {
        last = 0
        raf = requestAnimationFrame(frame)
      }
    }

    host.addEventListener(
      "pointermove",
      (event) => {
        const rect = canvas.getBoundingClientRect()
        const x = event.clientX - rect.left
        const y = event.clientY - rect.top
        if (pointer.inside) pointer.speed += Math.hypot(x - pointer.lastX, y - pointer.lastY) * 2
        pointer.x = pointer.lastX = x
        pointer.y = pointer.lastY = y
        pointer.inside = true
      },
      { passive: true },
    )
    host.addEventListener("pointerleave", () => (pointer.inside = false))
    new ResizeObserver(build).observe(canvas)
    new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting
      visible ? start() : (cancelAnimationFrame(raf), (raf = 0))
    }).observe(canvas)
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        cancelAnimationFrame(raf)
        raf = 0
      } else start()
    })
  }

  // Texto que se decodifica letra a letra desde una secuencia, como al abrir una sesión.
  const escape = (ch) => (ch === "<" ? "&lt;" : ch === "&" ? "&amp;" : ch === ">" ? "&gt;" : ch)
  const STATIC = /[\s/·,.:;→↗↓↘↑—–\-()¿?!¡]/

  function prepare(el) {
    if (el.dataset.ready) return el.querySelector("[data-glyph-target]")
    const text = el.textContent.trim()
    const readable = document.createElement("span")
    readable.className = "sr-only"
    readable.textContent = text
    const visual = document.createElement("span")
    visual.setAttribute("aria-hidden", "true")
    visual.dataset.glyphTarget = text
    visual.textContent = text
    el.replaceChildren(readable, visual)
    el.dataset.ready = "1"
    return visual
  }

  function scramble(el, { alphabet = DNA, stagger = 24, spread = 280 } = {}) {
    const target = prepare(el)
    const text = target.dataset.glyphTarget
    if (reduced.matches) return
    cancelAnimationFrame(target._raf)
    const settle = [...text].map((_, i) => 120 + i * stagger + Math.random() * spread)
    const begin = performance.now()
    const tick = (now) => {
      const t = now - begin
      let html = ""
      let pending = false
      for (let i = 0; i < text.length; i++) {
        const ch = text[i]
        if (STATIC.test(ch) || t >= settle[i]) html += escape(ch)
        else {
          pending = true
          html += `<span class="glyph">${pick(alphabet)}</span>`
        }
      }
      target.innerHTML = html
      if (pending) target._raf = requestAnimationFrame(tick)
    }
    target._raf = requestAnimationFrame(tick)
  }

  window.HelixGlyphs = { field, scramble, prepare, DNA, PROTEIN }
})()
