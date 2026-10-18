import { resolve } from "node:path"
import { readFileSync, existsSync, readdirSync } from "node:fs"
import { createHash } from "node:crypto"
const root = resolve(import.meta.dir, "../..")
const workspace = resolve(root, "tmp/tui-identity")
const dir = resolve(workspace, "verification")
const allFlows = [
  "permission-once",
  "permission-always",
  "permission-reject",
  "permission-mouse",
  "question-select",
  "question-custom",
  "question-reject",
  "dialog-select",
  "dialog-mouse",
  "dialog-prompt",
  "prompt-unicode",
  "prompt-paste",
  "prompt-ime-flush",
  "copy-selection",
  "interrupt",
]
const flows = process.env.VERIFY_FLOWS?.split(",").filter(Boolean) ?? allFlows
const sizes = process.env.VERIFY_SIZES?.split(",").map((s) => s.split("x").map(Number)) ?? [
  [120, 40],
  [60, 20],
]
const results = []
for (const flow of flows)
  for (const [width, height] of sizes) {
    const file = `${flow}-${width}x${height}.json`
    const before = JSON.parse(readFileSync(resolve(dir, "before", file), "utf8"))
    const after = JSON.parse(readFileSync(resolve(dir, "after", file), "utf8"))
    results.push({
      flow,
      width,
      height,
      beforePassed: before.passed,
      afterPassed: after.passed,
      effectsEqual: JSON.stringify(before.effects) === JSON.stringify(after.effects),
      callbacksEqual: JSON.stringify(before.callbacks) === JSON.stringify(after.callbacks),
      effects: after.effects,
      callbacks: after.callbacks,
      beforeError: before.error,
      afterError: after.error,
    })
  }
const audit = JSON.parse(readFileSync(resolve(dir, "behavioral-source-audit.json"), "utf8"))
const baseline = resolve(root, process.env.VERIFY_SOURCE ?? "tmp/tui-identity/baseline/source", "src")
const active = resolve(root, "packages/tui/src")
function sourceFiles(directory: string, prefix = ""): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = prefix + entry.name
    return entry.isDirectory() ? sourceFiles(resolve(directory, entry.name), path + "/") : [path]
  })
}
const sourceHashes = Object.fromEntries(
  sourceFiles(active)
    .filter((path) => {
      const before = resolve(baseline, path)
      return !existsSync(before) || !readFileSync(before).equals(readFileSync(resolve(active, path)))
    })
    .map((path) => [
      "packages/tui/src/" + path,
      createHash("sha256")
        .update(readFileSync(resolve(active, path)))
        .digest("hex"),
    ]),
)
const report = {
  generatedAt: new Date().toISOString(),
  scope: `${flows.length} full-app mocked-SDK input flows at ${sizes.map(([w, h]) => `${w}×${h}`).join(", ")}, comparing same fixtures against frozen source and active source. No external provider or pipeline calls.`,
  cases: results.length,
  allPassed: results.every((r) => r.beforePassed && r.afterPassed && r.effectsEqual && r.callbacksEqual),
  sdkCallsAllEqual: audit.sdkCallsAllEqual,
  bindingsAllEqual: audit.bindingsAllEqual,
  limitations: [
    "OS-level IME composition is not modeled by this renderer test API. A real Textarea late-flush path is exercised separately: double Enter, next-tick composed Hangul tail insertion, one final-text submission.",
    "Typed Unicode uses pressKeys(Array.from(text)) and NFC because OpenTUI0.4.3 mockInput.typeText splits surrogate pairs; decomposed combining text and emoji are additionally exercised through bracketed paste.",
    "Clipboard writes are intercepted after native mouse selection; the fixtures compare copied text and selection cleanup without modifying the OS clipboard.",
    "These assertions prove exercised actions/payloads, not the absence of every possible behavioral difference; AST review provides separate evidence for unchanged SDK calls and binding registrations.",
  ],
  sourceHashes,
  results,
}
await Bun.write(resolve(dir, "behavioral-comparison.json"), JSON.stringify(report, null, 2))
console.log(
  JSON.stringify(
    {
      cases: report.cases,
      allPassed: report.allPassed,
      sdkCallsAllEqual: report.sdkCallsAllEqual,
      bindingsAllEqual: report.bindingsAllEqual,
      failed: results.filter((r) => !r.beforePassed || !r.afterPassed || !r.effectsEqual || !r.callbacksEqual),
    },
    null,
    2,
  ),
)
if (!report.allPassed || !report.sdkCallsAllEqual || !report.bindingsAllEqual) process.exit(1)
