export * as TrpRemoteEnforcement from "./remote-enforcement"

import fs from "node:fs/promises"
import path from "node:path"
import { Schema } from "effect"
import { TrpSpecification as S } from "./specification"
import CHECKER from "./remote_strict.py.txt"

export const VERSION = "trp-remote-strict/1.0.0"
export const BACKEND = "trp-slurm-colocated-strict/1.0.0"
export const checkerPath = "/usr/local/libexec/helix-remote-strict-check.py"
export const checkerSha256 = S.sha256(CHECKER)

export const Policy = Schema.Struct({
  version: Schema.Literal(VERSION),
  id: Schema.String,
  uid: Schema.Number,
  hostname: Schema.String,
  bootId: Schema.String,
  target: Schema.Record(Schema.String, Schema.Union([Schema.String, Schema.Number])),
  filesystem: Schema.Struct({
    mountPoint: Schema.String,
    uuid: Schema.String,
    device: Schema.Number,
    projectId: Schema.Number,
    hardBytes: Schema.Number,
  }),
  paths: Schema.Struct({
    allocationRoot: Schema.String,
    clientWorkspace: Schema.String,
    temporaryRoot: Schema.String,
    exportRoot: Schema.String,
    clientStateRoot: Schema.String,
    clientCacheRoot: Schema.String,
    remoteRoot: Schema.String,
  }),
  controller: Schema.Struct({
    cgroup: Schema.String,
    cpus: Schema.Number,
    memoryBytes: Schema.Number,
    swapBytes: Schema.Number,
  }),
  entitlement: Schema.Struct({
    cpus: Schema.Number,
    memoryBytes: Schema.Number,
    workBytes: Schema.Number,
    wallSeconds: Schema.Number,
  }),
  checker: Schema.Struct({ path: Schema.String, sha256: Schema.String }),
  samplePath: Schema.String,
})
export type Policy = Schema.Schema.Type<typeof Policy>
export const Allocation = Schema.Struct({
  version: Schema.Literal(VERSION),
  policyPath: Schema.String,
  policySha256: Schema.String,
  policy: Policy,
  targetFingerprint: Schema.String,
})
export type Allocation = Schema.Schema.Type<typeof Allocation>
export interface Receipt {
  ok: true
  policy: Policy
  policySha256: string
  sampleSha256: string
  observedAt: number
  transport: "co-located-python"
  entitlement: Policy["entitlement"]
  quota: { usedBytes: number; hardBytes: number }
  [key: string]: unknown
}

/** A receipt is structured source evidence, never a yes/no enforcement flag.
 * Live observe() additionally checks the root-owned files and actual kernel. */
export function validateReceipt(raw: unknown, allocated: Allocation, now = Date.now() / 1000): boolean {
  try {
    const r = raw as any,
      p = allocated.policy
    if (
      !r ||
      r.version !== VERSION ||
      r.policySha256 !== allocated.policySha256 ||
      S.canonical(r.policy) !== S.canonical(p) ||
      S.sha256(r.policyRaw) !== allocated.policySha256 ||
      S.canonical(JSON.parse(r.policyRaw)) !== S.canonical(p) ||
      S.sha256(r.sampleRaw) !== r.sampleSha256 ||
      r.transport !== "co-located-python" ||
      r.host !== p.hostname ||
      r.membership !== "0::/" + p.controller.cgroup ||
      r.currentUsageIsSubtractedFromEntitlement !== false ||
      S.canonical(r.entitlement) !== S.canonical(p.entitlement)
    )
      return false
    const sample = JSON.parse(r.sampleRaw)
    if (
      sample.version !== "trp-remote-strict-sample/1.0.0" ||
      sample.policySha256 !== allocated.policySha256 ||
      sample.bootId !== p.bootId ||
      !Number.isFinite(r.checkedAt) ||
      !Number.isFinite(sample.observedAt) ||
      r.checkedAt - sample.observedAt < -1 ||
      r.checkedAt - sample.observedAt > 5 ||
      now - r.checkedAt < -1 ||
      now - r.checkedAt > 5
    )
      return false
    const cpu = r.cgroup["cpu.max"].trim().split(/\s+/).map(Number)
    if (
      cpu.length !== 2 ||
      cpu[0] !== cpu[1] ||
      cpu[0] <= 0 ||
      r.cgroup["memory.max"] !== "2147483648" ||
      r.cgroup["memory.swap.max"] !== "0"
    )
      return false
    if (r.role !== "client" && r.role !== "controller") return false
    const cwd = r.role === "client" ? p.paths.clientWorkspace : p.paths.remoteRoot
    if (
      (r.cwd !== cwd && !r.cwd.startsWith(cwd + path.sep)) ||
      (r.role === "client" && r.parentMembership !== r.membership)
    )
      return false
    if (
      !Array.isArray(r.paths) ||
      r.paths.length !== Object.keys(p.paths).length ||
      new Set(r.paths.map((v: any) => v.name)).size !== r.paths.length
    )
      return false
    for (const row of r.paths)
      if (
        row.path !== (p.paths as Record<string, string>)[row.name] ||
        row.device !== p.filesystem.device ||
        row.projectId !== p.filesystem.projectId ||
        row.inherit !== true
      )
        return false
    const q = sample.quota
    const lines = q.reportSource.match(
      new RegExp("^#?" + p.filesystem.projectId + "\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s", "m"),
    )
    if (
      !lines ||
      Number(lines[1]) * 1024 !== q.usedBytes ||
      Number(lines[3]) * 1024 !== q.hardBytes ||
      q.projectId !== p.filesystem.projectId ||
      q.hardBytes !== p.filesystem.hardBytes ||
      r.quota.hardBytes !== q.hardBytes ||
      r.quota.usedBytes !== q.usedBytes ||
      !q.stateSource.includes("Accounting: ON") ||
      !q.stateSource.includes("Enforcement: ON") ||
      q.treeCheckExitCode !== 0 ||
      q.treeCheckStdout.trim() ||
      q.treeCheckStderr.trim()
    )
      return false
    return true
  } catch {
    return false
  }
}

function fail(message: string): never {
  throw new S.WorkflowError("remote-strict-unverified", message)
}

async function rootOwned(file: string, directory = false): Promise<void> {
  const stat = await fs.lstat(file)
  if (
    stat.uid !== 0 ||
    stat.mode & 0o022 ||
    stat.isSymbolicLink() ||
    (directory ? !stat.isDirectory() : !stat.isFile()) ||
    (await fs.realpath(file)) !== file
  )
    fail("Strict operator policy/checker must be ordinary root-controlled files")
}

/** Both the root policy and Linux checks are required; no model-facing flag can
 * create this allocation. The checker is read-only and pinned in this module. */
export async function observe(
  policyPath: string,
  target: Record<string, unknown>,
  expectedSha?: string,
): Promise<Receipt> {
  if (!/^\/run\/helix-remote-strict\/hrs[0-9a-f]{16}\.json$/.test(policyPath))
    fail("Invalid immutable remote policy path")
  await rootOwned("/run/helix-remote-strict", true)
  await rootOwned(policyPath)
  await rootOwned(path.dirname(checkerPath), true)
  await rootOwned(checkerPath)
  const raw = await fs.readFile(policyPath)
  const policySha256 = S.sha256(raw)
  if (expectedSha && expectedSha !== policySha256) fail("Remote allocation changed during review")
  const policy = Schema.decodeUnknownSync(Policy)(JSON.parse(raw.toString()), { onExcessProperty: "error" })
  if (
    policy.checker.path !== checkerPath ||
    policy.checker.sha256 !== checkerSha256 ||
    S.sha256(await fs.readFile(checkerPath)) !== checkerSha256
  )
    fail("Installed root checker differs from approved code")
  const child = Bun.spawn(["/usr/bin/python3", checkerPath], {
    stdin: new Blob([S.canonical({ policyPath, target, policySha256, role: "client" })]),
    stdout: "pipe",
    stderr: "pipe",
    env: process.env,
  })
  const timer = setTimeout(() => child.kill(), 15_000)
  let receipt: Receipt
  try {
    const [code, out, err] = await Promise.all([
      child.exited,
      new Response(child.stdout).text(),
      new Response(child.stderr).text(),
    ])
    if (code !== 0 || err.trim()) fail("Kernel/root policy verification failed: " + out.slice(-4096) + err.slice(-1024))
    receipt = JSON.parse(out)
  } finally {
    clearTimeout(timer)
  }
  if (
    !receipt.ok ||
    receipt.policySha256 !== policySha256 ||
    S.canonical(receipt.policy) !== S.canonical(policy) ||
    receipt.transport !== "co-located-python" ||
    receipt.quota.hardBytes !== policy.filesystem.hardBytes
  )
    fail("Kernel receipt differs from fixed operator policy")
  if (!validateReceipt(receipt, allocation(policyPath, receipt, ""))) fail("Kernel receipt sources or limits differ")
  return receipt
}

export function allocation(policyPath: string, receipt: Receipt, targetFingerprint: string): Allocation {
  return { version: VERSION, policyPath, policySha256: receipt.policySha256, policy: receipt.policy, targetFingerprint }
}

export async function claim(allocated: Allocation): Promise<void> {
  const file = await fs.open(
    path.join(allocated.policy.paths.allocationRoot, ".helix-remote-strict-claim"),
    "wx",
    0o600,
  )
  await file.writeFile("One reviewed composition per co-located remote strict allocation\n")
  await file.close()
}

export const checkerSource = CHECKER
