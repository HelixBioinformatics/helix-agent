export * as TrpInterventions from "./interventions"

import { HandCount } from "../nfcore/handcount"

export const VERSION = "trp-handcount-es-en/1.0.0"
const cues: { class: HandCount.Intervention; id: string; test: RegExp }[] = [
  {
    class: "factual-correction",
    id: "es.correction",
    test: /\b(eso es incorrecto|te equivocaste|corrige|la cadena correcta|el residuo correcto|no es correcto)\b/,
  },
  {
    class: "rejection",
    id: "es.rejection",
    test: /\b(rechazo|rechazar|no ejecutes|no lo ejecutes|deten|cancela|no apruebo)\b/,
  },
  {
    class: "redirection",
    id: "es.redirection",
    test: /\b(en vez de|en lugar de|cambia el objetivo|ahora analiza|prioriza|mejor usa)\b/,
  },
  {
    class: "disambiguation",
    id: "es.clarification",
    test: /\b(me refiero|para aclarar|la primera opcion|la segunda opcion|quise decir|ambas cadenas)\b/,
  },
  {
    class: "approval",
    id: "es.approval",
    test: /\b(apruebo|aprobar y ejecutar|adelante|de acuerdo|puedes ejecutar)\b/,
  },
]

export function classify(text: string): HandCount.Classification {
  const normalized = HandCount.normalize(HandCount.stripInjected(text)).normalize("NFD").replace(/\p{M}/gu, "")
  const english = HandCount.classifyDetailed(text)
  for (const cls of HandCount.PRECEDENCE) {
    const value = cls === "approval" ? normalized.split(/\b(?:pero|sin embargo|excepto)\b/).at(-1)! : normalized
    const hits = cues.filter((cue) => cue.class === cls && cue.test.test(value))
    // Negated approvals are rejection cues and must not win through a substring.
    if (hits.length) return { class: cls, score: hits.length * 3, cues: hits.map((cue) => cue.id) }
    if (english.class === cls) return english
  }
  return { class: "other", score: 0, cues: [] }
}

export function tally(turns: readonly string[]) {
  const counts = Object.fromEntries(HandCount.CLASSES.map((cls) => [cls, 0]))
  const entries = turns.map((text, index) => {
    const result = classify(text)
    counts[result.class]++
    return { index, text, ...result }
  })
  return {
    classifier: VERSION,
    total: turns.length,
    entries,
    counts,
    externalAgreement: null,
    limitation:
      "Deterministic surface-cue heuristic, not an intent oracle. Other means no cue found. External non-adjudicated labels and kappa remain pending.",
  }
}
