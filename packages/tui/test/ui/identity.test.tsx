import { expect, test } from "bun:test"
import { identityAlphabet } from "../../src/ui/identity"
import { MARK_INNER, MARK_OUTER } from "../../src/logo"

test("normal identity preserves published strands while plain fallback stays ASCII", () => {
  expect(identityAlphabet(false).outer).toBe(MARK_OUTER)
  expect(identityAlphabet(false).inner).toBe(MARK_INNER)
  for (const glyph of Object.values(identityAlphabet(true))) {
    expect(glyph).toMatch(/^[\x20-\x7e]$/)
  }
})
