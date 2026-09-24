import { beforeEach, afterEach, expect, test } from "bun:test"
import fs from "node:fs/promises"
import path from "node:path"
import os from "node:os"
import { executePredicted, launch, APPROVE } from "../../src/tool/trp-predicted"
import source from "../../../../evaluation/trp/reference/predicted-geometry-20260921-corrected/request.json"

const checkout = path.resolve(import.meta.dir, "../../../..")
let root: string
const oldPython = process.env.HELIX_TRP_PYTHON
beforeEach(async () => {
  root = await fs.mkdtemp(path.join(os.tmpdir(), "helix-predicted-test-"))
  process.env.HELIX_TRP_PYTHON = oldPython ?? path.join(checkout, ".bioinformatica/trp-python/bin/python")
  await fs.writeFile(path.join(root, "input.cif"), source.structure)
  await fs.writeFile(path.join(root, "pae.json"), JSON.stringify(source.pae))
  await fs.writeFile(path.join(root, "api.json"), JSON.stringify(source.api))
})
afterEach(async () => {
  await fs.rm(root, { recursive: true, force: true })
  if (oldPython) process.env.HELIX_TRP_PYTHON = oldPython
  else delete process.env.HELIX_TRP_PYTHON
})
const args = () => ({
  structure: "input.cif",
  pae: "pae.json",
  api: "api.json",
  options: structuredClone(source.options) as any,
})
const signal = () => new AbortController().signal

test("forged model approvals and escaping files are refused", async () => {
  const deps = { approve: async () => [[APPROVE]] }
  await expect(executePredicted({ ...args(), approved: true } as any, root, "s", signal(), deps)).rejects.toThrow()
  await fs.symlink(path.join(checkout, "package.json"), path.join(root, "outside.json"))
  await expect(executePredicted({ ...args(), api: "outside.json" }, root, "s", signal(), deps)).rejects.toThrow(
    "escapes",
  )
})

test("human rejection never starts scientific process", async () => {
  const calls: string[] = []
  await expect(
    executePredicted(args(), root, "session-x", signal(), {
      approve: async (prompt) => {
        expect(prompt).toContain("session-x")
        expect(prompt).toContain("pLDDT")
        return [["Rechazar"]]
      },
      launch: async (script, a, dir, sig) => {
        calls.push(a[0])
        return launch(script, a, dir, sig)
      },
    }),
  ).rejects.toThrow("unapproved")
  expect(calls).toEqual(["prepare"])
})

test.each(["input.cif", "pae.json", "api.json"])("changed original %s invalidates approval", async (file) => {
  const calls: string[] = []
  await expect(
    executePredicted(args(), root, "s", signal(), {
      approve: async () => {
        await fs.appendFile(path.join(root, file), " ")
        return [[APPROVE]]
      },
      launch: async (script, a, dir, sig) => {
        calls.push(a[0])
        return launch(script, a, dir, sig)
      },
    }),
  ).rejects.toThrow("Original source changed")
  expect(calls).toEqual(["prepare"])
})

test("mismatched AFDB identity and insufficient units fail before approval", async () => {
  let approvals = 0
  const deps = {
    approve: async () => {
      approvals++
      return [[APPROVE]]
    },
  }
  const altered = structuredClone(source.api)
  altered[0].sequence = "A".repeat(altered[0].sequence.length)
  await fs.writeFile(path.join(root, "api.json"), JSON.stringify(altered))
  await expect(executePredicted(args(), root, "s", signal(), deps)).rejects.toThrow("structural-rejection")
  await fs.writeFile(path.join(root, "api.json"), JSON.stringify(source.api))
  const short = args()
  short.options.units = short.options.units.slice(0, 2)
  await expect(executePredicted(short, root, "s", signal(), deps)).rejects.toThrow("three-units")
  expect(approvals).toBe(0)
})

test("tampered adapter or proposal cannot execute", async () => {
  let runner = ""
  await expect(
    executePredicted(args(), root, "s", signal(), {
      approve: async () => {
        await fs.appendFile(runner, "\n#tamper\n")
        return [[APPROVE]]
      },
      launch: async (script, a, dir, sig) => {
        runner = script
        return launch(script, a, dir, sig)
      },
    }),
  ).rejects.toThrow("adapter or proposal changed")
})

test("cancellation during approval never starts geometry", async () => {
  const abort = new AbortController(),
    calls: string[] = []
  await expect(
    executePredicted(args(), root, "s", abort.signal, {
      approve: async () => {
        abort.abort()
        return [[APPROVE]]
      },
      launch: async (script, a, dir, sig) => {
        calls.push(a[0])
        return launch(script, a, dir, sig)
      },
    }),
  ).rejects.toThrow()
  expect(calls).toEqual(["prepare"])
})

test("modified prepared proposal cannot execute", async () => {
  let work = ""
  await expect(
    executePredicted(args(), root, "s", signal(), {
      approve: async () => {
        await fs.appendFile(path.join(work, "proposal.json"), " ")
        return [[APPROVE]]
      },
      launch: async (script, a, dir, sig) => {
        work = a[2]
        return launch(script, a, dir, sig)
      },
    }),
  ).rejects.toThrow("adapter or proposal changed")
})

test.skipIf(process.env.TRP_PREDICTED_LIVE !== "1")(
  "real pinned geometry through agent execution path",
  async () => {
    const result = await executePredicted(args(), root, "engineering-synthetic-approval", signal(), {
      approve: async () => [[APPROVE]],
    })
    expect(result.status).toBe("succeeded")
    expect(await fs.readFile(result.geometry, "utf8")).toBe(
      await fs.readFile(
        path.join(checkout, "evaluation/trp/reference/predicted-geometry-20260921-corrected/geometry.csv"),
        "utf8",
      ),
    )
    if (process.env.TRP_PREDICTED_OUTPUT)
      await fs.cp(result.directory, process.env.TRP_PREDICTED_OUTPUT, { recursive: true })
  },
  180_000,
)
