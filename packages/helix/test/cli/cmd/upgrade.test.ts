import { expect, test } from "bun:test"
import { upgradeAction } from "../../../src/cli/cmd/upgrade"

test("upgrades to a newer stable version and skips the current version", () => {
  expect(upgradeAction("0.3.0", "0.3.1", false)).toBe("install")
  expect(upgradeAction("0.3.1", "v0.3.1", false)).toBe("current")
})

test("never silently downgrades; an explicit older target remains available", () => {
  expect(upgradeAction("0.4.0", "0.3.1", false)).toBe("newer-installed")
  expect(upgradeAction("0.4.0", "0.3.1", true)).toBe("install")
  expect(() => upgradeAction("0.3.0", "latest; sh", true)).toThrow()
})
