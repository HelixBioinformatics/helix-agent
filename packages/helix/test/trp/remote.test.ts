import { describe, expect, test } from "bun:test"
import { Effect, Exit, Fiber } from "effect"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { TrpRemote as Remote } from "../../src/trp/remote"
import { TrpNextflow as N } from "../../src/trp/nextflow"
import { TrpResources as R } from "../../src/trp/resources"
import { TrpSpecification as S } from "../../src/trp/specification"
import type { AppProcess } from "@helix/core/process"
import { inventory } from "./resource-fixture"
import budget from "../../../../evaluation/trp/development/f4-budget.json"

function target(): Remote.Target {
  return {
    config: {
      version: Remote.VERSION,
      host: "192.0.2.1",
      port: 22,
      user: "ubuntu",
      identityFile: "/private/key",
      knownHostsFile: "/private/hosts",
      hostKeyAlias: "host1",
      root: "/shared/helix",
      partition: "helix",
      selectNode: "worker1",
      geometryNode: "worker2",
      numericalProfile: "haswell-single-thread",
    },
    fingerprint: "f".repeat(64),
    public: { version: Remote.VERSION, root: "/shared/helix", partition: "helix", fingerprint: "f".repeat(64) },
  }
}
function fixture(): N.Bundle {
  return {
    spec: {
      graph: {
        nodes: [
          { id: "select", operation: "pdb.select" },
          { id: "geometry", operation: "geometre.geometry" },
        ],
      },
    } as any,
    report: {} as any,
    files: {
      "source.pdb": "source",
      "selection.pdb": "selection",
      "nextflow.config": "process.executor = 'local'\n--cpus 2 --tmpfs\n",
      "execution.json": '{"engine":"trp-nextflow/1.4.0"}',
      "trp_select.py": "print('select')\n",
      "trp_geometry.py": "print('geometry')\n",
    },
    digest: "",
    image: "sha256:" + "a".repeat(64),
  }
}
function remoteInventory() {
  return {
    ...inventory(),
    remote: {
      version: Remote.VERSION,
      fingerprint: "f".repeat(64),
      partition: "helix",
      controllerCpus: 2,
      controllerMemoryBytes: 3 * 1024 ** 3,
      secondsRemaining: 3600,
      requiredNodes: ["worker1", "worker2"],
      nodes: ["worker1", "worker2"].map((name) => ({
        name,
        cpus: 2,
        memoryBytes: 7 * 1024 ** 3,
        eligible: true,
        state: "IDLE",
        source: "observed fixture",
      })),
    },
  }
}
const result = (value: unknown) => ({
  command: "ssh fixture",
  exitCode: 0,
  stdout: Buffer.from(JSON.stringify(value)),
  stderr: Buffer.alloc(0),
  stdoutTruncated: false,
  stderrTruncated: false,
})

describe("TRP remote infrastructure admission", () => {
  test("Slurm topology and exact runtime code enter the approval digest", () => {
    const bundle = fixture()
    Remote.bind(bundle, target(), "11111111-1111-1111-1111-111111111111")
    const digest = N.bundleDigest(bundle.files)
    expect(bundle.files["nextflow.config"]).toContain("process.executor = 'slurm'")
    expect(bundle.files["nextflow.config"]).toContain("--comment=helix:11111111")
    expect(bundle.files["nextflow.config"]).toContain("--memory=2g --memory-swap=2g")
    expect(bundle.files["nextflow.config"]).toContain("env.OPENBLAS_CORETYPE = 'Haswell'")
    expect(bundle.files["trp_geometry.py"]).toContain("threadpool_info")
    expect(bundle.files["remote_runner.py"]).toContain("Slurm controller")
    bundle.files["remote_target.json"] += " "
    expect(N.bundleDigest(bundle.files)).not.toBe(digest)
  })
  test("per-worker memory cannot be pooled to admit a task", () => {
    const bundle = fixture()
    Remote.bind(bundle, target(), "11111111-1111-1111-1111-111111111111")
    const observed = remoteInventory()
    observed.remote.nodes.forEach((n) => (n.memoryBytes = 1024 ** 3))
    const decision = R.admit(R.count(bundle.files), observed, budget)
    expect(decision.accepted).toBe(false)
    expect(decision.rejections.some((r) => r.code === "remote-worker-insufficient")).toBe(true)
  })
  test("a depleted required worker is refused even if another worker could fit", () => {
    const observed = remoteInventory()
    observed.remote.nodes[1].cpus = 1
    expect(
      R.admit(R.count(fixture().files), observed, budget).rejections.some(
        (r) => r.code === "remote-placement-insufficient",
      ),
    ).toBe(true)
  })
  test("controller and session capacity are separate admission requirements", () => {
    const observed = remoteInventory()
    observed.remote.controllerMemoryBytes = 1024 ** 3
    observed.remote.secondsRemaining = 500
    const decision = R.admit(R.count(fixture().files), observed, budget)
    expect(decision.rejections.map((r) => r.code)).toContain("remote-controller-insufficient")
    expect(decision.rejections.map((r) => r.code)).toContain("remote-session-insufficient")
  })
  test("operator config rejects permissive credentials and binds SSH trust", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "helix-remote-"))
    const previous = process.env.HELIX_TRP_REMOTE
    try {
      const config = {
        ...target().config,
        identityFile: path.join(directory, "key"),
        knownHostsFile: path.join(directory, "hosts"),
      }
      await fs.writeFile(config.identityFile, "synthetic private fixture", { mode: 0o600 })
      await fs.writeFile(config.knownHostsFile, "synthetic pinned host fixture", { mode: 0o600 })
      const file = path.join(directory, "operator.json")
      await fs.writeFile(file, JSON.stringify(config), { mode: 0o600 })
      process.env.HELIX_TRP_REMOTE = file
      const first = (await Remote.configured())!
      await fs.appendFile(config.knownHostsFile, " changed")
      expect((await Remote.configured())!.fingerprint).not.toBe(first.fingerprint)
      await fs.chmod(config.identityFile, 0o644)
      await expect(Remote.configured()).rejects.toThrow("owner-controlled")
    } finally {
      if (previous === undefined) delete process.env.HELIX_TRP_REMOTE
      else process.env.HELIX_TRP_REMOTE = previous
      await fs.rm(directory, { recursive: true, force: true })
    }
  })
})

describe("TRP remote transfer and lifecycle", () => {
  test("fiber interruption runs owner-scoped native cancellation", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "helix-remote-interrupt-"))
    const actions: string[] = []
    const bundle = fixture()
    bundle.digest = "f".repeat(64)
    let started!: () => void
    const ready = new Promise<void>((resolve) => (started = resolve))
    const runProcess: AppProcess.Interface["run"] = (_command, options) =>
      Effect.gen(function* () {
        const req = JSON.parse(String(options?.stdin))
        actions.push(req.action)
        if (req.action === "start") {
          started()
          return result({ ok: true, directory: "/fixture", controller: {} })
        }
        if (req.action === "status") return yield* Effect.never
        if (req.action === "cancel") return result({ ok: true, confirmed: true, controllerStopped: true })
        return result({
          ok: true,
          files: Object.entries(bundle.files).map(([path, bytes]) => ({
            path,
            bytes: Buffer.byteLength(bytes),
            sha256: S.sha256(bytes),
            base64: Buffer.from(bytes).toString("base64"),
          })),
        })
      })
    try {
      await Effect.runPromise(
        Effect.gen(function* () {
          const fiber = yield* Remote.execute(
            target(),
            bundle,
            directory,
            "11111111-1111-1111-1111-111111111111",
            budget,
            runProcess,
            new AbortController().signal,
            async () => {},
          ).pipe(Effect.forkScoped)
          yield* Effect.promise(() => ready)
          yield* Fiber.interrupt(fiber)
        }).pipe(Effect.scoped),
      )
      expect(actions).toContain("cancel")
      expect(actions).toContain("export")
      expect(JSON.parse(await fs.readFile(path.join(directory, "remote-cancellation.json"), "utf8")).confirmed).toBe(
        true,
      )
    } finally {
      await fs.rm(directory, { recursive: true, force: true })
    }
  })
  test("retrieval refuses escaped filenames, wrong bytes and changed approved inputs", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "helix-import-"))
    try {
      const bundle = fixture()
      const file = { path: "../outside", bytes: 1, sha256: S.sha256("x"), base64: Buffer.from("x").toString("base64") }
      await expect(Remote.importExport(bundle, directory, { files: [file] })).rejects.toThrow("../outside")
      file.path = "source.pdb"
      file.sha256 = "0".repeat(64)
      await expect(Remote.importExport(bundle, directory, { files: [file] })).rejects.toThrow("source.pdb")
      file.sha256 = S.sha256("x")
      await expect(Remote.importExport(bundle, directory, { files: [file] })).rejects.toThrow("source.pdb")
    } finally {
      await fs.rm(directory, { recursive: true, force: true })
    }
  })
  for (const mode of ["ssh-status-lost", "native-failure", "abort", "analysis-rejected"]) {
    test(`${mode} cancels owned jobs and retrieves evidence without resubmission`, async () => {
      const directory = await fs.mkdtemp(path.join(os.tmpdir(), "helix-remote-run-"))
      const actions: string[] = []
      const controller = new AbortController()
      const bundle = fixture()
      bundle.digest = "f".repeat(64)
      bundle.files["admission.json"] = JSON.stringify({ demand: R.count(bundle.files) })
      const runProcess: AppProcess.Interface["run"] = (_command, options) =>
        Effect.gen(function* () {
          const req = JSON.parse(String(options?.stdin))
          actions.push(req.action)
          if (req.action === "start") {
            if (mode === "abort") controller.abort(new Error("User cancelled fixture"))
            return result({ ok: true, directory: "/shared/helix/run", controller: { pid: 1 } })
          }
          if (req.action === "status") {
            if (mode === "ssh-status-lost") return yield* Effect.die(new Error("Transport disconnected fixture"))
            if (mode === "analysis-rejected")
              return result({
                ok: true,
                status: "running",
                controllerAlive: true,
                analysisAdmitted: false,
                analysisInventory: {
                  ...remoteInventory(),
                  remote: { ...remoteInventory().remote, controllerMemoryBytes: 1 },
                },
              })
            return result({ ok: true, status: "failed", error: "Native job failed fixture", controllerAlive: false })
          }
          if (req.action === "cancel")
            return result({ ok: true, confirmed: true, remaining: [], controllerStopped: true })
          return result({
            ok: true,
            files: Object.entries(bundle.files).map(([path, bytes]) => ({
              path,
              bytes: Buffer.byteLength(bytes),
              sha256: S.sha256(bytes),
              base64: Buffer.from(bytes).toString("base64"),
            })),
          })
        })
      try {
        const exit = await Effect.runPromise(
          Remote.execute(
            target(),
            bundle,
            directory,
            "11111111-1111-1111-1111-111111111111",
            budget,
            runProcess,
            controller.signal,
            async () => {},
          ).pipe(Effect.exit),
        )
        expect(Exit.isFailure(exit)).toBe(true)
        expect(actions.filter((a) => a === "start")).toHaveLength(1)
        expect(actions).toContain("cancel")
        expect(actions).toContain("export")
        expect(actions).not.toContain("admit-analysis")
        expect(JSON.parse(await fs.readFile(path.join(directory, "remote-cancellation.json"), "utf8")).confirmed).toBe(
          true,
        )
      } finally {
        await fs.rm(directory, { recursive: true, force: true })
      }
    })
  }
})
