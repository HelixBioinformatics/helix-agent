export * as TrpEnforcement from "./enforcement"

import fs from "node:fs/promises"
import path from "node:path"
import { TrpSpecification as S } from "./specification"
import { Schema } from "effect"

export const AllocationSchema = Schema.Struct({
  version: Schema.Literal("trp-sandbox/1.0.0"), id: Schema.String, workspace: Schema.String,
  device: Schema.Number, projectId: Schema.Number, workBytes: Schema.Number, cpus: Schema.Number,
  memoryBytes: Schema.Number, aggregate: Schema.String, tasks: Schema.String, dockerParent: Schema.String,
  controller: Schema.String, controllerCpus: Schema.Number, controllerMemoryBytes: Schema.Number,
  controllerMemoryMin: Schema.Number, wallSeconds: Schema.Number, supervisorSha256: Schema.String,
})

export interface Allocation {
  version: "trp-sandbox/1.0.0"
  id: string
  workspace: string
  device: number
  projectId: number
  workBytes: number
  cpus: number
  memoryBytes: number
  aggregate: string
  tasks: string
  dockerParent: string
  controller: string
  controllerCpus: number
  controllerMemoryBytes: number
  controllerMemoryMin: number
  wallSeconds: number
  supervisorSha256: string
}
export interface Observed {
  config: Allocation
  sample: { observedAt: number; quota: { usedBytes: number; hardBytes: number }; [key: string]: unknown }
}

function fail(message: string): never {
  throw new S.WorkflowError("resource-enforcement-unverified", message)
}

/** Operator state is a pointer to evidence, not permission to invent capacity.
 * Check root ownership, freshness, filesystem identity and the running cgroups.
 * The agent tool has no argument capable of constructing this allocation. */
export async function observe(workspace: string): Promise<Observed | undefined> {
  const pointer = process.env.HELIX_TRP_SANDBOX
  if (!pointer) return undefined
  if (!/^\/run\/trp-sandbox\/trp[0-9a-f]{16}\.json$/.test(pointer)) fail("Invalid supervisor state path")
  for (const target of ["/run/trp-sandbox", pointer]) {
    const stat = await fs.lstat(target)
    if (stat.uid !== 0 || stat.mode & 0o022 || stat.isSymbolicLink()) fail("Supervisor state is not root controlled")
  }
  const state = Schema.decodeUnknownSync(Schema.Struct({
    config: AllocationSchema,
    sample: Schema.Struct({ observedAt: Schema.Number,
      quota: Schema.Struct({ usedBytes: Schema.Number, hardBytes: Schema.Number }) }),
  }))(JSON.parse(await fs.readFile(pointer, "utf8")))
  const c = Schema.decodeUnknownSync(AllocationSchema)(state.config, { onExcessProperty: "error" })
  if (!c || c.version !== "trp-sandbox/1.0.0" || !/^trp[0-9a-f]{16}$/.test(c.id)) fail("Unknown allocation")
  if (c.aggregate !== `${c.id}.slice` || c.dockerParent !== `${c.id}-tasks.slice` ||
      c.tasks !== `${c.aggregate}/${c.dockerParent}` || c.controller !== `${c.aggregate}/${c.id}-controller.service`)
    fail("Invalid cgroup hierarchy")
  if (c.cpus !== 3 || c.memoryBytes !== 4096 * 1024 ** 2 || c.controllerCpus !== 1 ||
      c.controllerMemoryBytes !== 2048 * 1024 ** 2 || c.controllerMemoryMin !== c.controllerMemoryBytes ||
      !Number.isSafeInteger(c.workBytes) || c.workBytes <= 0 || c.projectId !== 42)
    fail("Unsupported allocation bounds")
  const real = await fs.realpath(workspace), root = await fs.realpath(c.workspace)
  if (root !== c.workspace || (real !== root && !real.startsWith(root + path.sep))) fail("Workspace outside quota")
  if ((await fs.stat(real)).dev !== c.device || (await fs.statfs(real)).type !== 0x58465342)
    fail("XFS allocation identity changed")
  const age = Date.now() / 1000 - state.sample.observedAt
  if (!Number.isFinite(age) || age < -1 || age > 5 || state.sample.quota.hardBytes !== c.workBytes)
    fail("Quota observation stale or changed")
  const membership = (await fs.readFile("/proc/self/cgroup", "utf8")).trim()
  if (membership !== `0::/${c.controller}`) fail("Controller outside allocated cgroup")
  for (const [group, cpus, memory] of [
    [c.aggregate, 3, c.memoryBytes], [c.controller, 1, c.controllerMemoryBytes],
    [c.tasks, 2, 2048 * 1024 ** 2],
  ] as const) {
    const base = `/sys/fs/cgroup/${group}`
    const cpu = (await fs.readFile(`${base}/cpu.max`, "utf8")).trim().split(/\s+/).map(Number)
    if (cpu.length !== 2 || cpu[0] / cpu[1] !== cpus) fail("CPU limit changed")
    for (const [key, value] of [["memory.max", memory], ["memory.min", memory], ["memory.swap.max", 0]] as const)
      if (Number((await fs.readFile(`${base}/${key}`, "utf8")).trim()) !== value) fail(`${key} changed`)
  }
  return state
}

export function dockerOptions(c: Allocation): string {
  return ` --cgroup-parent=${c.dockerParent} --label=trp.sandbox=${c.id} --memory-swap=2g --log-driver=none`
}

/** One preparation per allocation. A replacement receives a fresh sandbox;
 * abandoned proposals cannot invisibly spend the next proposal's quota. */
export async function claim(c: Allocation): Promise<void> {
  const handle = await fs.open(path.join(c.workspace, ".trp-allocation-claim"), "wx", 0o600)
  await handle.writeFile("One reviewed composition per resource allocation\n")
  await handle.close()
}
