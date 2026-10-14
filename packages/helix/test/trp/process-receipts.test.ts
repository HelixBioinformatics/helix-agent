import { expect, test } from "bun:test"
import { TrpWorkflow as W } from "../../src/trp/workflow"
import { TrpSpecification as S } from "../../src/trp/specification"

test("receipt references the exact approved runner without modifying process arguments", () => {
  const runner = "print('approved')\n", argv = ["/usr/bin/python3", "-c", runner]
  expect(W.processReceiptArgv(argv, runner, true)).toEqual(["/usr/bin/python3", "-c", `<approved-runner-sha256:${S.sha256(runner)}>`])
  expect(argv).toEqual(["/usr/bin/python3", "-c", runner])
})

test("unrelated source, flags, interpreter, missing approval and ordinary profiles remain literal", () => {
  const approved = "print('approved')\n"
  for (const argv of [
    ["/usr/bin/python3", "-c", approved + "print('changed')"],
    ["/usr/bin/python3", "-c", "unrelated"],
    ["/usr/bin/python3", "-I", "-c", approved],
    ["python3", "-c", approved],
    ["/usr/bin/python3", "other.py"],
  ]) expect(W.processReceiptArgv(argv, approved, true)).toEqual(argv)
  const argv = ["/usr/bin/python3", "-c", approved]
  expect(W.processReceiptArgv(argv, undefined, true)).toEqual(argv)
  expect(W.processReceiptArgv(argv, approved, false)).toEqual(argv)
})
