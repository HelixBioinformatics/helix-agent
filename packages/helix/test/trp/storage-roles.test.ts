import { describe, expect, test } from "bun:test"
import { TrpResources as R } from "../../src/trp/resources"

const files = {
  "source.pdb": "s".repeat(4096),
  "selection.pdb": "q".repeat(4096),
  "settings.json": "{}",
  "trp_select.py": "select()",
  "trp_geometry.py": "geometry()",
  "remote_strict_policy.json": "{}",
  "catalogue_evidence.json": "reference",
}

describe("strict storage path roles and allocation phases", () => {
  test("counts distinct retained paths even when their contents are identical", () => {
    const plan = R.colocatedStorage({ ...files, "source.pdb": "same", "selection.pdb": "same" })
    expect(plan.roles.find((r) => r.file === "source.pdb")?.copies).toBe(17)
    expect(plan.roles.find((r) => r.file === "selection.pdb")?.copies).toBe(32)
    expect(plan.roles.find((r) => r.file === "settings.json")?.copies).toBe(24)
    expect(plan.roles.find((r) => r.file === "trp_select.py")?.copies).toBe(16)
    expect(plan.roles.find((r) => r.file === "trp_geometry.py")?.copies).toBe(16)
    expect(plan.roles.find((r) => r.file === "catalogue_evidence.json")?.copies).toBe(8)
  })
  test("one additional source block reserves its seventeen actual path roles", () => {
    const before = R.count(files)
    const after = R.count({ ...files, "source.pdb": files["source.pdb"] + "x" })
    expect(after.workBytes - before.workBytes).toBe(17 * 4096)
    // Equal total bundle growth in another role must not predict equal work.
    const selected = R.count({ ...files, "selection.pdb": files["selection.pdb"] + "x" })
    expect(selected.workBytes - before.workBytes).toBe(32 * 4096)
    expect(after.bundleBytes).toBe(selected.bundleBytes)
  })
  test("per-file allocation prevents many tiny files disappearing into one block", () => {
    const demand = R.count(files)
    const extra = R.count({ ...files, "extra_a.txt": "x", "extra_b.txt": "x" })
    expect(extra.workBytes - demand.workBytes).toBe(2 * 8 * 4096)
    expect(extra.storage.plan?.roles.find((r) => r.file === "extra_a.txt")?.allocatedBytesPerCopy).toBe(4096)
  })
  test("UTF8 and zero-size paths keep actual byte and block semantics", () => {
    const plan = R.colocatedStorage({ ...files, "unicode.txt": "é", "empty.txt": "" })
    expect(plan.roles.find((r) => r.file === "unicode.txt")).toEqual({ file: "unicode.txt", bytes: 2, allocatedBytesPerCopy: 4096, copies: 8 })
    expect(plan.roles.find((r) => r.file === "empty.txt")?.allocatedBytesPerCopy).toBe(0)
  })
  test("bootstrap, SQLite, cold caches, temp and portable copies remain in the maximum phase", () => {
    const demand = R.count(files), plan = demand.storage.plan!
    expect(demand.storage.profile).toBe(R.COLOCATED_STORAGE_PROFILE)
    expect(demand.storage.hardLimit).toBe(false)
    expect(plan.allowances.coldClientCacheBytes).toBeGreaterThan(0)
    expect(plan.allowances.persistentSqliteBytes).toBeGreaterThan(0)
    expect(plan.allowances.temporaryBytes).toBeGreaterThan(0)
    expect(plan.allowances.processLogPerViewBytes).toBeGreaterThan(0)
    expect(plan.phases.map((p) => p.name)).toEqual(["cold-bootstrap-and-input", "prepared-client", "remote-traversals", "retrieved-client", "packed-evidence", "portable-export"])
    expect(demand.workBytes).toBe(Math.max(...plan.phases.map((p) => p.estimatedBytes)))
    expect(plan.phases.at(-1)!.estimatedBytes).toBeGreaterThan(plan.phases.at(-2)!.estimatedBytes)
    expect(demand.workBytes % 4096).toBe(0)
  })
  test("ordinary route keeps its original twelve-MiB formula", () => {
    const { "remote_strict_policy.json": _policy, ...ordinary } = files
    const demand = R.count(ordinary)
    expect(demand.storage.profile).toBeUndefined()
    expect(demand.workBytes).toBe(Math.ceil((12 * R.MiB + 7 * demand.bundleBytes + 4 * demand.selectionBytes) / 4096) * 4096)
  })
})
