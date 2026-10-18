import ts from "typescript"
import { readFileSync, existsSync, readdirSync } from "node:fs"
import { resolve, relative } from "node:path"

const root = resolve(import.meta.dir, "../..")
const workspace = resolve(root, "tmp/tui-identity")
const baseline = resolve(root, process.env.VERIFY_SOURCE ?? "tmp/tui-identity/baseline/source", "src")
const active = resolve(root, "packages/tui/src")
if (!existsSync(baseline)) throw new Error(`Missing frozen baseline: ${baseline}`)

function paths(directory: string, prefix = ""): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const name = prefix + entry.name
    return entry.isDirectory()
      ? paths(resolve(directory, entry.name), name + "/")
      : /\.tsx?$/.test(entry.name)
        ? [name]
        : []
  })
}
const changed = [...new Set([...paths(baseline), ...paths(active)])].sort().filter((path) => {
  const before = resolve(baseline, path)
  const after = resolve(active, path)
  return !existsSync(before) || !existsSync(after) || readFileSync(before, "utf8") !== readFileSync(after, "utf8")
})
const printer = ts.createPrinter({ removeComments: true })
const print = (node: ts.Node, source: ts.SourceFile) => printer.printNode(ts.EmitHint.Unspecified, node, source)
function inspect(path: string) {
  const result = {
    exists: existsSync(path),
    sdkCalls: [] as string[],
    bindings: [] as string[],
    handlers: [] as { name: string; code: string }[],
  }
  if (!result.exists) return result
  const source = ts.createSourceFile(path, readFileSync(path, "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  function visit(node: ts.Node) {
    if (ts.isCallExpression(node)) {
      const callee = node.expression.getText(source).replace(/\s+/g, "")
      if (callee.startsWith("sdk.client.")) result.sdkCalls.push(print(node, source))
      if (callee === "useBindings") result.bindings.push(print(node, source))
    }
    if (ts.isJsxAttribute(node) && /^on[A-Z]/.test(node.name.getText(source)) && node.initializer) {
      result.handlers.push({ name: node.name.getText(source), code: print(node.initializer, source) })
    }
    ts.forEachChild(node, visit)
  }
  visit(source)
  return result
}
const files = changed.map((path) => {
  const before = inspect(resolve(baseline, path)),
    after = inspect(resolve(active, path))
  return {
    path: "packages/tui/src/" + path,
    sdkCallsEqual: JSON.stringify(before.sdkCalls) === JSON.stringify(after.sdkCalls),
    bindingsEqual: JSON.stringify(before.bindings) === JSON.stringify(after.bindings),
    handlersEqual: JSON.stringify(before.handlers) === JSON.stringify(after.handlers),
    before,
    after,
  }
})
const revisionPath = resolve(baseline, "../../source-revision.txt")
const report = {
  generatedAt: new Date().toISOString(),
  baseline: relative(root, baseline),
  baselineRevision: existsSync(revisionPath) ? readFileSync(revisionPath, "utf8").trim() : undefined,
  scope:
    "AST evidence for SDK calls, useBindings registrations and JSX event attributes in TS/TSX files differing between frozen source and active source; works after commits and does not prove runtime equivalence alone.",
  sdkCallsAllEqual: files.every((file) => file.sdkCallsEqual),
  bindingsAllEqual: files.every((file) => file.bindingsEqual),
  files,
}
await Bun.write(resolve(workspace, "verification/behavioral-source-audit.json"), JSON.stringify(report, null, 2))
console.log(
  JSON.stringify(
    {
      files: files.length,
      sdkCalls: files.reduce((sum, file) => sum + file.after.sdkCalls.length, 0),
      bindings: files.reduce((sum, file) => sum + file.after.bindings.length, 0),
      sdkCallsAllEqual: report.sdkCallsAllEqual,
      bindingsAllEqual: report.bindingsAllEqual,
      handlerChanges: files.filter((file) => !file.handlersEqual).map((file) => file.path),
    },
    null,
    2,
  ),
)
if (!report.sdkCallsAllEqual || !report.bindingsAllEqual) process.exit(1)
