import { LayerNode } from "@helix/core/effect/layer-node"
import { AppNodeBuilder } from "@helix/core/effect/app-node-builder"
import { httpClient } from "@helix/core/effect/app-node-platform"
import { Effect, Layer, Schema, Context, Stream } from "effect"
import { serviceUse } from "@helix/core/effect/service-use"
import { HttpClient, HttpClientRequest, HttpClientResponse } from "effect/unstable/http"
import { withTransientReadRetry } from "@/util/effect-http-client"
import { ChildProcess } from "effect/unstable/process"
import { AppProcess } from "@helix/core/process"
import path from "path"
import os from "node:os"
import { makeRuntime } from "@helix/core/effect/runtime"
import semver from "semver"
import { InstallationChannel, InstallationVersion } from "@helix/core/installation/version"
import { InstallationEvent } from "@helix/schema/installation-event"
import { Identity } from "@helix/script/identity"

export type Method = "curl" | "npm" | "yarn" | "pnpm" | "bun" | "brew" | "scoop" | "choco" | "unknown"

// Explicit upgrades use official releases. Background upgrades remain disabled.
export const automaticUpdatesEnabled: boolean = false

export type ReleaseType = "patch" | "minor" | "major"

export const Event = InstallationEvent

export function getReleaseType(current: string, latest: string): ReleaseType {
  const currMajor = semver.major(current)
  const currMinor = semver.minor(current)
  const newMajor = semver.major(latest)
  const newMinor = semver.minor(latest)

  if (newMajor > currMajor) return "major"
  if (newMinor > currMinor) return "minor"
  return "patch"
}

export const Info = Schema.Struct({
  version: Schema.String,
  latest: Schema.String,
}).annotate({ identifier: "InstallationInfo" })
export type Info = Schema.Schema.Type<typeof Info>

export function userAgent(client = "cli") {
  return `helix/${InstallationChannel}/${InstallationVersion}/${client}`
}

export const USER_AGENT = userAgent()

export function isPreview() {
  return InstallationChannel !== "latest"
}

export function isLocal() {
  return InstallationChannel === "local"
}

export class UpgradeFailedError extends Schema.TaggedErrorClass<UpgradeFailedError>()("UpgradeFailedError", {
  stderr: Schema.String,
}) {
  override get message() {
    return this.stderr
  }
}

export function normalizeVersion(value: string) {
  const version = value.replace(/^v/, "")
  if (!semver.valid(version) || !/^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/.test(version))
    throw new UpgradeFailedError({ stderr: "Expected a published version such as 0.3.0." })
  return version
}

export function detectMethod(executable: string, home: string): Method {
  return path.resolve(executable) === path.join(home, ".helix", "bin", "helix") ? "curl" : "unknown"
}

// Response schemas for external version APIs
const GitHubRelease = Schema.Struct({ tag_name: Schema.String })
export interface Interface {
  readonly info: () => Effect.Effect<Info>
  readonly method: () => Effect.Effect<Method>
  readonly latest: (method?: Method) => Effect.Effect<string>
  readonly upgrade: (method: Method, target: string) => Effect.Effect<void, UpgradeFailedError>
}

export class Service extends Context.Service<Service, Interface>()("@helix/Installation") {}

export const use = serviceUse(Service)

const layer: Layer.Layer<Service, never, HttpClient.HttpClient | AppProcess.Service> = Layer.effect(
  Service,
  Effect.gen(function* () {
    const http = yield* HttpClient.HttpClient
    const httpOk = HttpClient.filterStatusOk(withTransientReadRetry(http))
    const appProcess = yield* AppProcess.Service

    const upgradeFailure = (method: Method, result?: { code: number; stdout: string; stderr: string }) => {
      if (method === "choco") return "not running from an elevated command shell"
      if (result) return `Upgrade failed for ${method} (exit code ${result.code}).`
      return `Upgrade failed for ${method}.`
    }

    // Re-runs the published installer, pinned to the requested version.
    //
    // Fetch the installer from the selected release tag, rather than a moving site.
    const upgradeCurl = Effect.fnUntraced(
      function* (target: string) {
        const url = `https://raw.githubusercontent.com/${Identity.repository}/v${target}/install`
        const response = yield* httpOk.execute(HttpClientRequest.get(url))
        const body = yield* response.text
        const bodyBytes = new TextEncoder().encode(body)
        if (!body.startsWith("#!/usr/bin/env bash\n"))
          return yield* Effect.fail(
            new UpgradeFailedError({ stderr: "Release returned an invalid Bash installer; installation unchanged." }),
          )
        const shell = "bash"
        const result = yield* appProcess.run(
          ChildProcess.make(shell, ["-s", "--", "--version", target, "--no-modify-path"], {
            stdin: Stream.make(bodyBytes),
            env: { VERSION: target, HELIX_INSTALL_REPO: Identity.repository },
            extendEnv: true,
          }),
        )
        return {
          code: result.exitCode,
          stdout: result.stdout.toString("utf8"),
          stderr: result.stderr.toString("utf8"),
        }
      },
      Effect.mapError((error) =>
        error instanceof UpgradeFailedError ? error : new UpgradeFailedError({ stderr: upgradeFailure("curl") }),
      ),
    )

    const result: Interface = {
      info: Effect.fn("Installation.info")(function* () {
        return {
          version: InstallationVersion,
          latest: yield* result.latest(),
        }
      }),
      method: Effect.fn("Installation.method")(function* () {
        return detectMethod(process.execPath, os.homedir())
      }),
      latest: Effect.fn("Installation.latest")(function* (installMethod?: Method) {
        if (installMethod !== "curl") return InstallationVersion
        const response = yield* httpOk.execute(
          HttpClientRequest.get(`https://api.github.com/repos/${Identity.repository}/releases/latest`).pipe(
            HttpClientRequest.acceptJson,
          ),
        )
        const data = yield* HttpClientResponse.schemaBodyJson(GitHubRelease)(response)
        return normalizeVersion(data.tag_name)
      }, Effect.orDie),
      upgrade: Effect.fn("Installation.upgrade")(function* (m: Method, target: string) {
        if (m !== "curl")
          return yield* Effect.fail(
            new UpgradeFailedError({
              stderr:
                "Only the official ~/.helix/bin/helix installation supports replacement. Re-run the official installer without uninstalling. Package-manager names may belong to other products.",
            }),
          )
        target = yield* Effect.try({
          try: () => normalizeVersion(target),
          catch: (error) => error as UpgradeFailedError,
        })
        const upgradeResult = yield* upgradeCurl(target)
        if (!upgradeResult || upgradeResult.code !== 0) {
          return yield* new UpgradeFailedError({ stderr: upgradeFailure(m, upgradeResult) })
        }
        yield* Effect.logInfo("upgraded", {
          method: m,
          target,
          stdout: upgradeResult.stdout,
          stderr: upgradeResult.stderr,
        })
        const installed = yield* appProcess
          .run(ChildProcess.make(path.join(os.homedir(), ".helix", "bin", "helix"), ["--version"]))
          .pipe(
            Effect.mapError(() => new UpgradeFailedError({ stderr: "Installed executable could not be verified." })),
          )
        if (installed.exitCode !== 0 || installed.stdout.toString("utf8").trim() !== target)
          return yield* Effect.fail(
            new UpgradeFailedError({
              stderr: `Installer completed but installed version does not match ${target}. Check ~/.helix/bin/helix --version.`,
            }),
          )
      }),
    }

    return Service.of(result)
  }),
)

export const node = LayerNode.make({ service: Service, layer: layer, deps: [httpClient, AppProcess.node] })

const { runPromise } = makeRuntime(Service, AppNodeBuilder.build(node))

export const latest = (...args: Parameters<Interface["latest"]>) => runPromise((s) => s.latest(...args))
export const method = () => runPromise((s) => s.method())
export const upgrade = (...args: Parameters<Interface["upgrade"]>) => runPromise((s) => s.upgrade(...args))

export * as Installation from "."
