import { describe, expect, test } from "bun:test"
import { makeGlobalNode } from "@helix/core/effect/app-node"
import { LayerNode } from "@helix/core/effect/layer-node"
import { httpClient } from "@helix/core/effect/app-node-platform"
import { Effect, Layer, Stream } from "effect"
import { HttpClient, HttpClientRequest, HttpClientResponse } from "effect/unstable/http"
import { ChildProcess, ChildProcessSpawner } from "effect/unstable/process"
import { Installation } from "../../src/installation"
import { InstallationVersion } from "@helix/core/installation/version"
import { CrossSpawnSpawner } from "@helix/core/cross-spawn-spawner"
import { testEffect } from "../lib/effect"
import os from "os"
import path from "path"

const encoder = new TextEncoder()
const installedBinary = path.join(os.homedir(), ".helix", "bin", "helix")

function mockHttpClient(handler: (request: HttpClientRequest.HttpClientRequest) => Response) {
  const client = HttpClient.make((request) => Effect.succeed(HttpClientResponse.fromWeb(request, handler(request))))
  return Layer.succeed(HttpClient.HttpClient, client)
}

function mockSpawner(
  handler: (cmd: string, args: readonly string[]) => string | { code: number; stdout?: string; stderr?: string } = () =>
    "",
) {
  const spawner = ChildProcessSpawner.make((command) => {
    const std = ChildProcess.isStandardCommand(command) ? command : undefined
    const result = handler(std?.command ?? "", std?.args ?? [])
    const output = typeof result === "string" ? { code: 0, stdout: result, stderr: "" } : result
    return Effect.succeed(
      ChildProcessSpawner.makeHandle({
        pid: ChildProcessSpawner.ProcessId(0),
        exitCode: Effect.succeed(ChildProcessSpawner.ExitCode(output.code)),
        isRunning: Effect.succeed(false),
        kill: () => Effect.void,
        stdin: { [Symbol.for("effect/Sink/TypeId")]: Symbol.for("effect/Sink/TypeId") } as any,
        stdout: output.stdout ? Stream.make(encoder.encode(output.stdout)) : Stream.empty,
        stderr: output.stderr ? Stream.make(encoder.encode(output.stderr)) : Stream.empty,
        all: Stream.empty,
        getInputFd: () => ({ [Symbol.for("effect/Sink/TypeId")]: Symbol.for("effect/Sink/TypeId") }) as any,
        getOutputFd: () => Stream.empty,
        unref: Effect.succeed(Effect.void),
      }),
    )
  })
  return Layer.succeed(ChildProcessSpawner.ChildProcessSpawner, spawner)
}

function testLayer(
  httpHandler: (request: HttpClientRequest.HttpClientRequest) => Response,
  spawnHandler?: (cmd: string, args: readonly string[]) => string | { code: number; stdout?: string; stderr?: string },
) {
  const spawnerNode = makeGlobalNode({
    service: ChildProcessSpawner.ChildProcessSpawner,
    layer: mockSpawner(spawnHandler),
    deps: [],
  })
  return LayerNode.compile(Installation.node, [
    [httpClient, mockHttpClient(httpHandler)],
    [CrossSpawnSpawner.node, spawnerNode],
  ])
}

// Only explicit official-installer checks reach the release channel.
describe("installation", () => {
  describe("latest", () => {
    const calls: string[] = []
    testEffect(
      testLayer((request) => {
        calls.push(request.url)
        return new Response("unexpected", { status: 500 })
      }),
    ).effect("unsupported methods report running version without contacting namesake packages", () =>
      Effect.gen(function* () {
        for (const method of ["unknown", "npm", "bun", "pnpm", "scoop", "choco", "brew"] as const) {
          const result = yield* Installation.use.latest(method)
          expect(result).toBe(InstallationVersion)
        }
        expect(calls).toEqual([])
      }),
    )
  })

  describe("upgrade", () => {
    testEffect(
      testLayer(
        () => new Response("install script", { status: 200 }),
        () => ({ code: 1, stderr: "should not spawn any upgrade command" }),
      ),
    ).effect("rejects package-manager replacements because those names can identify another product", () =>
      Effect.gen(function* () {
        const error = yield* Effect.flip(Installation.use.upgrade("npm", "9.9.9"))
        expect(error).toBeInstanceOf(Installation.UpgradeFailedError)
        expect(error.stderr).toContain("Only the official")
      }),
    )
  })
})

const releaseRequests: string[] = []
testEffect(
  testLayer((request) => {
    releaseRequests.push(request.url)
    return Response.json({ tag_name: "v0.3.1" })
  }),
).effect("explicit latest uses the Helix Bioinformatics GitHub release only", () =>
  Effect.gen(function* () {
    expect(yield* Installation.use.latest("curl")).toBe("0.3.1")
    expect(releaseRequests).toEqual(["https://api.github.com/repos/HelixBioinformatics/helix-agent/releases/latest"])
  }),
)

const installerRequests: string[] = [],
  launches: { cmd: string; args: readonly string[] }[] = []
testEffect(
  testLayer(
    (request) => {
      installerRequests.push(request.url)
      return new Response("#!/usr/bin/env bash\nexit 0\n")
    },
    (cmd, args) => {
      launches.push({ cmd, args })
      return cmd === installedBinary ? "0.3.1\n" : ""
    },
  ),
).effect("pins installer to release tag, selects version explicitly and verifies installed binary", () =>
  Effect.gen(function* () {
    yield* Installation.use.upgrade("curl", "v0.3.1")
    expect(installerRequests).toEqual([
      "https://raw.githubusercontent.com/HelixBioinformatics/helix-agent/v0.3.1/install",
    ])
    expect(launches[0]).toEqual({ cmd: "bash", args: ["-s", "--", "--version", "0.3.1", "--no-modify-path"] })
    expect(launches[1].cmd).toBe(installedBinary)
  }),
)

testEffect(
  testLayer(
    () => new Response("<html>not a script</html>"),
    () => {
      throw new Error("must not execute")
    },
  ),
).effect("rejects unexpected installer content before process execution", () =>
  Effect.gen(function* () {
    const error = yield* Effect.flip(Installation.use.upgrade("curl", "0.3.1"))
    expect(error.stderr).toContain("invalid Bash installer")
  }),
)

testEffect(
  testLayer(() => {
    throw new Error("must not fetch")
  }),
).effect("rejects injection strings before any fetch or process", () =>
  Effect.gen(function* () {
    const error = yield* Effect.flip(Installation.use.upgrade("curl", "0.3.1; echo unsafe"))
    expect(error.stderr).toContain("Expected a published version")
  }),
)

testEffect(
  testLayer(
    () => new Response("#!/usr/bin/env bash\nexit 0\n"),
    (cmd) => (cmd === installedBinary ? "0.2.0\n" : ""),
  ),
).effect("fails if installer exits zero but replacement version is wrong", () =>
  Effect.gen(function* () {
    const error = yield* Effect.flip(Installation.use.upgrade("curl", "0.3.1"))
    expect(error.stderr).toContain("does not match")
  }),
)

test("installation detection never mistakes a package-manager or source executable for official Helix", () => {
  const home = path.resolve(os.tmpdir(), "helix-installation-home")
  expect(Installation.detectMethod(path.join(home, ".helix", "bin", "helix"), home)).toBe("curl")
  expect(Installation.detectMethod(path.join(home, ".local", "bin", "helix"), home)).toBe("unknown")
  expect(Installation.detectMethod(path.join(home, ".bun", "bin", "bun"), home)).toBe("unknown")
  expect(Installation.automaticUpdatesEnabled).toBe(false)
})
