import { test, expect } from "bun:test"
import { Effect, Exit } from "effect"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { TrpRemote as Remote } from "../../src/trp/remote"
import { TrpResources as R } from "../../src/trp/resources"
import { TrpSpecification as S } from "../../src/trp/specification"

const target: Remote.Target = {
  config: {
    version: Remote.VERSION,
    host: "192.0.2.1",
    port: 22,
    user: "ubuntu",
    identityFile: "/private/key",
    knownHostsFile: "/private/hosts",
    hostKeyAlias: "test",
    root: "/shared/helix",
    partition: "helix",
  },
  fingerprint: "f".repeat(64),
  public: { version: Remote.VERSION, root: "/shared/helix", fingerprint: "f".repeat(64) },
}
const base = {
  files: {
    "source.pdb": "synthetic fixture",
    "selection.pdb": "synthetic fixture",
    "execution.json": '{"engine":"trp-nextflow/1.4.0"}',
  },
  digest: "f".repeat(64),
  spec: {} as any,
  report: {} as any,
  image: "sha256:" + "f".repeat(64),
}
const budget = {
  cpus: 3,
  memoryBytes: 4096 * R.MiB,
  workBytes: 256 * R.MiB,
  wallSeconds: 1080,
  requireHardStorageLimit: false,
  origin: "isolated observer-repair regression, not experiment evidence",
}
const response = (value: unknown, code = 0, stderr = "") => ({
  command: "mocked SSH transport",
  exitCode: code,
  stdout: Buffer.from(value === undefined ? "" : JSON.stringify(value)),
  stderr: Buffer.from(stderr),
  stdoutTruncated: false,
  stderrTruncated: false,
})

async function scenario(failures: number, message: string, approvedSignal?: AbortController) {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "helix-status-repair-case-"))
  const actions: string[] = [],
    logs: any[] = []
  let probes = 0
  const bundle = structuredClone(base)
  const runProcess = (_command: any, options: any) =>
    Effect.gen(function* () {
      const req = JSON.parse(String(options.stdin))
      actions.push(req.action)
      if (req.action === "start") return response({ ok: true, controller: {}, directory: "/fixture" })
      if (req.action === "status") {
        probes++
        if (approvedSignal && probes === 1) approvedSignal.abort(new Error("Approved cancellation"))
        if (probes <= failures) return response(undefined, 255, message)
        return response({ ok: true, status: "succeeded", controllerAlive: false })
      }
      if (req.action === "cancel")
        return response({ ok: true, confirmed: true, controllerStopped: true, remaining: [] })
      if (req.action === "export")
        return response({
          ok: true,
          files: Object.entries(bundle.files).map(([path, content]) => ({
            path,
            bytes: Buffer.byteLength(content),
            sha256: S.sha256(content),
            base64: Buffer.from(content).toString("base64"),
          })),
        })
      throw new Error("Unexpected action " + req.action)
    })
  try {
    const result = await Effect.runPromise(
      Remote.execute(
        target,
        bundle,
        dir,
        "11111111-1111-1111-1111-111111111111",
        budget,
        runProcess,
        approvedSignal?.signal ?? new AbortController().signal,
        async (outcome, detail) => {
          logs.push({ outcome, detail: JSON.parse(S.canonical(detail)) })
        },
      ).pipe(Effect.exit),
    )
    return { result, actions, probes, logs }
  } finally {
    await fs.rm(dir, { recursive: true, force: true })
  }
}

test("one transient status reset recovers same controller with zero scientific resubmissions", async () => {
  const value = await scenario(1, "kex_exchange_identification: read: Connection reset by peer\r\n")
  expect(Exit.isSuccess(value.result)).toBe(true)
  expect(value.actions).toEqual(["start", "status", "status", "export"])
  expect(value.logs.find((r) => r.outcome === "remote-monitor-error").detail.diagnostic.stderr).toContain(
    "Connection reset",
  )
})

test("two transient status resets remain bounded and do not cancel a recovered controller", async () => {
  const value = await scenario(2, "Connection closed by 192.0.2.1 port 22")
  expect(Exit.isSuccess(value.result)).toBe(true)
  expect(value.probes).toBe(3)
  expect(value.actions.filter((r) => r === "start")).toHaveLength(1)
  expect(value.actions).not.toContain("cancel")
})

test("persistent transport failure keeps JSON-safe unknown terminal and primary diagnostic", async () => {
  const value = await scenario(10, "Connection reset by peer")
  expect(Exit.isFailure(value.result)).toBe(true)
  expect(String((value.result as any).cause)).toContain("SSH action status")
  expect(String((value.result as any).cause)).not.toContain("finite JSON")
  expect(value.probes).toBe(3)
  expect(value.actions.filter((r) => r === "start")).toHaveLength(1)
  expect(value.actions).toContain("cancel")
  expect(value.actions).toContain("export")
  expect(value.logs.find((r) => r.outcome === "remote-failed-or-cancelled").detail.terminal).toBeNull()
})

test("host-key and authentication errors are never retried", async () => {
  for (const message of [
    "Host key verification failed.",
    "Permission denied (publickey).",
    "REMOTE HOST IDENTIFICATION HAS CHANGED!",
    "",
  ]) {
    const value = await scenario(10, message)
    expect(Exit.isFailure(value.result)).toBe(true)
    expect(value.probes).toBe(1)
    expect(value.actions.filter((r) => r === "start")).toHaveLength(1)
  }
})

test("an explicit abort bypasses status retries and cleans up owned jobs", async () => {
  const value = await scenario(10, "Connection reset by peer", new AbortController())
  expect(Exit.isFailure(value.result)).toBe(true)
  expect(value.probes).toBe(1)
  expect(value.actions).toContain("cancel")
})
