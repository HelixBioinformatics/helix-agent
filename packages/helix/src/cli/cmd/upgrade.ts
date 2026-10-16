import { Effect } from "effect"
import semver from "semver"
import { Installation } from "@/installation"
import { InstallationVersion } from "@helix/core/installation/version"
import { effectCmd, fail } from "../effect-cmd"
import { UI } from "../ui"

export function upgradeAction(current: string, target: string, explicit: boolean) {
  const version = Installation.normalizeVersion(target)
  if (current === version) return "current" as const
  if (!explicit && semver.valid(current) && semver.lt(version, current)) return "newer-installed" as const
  return "install" as const
}

export const UpgradeCommand = effectCmd({
  command: "upgrade [target]",
  describe: "update Helix Agent without uninstalling or deleting settings",
  instance: false,
  builder: (yargs) =>
    yargs
      .positional("target", { type: "string", describe: "published version (default: latest stable)" })
      .option("check", { type: "boolean", default: false, describe: "show the available version without installing" }),
  handler: Effect.fn("Cli.upgrade")(function* (args) {
    const installation = yield* Installation.Service
    const method = yield* installation.method()
    if (method !== "curl" && !args.check)
      return yield* fail(
        "This executable is not the official ~/.helix/bin/helix installation. Re-run the installer from https://helixbioinformatics.github.io/helix-agent/ without uninstalling; your settings and sessions are retained.",
      )
    const target = args.target
      ? yield* Effect.try({
          try: () => Installation.normalizeVersion(args.target!),
          catch: (error) => new Error(String(error)),
        }).pipe(Effect.catch((error) => fail(error.message)))
      : yield* installation
          .latest("curl")
          .pipe(
            Effect.catchCause(() =>
              fail("Could not check the official GitHub release. Check your connection and try again."),
            ),
          )
    if (args.check) {
      UI.println(`Installed: ${InstallationVersion}\nAvailable: ${target}\nInstallation: ${method}`)
      return
    }
    const action = upgradeAction(InstallationVersion, target, Boolean(args.target))
    if (action !== "install") {
      UI.println(
        action === "current"
          ? `Helix ${target} is already installed.`
          : `Installed version ${InstallationVersion} is newer than stable ${target}; no downgrade performed.`,
      )
      return
    }
    UI.println(`Updating Helix Agent ${InstallationVersion} → ${target}…`)
    yield* installation.upgrade(method, target).pipe(Effect.catch((error) => fail(error.stderr)))
    UI.println(
      `Helix Agent ${target} installed. Start a new Helix session to use it. Settings and session history were retained.`,
    )
  }),
})
