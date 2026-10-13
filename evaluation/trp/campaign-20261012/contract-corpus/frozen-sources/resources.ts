export * as TrpResources from "./resources"

import { Context, Effect, Layer, Schema } from "effect"
import { LayerNode } from "@helix/core/effect/layer-node"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { TrpSpecification as S } from "./specification"
import { TrpEnforcement } from "./enforcement"

export const VERSION = "trp-resources/1.2.0"
export const MiB = 1024 ** 2
export const Budget = Schema.Struct({
  cpus: Schema.Number,
  memoryBytes: Schema.Number,
  workBytes: Schema.Number,
  wallSeconds: Schema.Number,
  requireHardStorageLimit: Schema.Boolean,
  origin: Schema.String,
})
export type Budget = Schema.Schema.Type<typeof Budget>
export const Inventory = Schema.Struct({
  version: Schema.Literal(VERSION),
  observedAt: Schema.String,
  platform: Schema.String,
  architecture: Schema.String,
  host: Schema.String,
  workspace: Schema.String,
  filesystem: Schema.String,
  cpus: Schema.Number,
  memoryBytes: Schema.Number,
  freeBytes: Schema.Number,
  sources: Schema.Array(Schema.String),
  limitations: Schema.Array(Schema.String),
  enforcement: Schema.optional(TrpEnforcement.AllocationSchema),
})
export type Inventory = Schema.Schema.Type<typeof Inventory>
export interface Demand {
  version: string
  sourceBytes: number
  selectionBytes: number
  bundleBytes: number
  counts: { scientificTasks: number; stubTasks: number; remoteScientificCalls: number; retries: number }
  cpus: number
  memoryBytes: number
  workBytes: number
  wallSeconds: number
  storage: { kind: "estimate"; formula: string; hardLimit: false }
  assumptions: string[]
}
export interface Rejection {
  code: string
  resource: string
  demand: number | string | null
  available: number | string | null
}
export interface Decision {
  version: string
  decidedAt: string
  accepted: boolean
  inventoryHash: string | null
  budgetHash: string | null
  demand: Demand
  rejections: Rejection[]
}

/** Fixed, sequential route: input channels are not process tasks. The storage
 * formula is an engineering reservation, never a proven peak bound. */
export function count(files: Record<string, string>): Demand {
  const sourceBytes = Buffer.byteLength(files["source.pdb"])
  const selectionBytes = Buffer.byteLength(files["selection.pdb"])
  const bundleBytes = Object.values(files).reduce((n, s) => n + Buffer.byteLength(s), 0)
  return {
    version: VERSION,
    sourceBytes,
    selectionBytes,
    bundleBytes,
    counts: { scientificTasks: 2, stubTasks: 2, remoteScientificCalls: 0, retries: 0 },
    cpus: 3,
    memoryBytes: 4096 * MiB,
    workBytes: Math.ceil((12 * MiB + 7 * bundleBytes + 4 * selectionBytes) / 4096) * 4096,
    wallSeconds: 1080,
    storage: { kind: "estimate", formula: "ceil((12*1048576 + 7*bundleBytes + 4*selectionBytes)/4096)*4096", hardLimit: false },
    assumptions: [
      "Two sequential tasks per traversal; one stub traversal then one real traversal; no retry or resume.",
      "Task allocation: 2 CPUs/2 GiB. Controller allocation: 1 CPU/2 GiB; cgroup enforcement requires an independently verified operator sandbox. CPU bandwidth is not an exclusive core reservation.",
      "Each traversal has an 8 minute watchdog; probes/configuration reserve another 120 seconds. This is a configured timeout, not a runtime prediction.",
      "Storage estimates allocated workspace bytes including working copies, logs and portable evidence; an independently observed XFS project quota enforces an approved budget only inside an operator allocation.",
      "The exact image and Nextflow distribution must already be cached. Image pulls/builds and shared Docker/Nextflow caches are outside workBytes.",
      "Zero remote scientific calls applies to the offline workflow only; agent provider tokens, cost and conversation calls are not measured here.",
    ],
  }
}

export function admit(demand: Demand, rawInventory: unknown, rawBudget: unknown, now = new Date()): Decision {
  const rejections: Rejection[] = []
  const reject = (code: string, resource: string, needed: Rejection["demand"], available: Rejection["available"]) =>
    rejections.push({ code, resource, demand: needed, available })
  let inventory: Inventory | undefined, budget: Budget | undefined
  try {
    inventory = Schema.decodeUnknownSync(Inventory)(rawInventory, { onExcessProperty: "error" })
  } catch {
    reject("inventory-missing-or-invalid", "inventory", "complete observed inventory", null)
  }
  try {
    budget = Schema.decodeUnknownSync(Budget)(rawBudget, { onExcessProperty: "error" })
  } catch {
    reject("budget-missing-or-invalid", "budget", "explicit budget for review", null)
  }
  if (inventory) {
    if (
      [inventory.host, inventory.workspace, inventory.filesystem].some((v) => !v.trim()) ||
      !inventory.sources.length ||
      inventory.sources.some((v) => !v.trim())
    )
      reject("inventory-evidence-missing", "sources", "nonempty host, workspace, filesystem and sources", null)
    const age = now.getTime() - Date.parse(inventory.observedAt)
    if (!Number.isFinite(age) || age < 0 || age > 300_000)
      reject("inventory-stale", "ageMs", "0..300000", Number.isFinite(age) ? age : null)
    if (inventory.platform !== "linux") reject("platform-unsupported", "platform", "linux", inventory.platform)
    if (inventory.architecture !== "x64")
      reject("architecture-unsupported", "architecture", "x64", inventory.architecture)
    for (const [key, available] of [
      ["cpus", inventory.cpus],
      ["memoryBytes", inventory.memoryBytes],
      ["workBytes", inventory.freeBytes],
    ] as const) {
      if (!Number.isSafeInteger(available) || available < demand[key])
        reject("capacity-insufficient", key, demand[key], Number.isFinite(available) ? available : null)
    }
  }
  if (budget) {
    if (!budget.origin.trim()) reject("budget-origin-missing", "origin", "declared source", "")
    for (const key of ["cpus", "memoryBytes", "workBytes", "wallSeconds"] as const) {
      if (!Number.isSafeInteger(budget[key]) || budget[key] < demand[key])
        reject("budget-insufficient", key, demand[key], Number.isFinite(budget[key]) ? budget[key] : null)
    }
    const enforced = inventory?.enforcement as TrpEnforcement.Allocation | undefined
    if (budget.requireHardStorageLimit && !enforced)
      reject("storage-quota-unavailable", "workBytes", "enforced aggregate disk quota", "estimate only")
    if (enforced) {
      for (const key of ["cpus", "memoryBytes", "workBytes", "wallSeconds"] as const)
        if (enforced[key] > budget[key]) reject("enforcement-exceeds-budget", key, enforced[key], budget[key])
    }
  }
  return {
    version: VERSION,
    decidedAt: now.toISOString(),
    accepted: rejections.length === 0,
    inventoryHash: inventory ? S.sha256(S.canonical(inventory)) : null,
    budgetHash: budget ? S.sha256(S.canonical(budget)) : null,
    demand,
    rejections,
  }
}

/** Read-only host snapshot, using the same MemAvailable convention as Environment.
 * No caller may submit invented host capacity through the agent tool. */
export async function observe(workspace: string): Promise<Inventory> {
  const enforced = await TrpEnforcement.observe(workspace)
  const memory = await fs.readFile("/proc/meminfo", "utf8")
  const available = memory.match(/^MemAvailable:\s+(\d+) kB$/m)
  if (!available) throw new S.WorkflowError("inventory-unavailable", "Linux MemAvailable is unreadable")
  const stat = await fs.statfs(workspace)
  let cpus = os.availableParallelism(), memoryBytes = Number(available[1]) * 1024
  const cgroupSources: string[] = []
  if (!enforced) {
    const membership = (await fs.readFile("/proc/self/cgroup", "utf8")).match(/^0::([^\n]+)$/m)
    if (!membership) throw new S.WorkflowError("inventory-unavailable", "Unified cgroup membership unavailable")
    let current = path.resolve("/sys/fs/cgroup", "." + membership[1])
    if (!current.startsWith("/sys/fs/cgroup")) throw new S.WorkflowError("inventory-unavailable", "Cgroup path outside mount")
    for (;;) {
      const cpu = await fs.readFile(path.join(current, "cpu.max"), "utf8").catch(() => "max 100000")
      const [quota, period] = cpu.trim().split(/\s+/)
      if (quota !== "max") cpus = Math.min(cpus, Math.floor(Number(quota) / Number(period)))
      const max = await fs.readFile(path.join(current, "memory.max"), "utf8").catch(() => "max")
      if (max.trim() !== "max") {
        const used = Number(await fs.readFile(path.join(current, "memory.current"), "utf8"))
        memoryBytes = Math.min(memoryBytes, Math.max(0, Number(max) - used))
      }
      cgroupSources.push(current + ":cpu.max,memory.max,memory.current")
      if (current === "/sys/fs/cgroup") break
      current = path.dirname(current)
    }
  }
  return {
    version: VERSION,
    observedAt: new Date().toISOString(),
    platform: os.platform(),
    architecture: os.arch(),
    host: os.hostname(),
    workspace: await fs.realpath(workspace),
    filesystem: String(stat.type),
    cpus: enforced?.config.cpus ?? cpus,
    memoryBytes: enforced?.config.memoryBytes ?? memoryBytes,
    freeBytes: enforced?.config.workBytes ?? stat.bavail * stat.bsize,
    ...(enforced ? { enforcement: enforced.config } : {}),
    sources: enforced ? ["root supervisor: XFS project quota", "/proc/self/cgroup", "cgroup v2 cpu.max/memory.max/memory.min/memory.swap.max"] : ["os.availableParallelism", "/proc/meminfo:MemAvailable", "fs.statfs:bavail*bsize", ...cgroupSources],
    limitations: enforced ? [
      "Dedicated allocation entitlement; current usage is recorded separately, not subtracted from the total-run budget during rechecks.",
      "CPU bandwidth limits do not promise exclusive cores. Kernel memory protection is not a performance guarantee.",
      "Preloaded software/image caches, shared Docker daemon and external supervisor records are infrastructure outside workBytes.",
    ] : [
      "Host capacity clipped to inherited cgroup limits/headroom; not an exclusive allocation. Shared loads can change it.",
      "Local Docker daemon/image and Nextflow version are separately checked before task launch. Remote Docker is rejected.",
      "GPU not required; cluster access unconfirmed and unsupported by this route; aggregate disk quota unavailable.",
    ],
  }
}
export class Service extends Context.Service<Service, { observe: (workspace: string) => Effect.Effect<Inventory> }>()(
  "@helix/TrpResources",
) {}
export const node = LayerNode.make({
  service: Service,
  layer: Layer.succeed(Service, { observe: (workspace) => Effect.promise(() => observe(workspace)) }),
  deps: [],
})
