import { describe, expect, test } from "bun:test"
import fs from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { TrpRemoteEnforcement as H } from "../../src/trp/remote-enforcement"
import { TrpRemote as Remote } from "../../src/trp/remote"
import { TrpResources as R } from "../../src/trp/resources"
import { TrpNextflow as N } from "../../src/trp/nextflow"
import { TrpSpecification as S } from "../../src/trp/specification"
import { inventory } from "./resource-fixture"
const policySource = {
  version: "trp-remote-strict/1.0.0",
  id: "hrs0123456789abcdef",
  uid: 1000,
  hostname: "helix-head",
  bootId: "REPLACE_WITH_PROC_BOOT_ID",
  target: {
    host: "127.0.0.1",
    port: 22,
    user: "ubuntu",
    hostKeyAlias: "helix-lab2",
    root: "/shared/helix-strict/allocation/remote",
    partition: "helix",
    selectNode: "helix-worker1",
    geometryNode: "helix-worker2",
    numericalProfile: "haswell-single-thread",
  },
  filesystem: {
    mountPoint: "/shared/helix-strict",
    uuid: "REPLACE_XFS_UUID",
    device: 0,
    projectId: 142,
    hardBytes: 67108864,
  },
  paths: {
    allocationRoot: "/shared/helix-strict/allocation",
    clientWorkspace: "/shared/helix-strict/allocation/client",
    temporaryRoot: "/shared/helix-strict/allocation/tmp",
    exportRoot: "/shared/helix-strict/allocation/export",
    clientStateRoot: "/shared/helix-strict/allocation/state",
    clientCacheRoot: "/shared/helix-strict/allocation/cache",
    remoteRoot: "/shared/helix-strict/allocation/remote",
  },
  controller: {
    cgroup: "helix-strict-hrs0123456789abcdef.service",
    cpus: 1,
    memoryBytes: 2147483648,
    swapBytes: 0,
  },
  entitlement: {
    cpus: 3,
    memoryBytes: 4294967296,
    workBytes: 67108864,
    wallSeconds: 1080,
  },
  checker: {
    path: "/usr/local/libexec/helix-remote-strict-check.py",
    sha256: "REPLACE_WITH_FINAL_CHECKER_SHA256",
  },
  samplePath: "/run/helix-remote-strict/hrs0123456789abcdef.sample.json",
}
import budget from "../../../../evaluation/trp/development/f4-budget.json"

function allocation(): H.Allocation {
  const policy = {
    ...structuredClone(policySource),
    checker: { ...policySource.checker, sha256: H.checkerSha256 },
  } as H.Policy
  return {
    version: H.VERSION,
    policyPath: "/run/helix-remote-strict/hrs0123456789abcdef.json",
    policySha256: "a".repeat(64),
    policy,
    targetFingerprint: "f".repeat(64),
  }
}
function observed() {
  const initial = allocation()
  const policyRaw = JSON.stringify(initial.policy)
  const strict = { ...initial, policySha256: S.sha256(policyRaw) }
  const checkedAt = Date.now() / 1000
  const sampleRaw = JSON.stringify({
    version: "trp-remote-strict-sample/1.0.0",
    policySha256: strict.policySha256,
    bootId: strict.policy.bootId,
    observedAt: checkedAt,
    quota: {
      projectId: strict.policy.filesystem.projectId,
      usedBytes: 4096,
      hardBytes: strict.policy.filesystem.hardBytes,
      reportSource: "#142 4 0 65536 0 [------]\n",
      stateSource: "Accounting: ON\nEnforcement: ON\n",
      treeCheckExitCode: 0,
      treeCheckStdout: "",
      treeCheckStderr: "",
    },
  })
  const receipt = {
    version: H.VERSION,
    policy: strict.policy,
    policySha256: strict.policySha256,
    policyRaw,
    sampleRaw,
    sampleSha256: S.sha256(sampleRaw),
    checkedAt,
    role: "client",
    host: strict.policy.hostname,
    cwd: strict.policy.paths.clientWorkspace,
    membership: "0::/" + strict.policy.controller.cgroup,
    parentMembership: "0::/" + strict.policy.controller.cgroup,
    transport: "co-located-python",
    currentUsageIsSubtractedFromEntitlement: false,
    entitlement: strict.policy.entitlement,
    cgroup: {
      "cpu.max": "100000 100000",
      "memory.max": "2147483648",
      "memory.swap.max": "0",
      "memory.current": "52428800",
    },
    paths: Object.entries(strict.policy.paths).map(([name, path]) => ({
      name,
      path,
      device: strict.policy.filesystem.device,
      projectId: strict.policy.filesystem.projectId,
      inherit: true,
    })),
    quota: { usedBytes: 4096, hardBytes: strict.policy.filesystem.hardBytes },
  }
  return {
    ...inventory(),
    cpus: 3,
    memoryBytes: 4 * 1024 ** 3,
    freeBytes: strict.policy.entitlement.workBytes,
    remoteStrict: strict,
    remoteStrictObservation: receipt,
    remote: {
      version: Remote.VERSION,
      fingerprint: strict.targetFingerprint,
      partition: "helix",
      controllerCpus: 1,
      controllerMemoryBytes: 2 * 1024 ** 3,
      requiredNodes: ["worker1", "worker2"],
      secondsRemaining: 3600,
      nodes: ["worker1", "worker2"].map((name) => ({
        name,
        cpus: 2,
        memoryBytes: 2 * 1024 ** 3,
        eligible: true,
        state: "IDLE",
        source: "synthetic allocated worker contract",
      })),
    },
  }
}
const files = { "source.pdb": "ATOM\n", "selection.pdb": "ATOM\n" }

describe("optional co-located Slurm strict allocation", () => {
  test("dedicated controller entitlement is not its remaining headroom", () => {
    const value = observed()
    const decision = R.admit(R.count(files), value, { ...budget, requireHardStorageLimit: true })
    expect(decision.accepted).toBe(true)
    // A true reservation has the full two-GiB entitlement, although the client
    // already consumes memory inside it; remaining headroom is a different fact.
    value.remote.controllerMemoryBytes -= 50 * R.MiB
    expect(R.admit(R.count(files), value, budget).accepted).toBe(false)
  })
  test("one worker cannot borrow the second worker's memory", () => {
    const value = observed()
    value.remote.nodes[0].memoryBytes -= 1
    expect(R.admit(R.count(files), value, budget).rejections.map((r) => r.code)).toContain(
      "remote-placement-insufficient",
    )
  })
  test("receipts with stale sources, changed project flags or incomplete source evidence are refused", () => {
    for (const mode of ["stale", "project", "flag", "missing-source", "controller-limit", "subtracted-usage"]) {
      const value = observed()
      const r = value.remoteStrictObservation
      if (mode === "stale") r.checkedAt -= 10
      if (mode === "project") r.paths[0].projectId++
      if (mode === "flag") r.paths[0].inherit = false
      if (mode === "missing-source") r.sampleRaw = "{}"
      if (mode === "controller-limit") r.cgroup["memory.max"] = "4294967296"
      if (mode === "subtracted-usage") r.currentUsageIsSubtractedFromEntitlement = true
      expect(R.admit(R.count(files), value, budget).rejections.map((r) => r.code)).toContain(
        "remote-strict-receipt-invalid",
      )
    }
  })
  test("an unbound target or enlarged effective quota is rejected", () => {
    const value = observed()
    value.remoteStrict = { ...value.remoteStrict, targetFingerprint: "b".repeat(64) }
    expect(R.admit(R.count(files), value, budget).rejections.map((r) => r.code)).toContain(
      "remote-strict-receipt-invalid",
    )
    const allocated = observed()
    const reduced = { ...budget, workBytes: R.count(files).workBytes, requireHardStorageLimit: true }
    expect(R.admit(R.count(files), allocated, reduced).rejections.map((r) => r.code)).toContain(
      "enforcement-exceeds-budget",
    )
  })
  test("booleans, partial strict policy and a policy without a Slurm inventory never authorize a quota", () => {
    for (const remoteStrict of [true, {}, { version: H.VERSION }])
      expect(
        R.admit(R.count(files), { ...inventory(), remoteStrict }, { ...budget, requireHardStorageLimit: true })
          .accepted,
      ).toBe(false)
    expect(
      R.admit(R.count(files), { ...inventory(), remoteStrict: allocation() }, budget).rejections.map((r) => r.code),
    ).toContain("remote-strict-target-missing")
  })
  test("the local-only sandbox pointer cannot authorize a remote deployment", async () => {
    const oldRemote = process.env.HELIX_TRP_REMOTE,
      oldSandbox = process.env.HELIX_TRP_SANDBOX
    try {
      process.env.HELIX_TRP_REMOTE = "/tmp/unread-operator.json"
      process.env.HELIX_TRP_SANDBOX = "/run/trp-sandbox/trp0123456789abcdef.json"
      await expect(Remote.configured()).rejects.toThrow("local sandbox cannot authorize remote")
    } finally {
      if (oldRemote === undefined) delete process.env.HELIX_TRP_REMOTE
      else process.env.HELIX_TRP_REMOTE = oldRemote
      if (oldSandbox === undefined) delete process.env.HELIX_TRP_SANDBOX
      else process.env.HELIX_TRP_SANDBOX = oldSandbox
    }
  })
  test("an arbitrary user policy path fails before any process or filesystem allocation", async () => {
    await expect(H.observe("/tmp/pretend-root-policy.json", {})).rejects.toThrow("Invalid immutable remote policy path")
  })
  test("one preparation claims an allocation exactly once", async () => {
    const dir = await fs.mkdtemp(path.join(os.tmpdir(), "helix-remote-strict-claim-"))
    const initial = allocation()
    const value = { ...initial, policy: { ...initial.policy, paths: { ...initial.policy.paths, allocationRoot: dir } } }
    try {
      await H.claim(value)
      await expect(H.claim(value)).rejects.toThrow()
    } finally {
      await fs.rm(dir, { recursive: true, force: true })
    }
  })
  test("the strict policy and checker enter the digest with an explicit local transport backend", () => {
    const strict = allocation()
    const target: Remote.Target = {
      config: {
        version: Remote.VERSION,
        ...policySource.target,
        strictPolicy: strict.policyPath,
        numericalProfile: "haswell-single-thread",
      },
      fingerprint: strict.targetFingerprint,
      strict,
      public: {
        version: Remote.VERSION,
        ...policySource.target,
        strict,
        fingerprint: strict.targetFingerprint,
        transport: "co-located-python",
      },
    }
    const bundle = {
      spec: {
        graph: {
          nodes: [
            { id: "select", operation: "pdb.select" },
            { id: "geometry", operation: "geometre.geometry" },
          ],
        },
      },
      report: {},
      files: {
        ...files,
        "execution.json": "{}",
        "nextflow.config": "process.executor = 'local'\n--cpus 2 --tmpfs",
        "trp_select.py": "pass",
        "trp_geometry.py": "pass",
      },
      digest: "",
      image: "",
    } as any
    Remote.bind(bundle, target, "11111111-1111-1111-1111-111111111111")
    const execution = JSON.parse(bundle.files["execution.json"])
    expect(execution.backend).toBe(H.BACKEND)
    expect(execution.transport).toBe("co-located-python")
    expect(bundle.files["remote_strict.py"]).toBe(H.checkerSource)
    expect(JSON.parse(bundle.files["remote_strict_policy.json"])).toEqual(strict)
    const digest = N.bundleDigest(bundle.files)
    bundle.files["remote_strict_policy.json"] += " "
    expect(N.bundleDigest(bundle.files)).not.toBe(digest)
  })
})
