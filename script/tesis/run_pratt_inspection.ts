import fs from "node:fs/promises"
import path from "node:path"
import { TrpStructural as C } from "../../packages/helix/src/trp/structural"

// Representative published examples exercise the actual agent file adapter.
// The full deterministic two-profile challenge is evaluate_pratt_originals.py.
const root = path.resolve(import.meta.dir, "../..")
const base = "evaluation/trp/reference/pratt-author-20261001"
const cases = JSON.parse(await fs.readFile(path.join(root, base, "cases.json"), "utf8"))
const records = []
for (const item of cases.filter((c: { label: string }) => c.label === "published_problem")) {
  const meta = JSON.parse(await fs.readFile(path.join(root, base, "metadata", item.identifier + ".json"), "utf8"))
  const width = item.repeatSequence.length
  const result = await C.inspectFiles(
    {
      structure: path.join(base, "originals", meta.structureFile),
      options: {
        format: "pdb",
        model: 1,
        chain: "A",
        frame: "auth_seq_id",
        units: Array.from({ length: 10 }, (_, i) => ({ start: i * width + 1, end: (i + 1) * width })),
        plddtMin: 70,
        paeMax: 5,
      },
      colabfold: {
        metadata: path.join(base, "metadata", item.identifier + ".json"),
        scores: path.join(base, "originals", meta.scoresFile),
        pae: path.join(base, "originals", meta.paeFile),
      },
    },
    root,
  )
  const expected = JSON.parse(
    await fs.readFile(path.join(root, base, "reports/all-ten-repeats", item.identifier + ".json"), "utf8"),
  )
  if (JSON.stringify(result.report) !== JSON.stringify(expected)) {
    // Object key order differs between canonical TS JSON and Python pretty JSON.
    const canonical = (value: unknown): string =>
      JSON.stringify(value, (_key, item) =>
        item && typeof item === "object" && !Array.isArray(item)
          ? Object.fromEntries(Object.entries(item).sort(([a], [b]) => a.localeCompare(b)))
          : item,
      )
    if (canonical(result.report) !== canonical(expected)) throw new Error("adapter/core mismatch: " + item.identifier)
  }
  const python = process.env.HELIX_TRP_PYTHON ?? "python3"
  const child = Bun.spawn(
    [python, path.join(result.directory, "verify.py"), result.directory, "--sha256", result.manifestSha256],
    { stdout: "pipe", stderr: "pipe" },
  )
  const verification = JSON.parse(await new Response(child.stdout).text())
  if ((await child.exited) !== 0 || !verification.ok) throw new Error("portable verification failed")
  records.push({
    case: item.identifier,
    directory: path.relative(root, result.directory),
    manifestSha256: result.manifestSha256,
    verification,
    matchesCoreReport: true,
  })
}
await fs.writeFile(
  path.join(root, base, "agent-adapter.json"),
  JSON.stringify(
    {
      version: C.VERSION,
      modelCalls: 0,
      scope: "actual trp_inspect file adapter, without LLM inference",
      cases: records,
    },
    null,
    2,
  ) + "\n",
)
console.log(JSON.stringify({ verified: records.length, matchesCoreReport: true, modelCalls: 0 }))
