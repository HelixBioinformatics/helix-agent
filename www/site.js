const store = {
  get(key) {
    try {
      return localStorage.getItem(key)
    } catch {
      return null
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value)
    } catch {}
  },
}
const labels = {
  es: {
    copy: "Copiar",
    done: "Copiado",
    failed: "Selecciona el comando para copiarlo",
    title: "Helix Agent | Bioinformática en tu terminal",
  },
  en: {
    copy: "Copy",
    done: "Copied",
    failed: "Select the command to copy it",
    title: "Helix Agent | Bioinformatics in your terminal",
  },
}
// This is a convenience default, never a requirement: all systems stay selectable.
// Linux distributions are not reliably exposed by browsers.
function detectOs() {
  const ua = navigator.userAgent || ""
  const platform = navigator.userAgentData?.platform || navigator.platform || ""
  if (/Android|iPhone|iPad|iPod|CrOS/i.test(ua) || /Android|iOS|Chrome OS/i.test(platform)) return null
  if (/Mac/i.test(platform) && navigator.maxTouchPoints > 1) return null
  if (/Windows|Win32|Win64/i.test(platform + " " + ua)) return "win"
  if (/Mac/i.test(platform + " " + ua)) return "mac"
  if (/Linux/i.test(platform + " " + ua)) return "linux"
  return null
}
const detectedOs = detectOs()
const osNames = { linux: "Linux", mac: "macOS", win: "Windows" }
function applyLang(lang) {
  document.getElementById("lang-" + lang).checked = true
  document.documentElement.lang = lang
  document.title = labels[lang].title
  const recommendation = document.getElementById("os-recommendation")
  recommendation.hidden = !detectedOs
  if (detectedOs)
    recommendation.textContent =
      lang === "es"
        ? `Recomendado para tu equipo: ${osNames[detectedOs]}. Puedes elegir otro sistema.`
        : `Recommended for your device: ${osNames[detectedOs]}. You can choose another system.`
  for (const node of document.querySelectorAll("[data-lang]")) node.lang = node.dataset.lang
  for (const button of document.querySelectorAll(".copy")) {
    button.textContent = labels[lang].copy
    delete button.dataset.done
  }
}
const savedLang = store.get("lang")
applyLang(
  ["es", "en"].includes(savedLang) ? savedLang : navigator.language.toLowerCase().startsWith("es") ? "es" : "en",
)
const savedOs = store.get("os")
const os = ["linux", "mac", "win"].includes(savedOs) ? savedOs : detectedOs || "linux"
if (detectedOs) {
  const systems = document.querySelector(".systems")
  systems.prepend(systems.querySelector(`label[for="os-${detectedOs}"]`))
}
document.getElementById("os-" + os).checked = true
for (const lang of ["es", "en"])
  document.getElementById("lang-" + lang).addEventListener("change", () => {
    store.set("lang", lang)
    applyLang(lang)
  })
for (const os of ["linux", "mac", "win"])
  document.getElementById("os-" + os).addEventListener("change", () => store.set("os", os))
const status = document.createElement("span")
status.className = "copy-status"
status.setAttribute("role", "status")
status.setAttribute("aria-live", "polite")
document.body.appendChild(status)
async function copyText(value, button) {
  try {
    await navigator.clipboard.writeText(value)
    return true
  } catch {
    const area = document.createElement("textarea")
    area.value = value
    area.style.cssText = "position:fixed;opacity:0"
    document.body.appendChild(area)
    area.select()
    try {
      return document.execCommand("copy")
    } catch {
      return false
    } finally {
      area.remove()
      button.focus()
    }
  }
}
for (const block of document.querySelectorAll(".cmd[data-copy]")) {
  const button = document.createElement("button")
  button.type = "button"
  button.className = "copy"
  button.textContent = labels[document.documentElement.lang].copy
  button.addEventListener("click", async () => {
    const copied = await copyText(block.dataset.copy, button)
    const text = labels[document.documentElement.lang]
    button.textContent = copied ? text.done : text.copy
    button.dataset.done = String(copied)
    status.textContent = copied ? text.done : text.failed
    setTimeout(() => {
      button.textContent = labels[document.documentElement.lang].copy
      delete button.dataset.done
    }, 2000)
  })
  block.appendChild(button)
}
for (const button of document.querySelectorAll("[data-copy-value]"))
  button.addEventListener("click", async () => {
    const copied = await copyText(button.dataset.copyValue, button)
    button.dataset.done = String(copied)
    status.textContent = labels[document.documentElement.lang][copied ? "done" : "failed"]
    setTimeout(() => delete button.dataset.done, 2000)
  })

// En un teléfono no se instala: se ofrece enviar el enlace a la computadora o ver los pasos igualmente.
const installLink = () => location.origin + location.pathname + "#download"
document.querySelector("[data-share-link]").addEventListener("click", async (event) => {
  const button = event.currentTarget
  if (navigator.share) {
    try {
      await navigator.share({ title: "Helix Agent", url: installLink() })
      return
    } catch (error) {
      if (error.name === "AbortError") return
    }
  }
  const copied = await copyText(installLink(), button)
  status.textContent = labels[document.documentElement.lang][copied ? "done" : "failed"]
  button.dataset.done = String(copied)
  setTimeout(() => delete button.dataset.done, 2000)
})
document
  .querySelector("[data-show-steps]")
  .addEventListener("click", () => document.documentElement.classList.add("show-steps"))

// Movimiento: todo lo que sigue es decorativo y respeta prefers-reduced-motion.
const reduced = matchMedia("(prefers-reduced-motion: reduce)")
const once = (elements, callback, options = { threshold: 0.15 }) => {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries)
      if (entry.isIntersecting) {
        observer.unobserve(entry.target)
        callback(entry.target)
      }
  }, options)
  for (const element of elements) observer.observe(element)
}

const hero = document.querySelector(".hero")
requestAnimationFrame(() => requestAnimationFrame(() => hero.classList.add("is-ready")))

once(document.querySelectorAll("[data-reveal]"), (el) => el.classList.add("is-in"), {
  threshold: 0.12,
  rootMargin: "0px 0px -6% 0px",
})

// Las etiquetas se decodifican desde una secuencia de ADN al aparecer.
const { scramble, prepare, field } = window.HelixGlyphs
for (const el of document.querySelectorAll("[data-scramble]")) prepare(el)
setTimeout(() => document.querySelectorAll('[data-scramble="load"]').forEach((el) => scramble(el)), 280)
once(document.querySelectorAll('[data-scramble="view"]'), (el) => setTimeout(() => scramble(el), 180))
for (const eyebrow of document.querySelectorAll(".eyebrow"))
  eyebrow.addEventListener("pointerenter", () =>
    eyebrow.querySelectorAll("[data-scramble]").forEach((el) => el.offsetParent && scramble(el, { spread: 160 })),
  )

const header = document.querySelector(".site-header")
let scrollQueued = false
function onScroll() {
  if (scrollQueued) return
  scrollQueued = true
  requestAnimationFrame(() => {
    scrollQueued = false
    const max = document.documentElement.scrollHeight - innerHeight
    header.classList.toggle("is-scrolled", scrollY > 8)
    header.style.setProperty("--progress", max > 0 ? (scrollY / max).toFixed(4) : "0")
  })
}
addEventListener("scroll", onScroll, { passive: true })
onScroll()

for (const el of document.querySelectorAll(".spot"))
  el.addEventListener("pointermove", (event) => {
    const rect = el.getBoundingClientRect()
    el.style.setProperty("--mx", `${event.clientX - rect.left}px`)
    el.style.setProperty("--my", `${event.clientY - rect.top}px`)
  })

// Hélices metálicas.
const figure = document.querySelector(".hero-figure")
const angleLabel = document.getElementById("helix-angle")
const tip = document.getElementById("bp-tip")
let shownAngle = -1
const helixCanvas = document.getElementById("helix-canvas")
const helix = window.HelixGL?.mount(helixCanvas, {
  shape: "helix",
  onFrame({ angle }) {
    const value = Math.round(angle)
    if (value === shownAngle) return
    shownAngle = value
    angleLabel.textContent = `θ ${String(value).padStart(3, "0")}°`
  },
  onHover(info) {
    tip.classList.toggle("is-on", !!info)
    if (info) {
      const bond = info.base === "A" || info.base === "T" ? "=" : "≡"
      tip.textContent = `bp ${String(info.index).padStart(2, "0")} · ${info.base}${bond}${info.pair}`
    }
  },
})
if (!helix) figure.classList.add("no-webgl")
helixCanvas.addEventListener("pointermove", (event) => {
  const rect = figure.getBoundingClientRect()
  tip.style.left = `${event.clientX - rect.left}px`
  tip.style.top = `${event.clientY - rect.top}px`
})
const protein = window.HelixGL?.mount(document.getElementById("protein-canvas"), {
  shape: "gfp",
  light: true,
  scrollMode: "section",
})
if (!protein) document.querySelector(".about-figure").hidden = true

field(document.querySelector(".hero-glyphs"), hero, { base: innerWidth < 680 ? 0.04 : 0.06 })
field(document.querySelector(".footer-glyphs"), document.querySelector(".site-footer"), { base: 0.045, sparks: 2 })

// Sesión ilustrativa: el prompt se escribe y el plan aparece paso a paso.
const term = document.getElementById("term")
function playSession() {
  const main = [...term.querySelectorAll(".term-main [data-step]")]
  const side = [...term.querySelectorAll(".term-side [data-step]")]
  if (reduced.matches) {
    for (const step of [...main, ...side]) step.classList.add("is-on")
    return
  }
  side.forEach((step, i) => setTimeout(() => step.classList.add("is-on"), 200 + i * 220))
  const prompt = term.querySelector(".term-prompt")
  const typed = [...term.querySelectorAll("[data-type]")]
  const texts = typed.map((el) => el.textContent.replace(/\s+/g, " ").trim())
  typed.forEach((el) => (el.textContent = ""))
  prompt.classList.add("is-typing")
  let shown = 0
  const longest = Math.max(...texts.map((text) => text.length))
  const type = () => {
    shown += Math.random() < 0.3 ? 2 : 1
    typed.forEach((el, i) => (el.textContent = texts[i].slice(0, shown)))
    if (shown < longest) return setTimeout(type, 18 + Math.random() * 30)
    prompt.classList.remove("is-typing")
    main.forEach((step, i) => setTimeout(() => step.classList.add("is-on"), 420 + i * 300))
  }
  setTimeout(type, 500)
}
once([term], playSession, { threshold: 0.35 })

const video = document.getElementById("demo-video")
const body = term.querySelector(".term-body")
const progress = term.querySelector(".term-progress")
const videoHeight = () => Math.round((body.offsetWidth * 1080) / 1750)
function openVideo(fullscreen) {
  if (!term.classList.contains("is-playing")) {
    body.style.height = `${body.offsetHeight}px`
    term.classList.add("is-playing")
    requestAnimationFrame(() => (body.style.height = `${videoHeight()}px`))
  }
  video.play().catch(() => {})
  if (fullscreen) video.requestFullscreen?.().catch(() => {})
}
for (const trigger of document.querySelectorAll("[data-play]"))
  trigger.addEventListener("click", () => {
    if (term.classList.contains("is-playing") && trigger.closest(".term")) video.paused ? video.play() : video.pause()
    else openVideo(false)
  })
term.querySelector("[data-fullscreen]").addEventListener("click", () => openVideo(true))
video.addEventListener("timeupdate", () =>
  progress.style.setProperty("--p", video.duration ? (video.currentTime / video.duration).toFixed(4) : "0"),
)
new ResizeObserver(() => {
  if (term.classList.contains("is-playing")) body.style.height = `${videoHeight()}px`
}).observe(term)

// Evidencia: cada artefacto se verifica en orden y se ilumina al pasar el cursor.
const ledger = document.getElementById("ledger")
once(
  [ledger],
  () => {
    const rows = [...ledger.querySelectorAll(".ledger-rows li")]
    const state = ledger.querySelector(".verify-state")
    const delay = reduced.matches ? 0 : 450
    rows.forEach((row, i) =>
      setTimeout(() => {
        row.classList.add("is-ok", "is-lit")
        setTimeout(() => row.classList.remove("is-lit"), reduced.matches ? 0 : 900)
      }, delay + i * delay),
    )
    setTimeout(
      () => {
        state.textContent = "OK"
        scramble(state, { stagger: 40 })
      },
      delay * (rows.length + 1),
    )
  },
  { threshold: 0.4 },
)
for (const el of document.querySelectorAll("[data-artifact]")) {
  const light = (on) =>
    document.querySelectorAll(`[data-artifact="${el.dataset.artifact}"]`).forEach((node) => node.classList.toggle("is-lit", on))
  el.addEventListener("pointerenter", () => light(true))
  el.addEventListener("pointerleave", () => light(false))
}
