export * as TrpCatalog from "./catalog"

import { Schema } from "effect"
import { createHash } from "node:crypto"
import fs from "node:fs/promises"
import path from "node:path"
import source from "./catalog.json"
import vocabulary from "./edam.json"

const Term = Schema.Struct({ uri: Schema.String, term: Schema.String })
const Artifact = Schema.Struct({ path: Schema.String, bytes: Schema.Number, sha256: Schema.String })
const Scale = Schema.Struct({
  field: Schema.String,
  meaning: Schema.String,
  unit: Schema.String,
  minimum: Schema.optional(Schema.Number),
  maximum: Schema.optional(Schema.Number),
  direction: Schema.Literals(["higher", "lower", "none"]),
})
export const Port = Schema.Struct({
  id: Schema.String,
  data: Term,
  format: Term,
  namespace: Schema.String,
  chain: Schema.Literals(["author", "label", "none", "unresolved"]),
  numbering: Schema.Literals(["pdb-author", "label-seq-id", "uniprot", "none", "unresolved"]),
  insertionCodes: Schema.Literals(["preserved", "excluded", "none", "unresolved"]),
  confidence: Schema.Literals(["none", "plddt-0-100", "pae-angstrom", "unresolved"]),
  scales: Schema.Array(Scale),
  constraints: Schema.Array(Schema.String),
})
export type Port = Schema.Schema.Type<typeof Port>

export const Entry = Schema.Struct({
  id: Schema.String,
  name: Schema.String,
  status: Schema.Literals(["admitted", "candidate", "web-comparator"]),
  kind: Schema.Literals(["http", "container", "web"]),
  source: Schema.Struct({
    url: Schema.String,
    revision: Schema.String,
    license: Schema.String,
    licenseUrl: Schema.String,
  }),
  operation: Term,
  inputs: Schema.Array(Port),
  outputs: Schema.Array(Port),
  parameters: Schema.Array(Schema.String),
  limitations: Schema.Array(Schema.String),
  reference: Schema.optional(
    Schema.Struct({
      revision: Schema.String,
      command: Schema.Array(Schema.String),
      exitCode: Schema.Number,
      image: Schema.optional(Schema.String),
      record: Artifact,
      inputs: Schema.Array(Artifact),
      outputs: Schema.Array(Artifact),
    }),
  ),
})
export type Entry = Schema.Schema.Type<typeof Entry>
const Document = Schema.Struct({ version: Schema.String, entries: Schema.Array(Entry) })
export type Document = Schema.Schema.Type<typeof Document>

export class CatalogError extends Error {
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = "CatalogError"
  }
}

function term(value: typeof Term.Type, branch: "operation" | "data" | "format") {
  if (
    !vocabulary.terms.some((entry) => entry.uri === value.uri && entry.term === value.term) ||
    !value.uri.startsWith(`http://edamontology.org/${branch}_`)
  ) {
    throw new CatalogError("invalid-edam", `Unverified ${branch} term: ${value.uri} (${value.term})`)
  }
}

function artifact(value: typeof Artifact.Type) {
  if (
    !/^[a-f0-9]{64}$/.test(value.sha256) ||
    !Number.isSafeInteger(value.bytes) ||
    value.bytes < 0 ||
    !value.path ||
    path.isAbsolute(value.path) ||
    value.path.split(/[\\/]/).some((part) => !part || part === ".." || part === ".")
  ) {
    throw new CatalogError("invalid-artifact", `Invalid reference artifact: ${value.path}`)
  }
}

/** Validate declarations. Reading and checking the referenced bytes happens in resolve(). */
export function parse(raw: unknown): Document {
  const document = Schema.decodeUnknownSync(Document)(raw)
  const ids = new Set<string>()
  for (const entry of document.entries) {
    if (!entry.id || ids.has(entry.id)) throw new CatalogError("duplicate-id", entry.id)
    ids.add(entry.id)
    term(entry.operation, "operation")
    for (const ports of [entry.inputs, entry.outputs]) {
      if (ports.length === 0) throw new CatalogError("missing-port", entry.id)
      const portIds = new Set<string>()
      for (const port of ports) {
        if (!port.id || portIds.has(port.id)) throw new CatalogError("duplicate-port", entry.id)
        portIds.add(port.id)
        term(port.data, "data")
        term(port.format, "format")
        for (const scale of port.scales) {
          if (
            (scale.minimum !== undefined && !Number.isFinite(scale.minimum)) ||
            (scale.maximum !== undefined && !Number.isFinite(scale.maximum)) ||
            (scale.minimum !== undefined && scale.maximum !== undefined && scale.minimum > scale.maximum)
          ) {
            throw new CatalogError("invalid-scale", `${entry.id}:${scale.field}`)
          }
        }
      }
    }
    if (entry.status !== "admitted") continue
    const ref = entry.reference
    if (
      !ref ||
      ref.exitCode !== 0 ||
      ref.outputs.length === 0 ||
      ref.inputs.length === 0 ||
      ref.command.length === 0 ||
      !entry.source.revision ||
      ref.revision !== entry.source.revision ||
      entry.source.license === "unresolved"
    ) {
      throw new CatalogError("missing-reference", entry.id)
    }
    if (entry.kind === "web" || (entry.kind === "container" && !/^sha256:[a-f0-9]{64}$/.test(ref.image ?? ""))) {
      throw new CatalogError("missing-image", entry.id)
    }
    for (const file of [ref.record, ...ref.inputs, ...ref.outputs]) artifact(file)
  }
  return document
}

export const catalog = parse(source)

/** Narrow equality only. F3 must also check identity, mapping evidence, graph and actual data. */
export function compatible(output: Port, input: Port): boolean {
  return (
    output.data.uri === input.data.uri &&
    output.format.uri === input.format.uri &&
    output.namespace === input.namespace &&
    output.chain === input.chain &&
    output.chain !== "unresolved" &&
    output.numbering === input.numbering &&
    output.numbering !== "unresolved" &&
    output.insertionCodes === input.insertionCodes &&
    output.insertionCodes !== "unresolved" &&
    output.confidence === input.confidence &&
    output.confidence !== "unresolved" &&
    JSON.stringify(output.scales) === JSON.stringify(input.scales) &&
    input.constraints.every((constraint) => output.constraints.includes(constraint))
  )
}

/** Resolve only admitted entries after independently checking their stored reference artifacts. */
export async function resolve(id: string, root: string, document: Document = catalog): Promise<Entry> {
  const entry = parse(document).entries.find((item) => item.id === id)
  if (!entry) throw new CatalogError("unknown-operation", id)
  if (entry.status !== "admitted" || !entry.reference) throw new CatalogError("not-admitted", id)
  const base = await fs.realpath(root)
  for (const file of [entry.reference.record, ...entry.reference.inputs, ...entry.reference.outputs]) {
    let actual: string
    try {
      actual = await fs.realpath(path.join(base, file.path))
    } catch {
      throw new CatalogError("missing-artifact", file.path)
    }
    const relative = path.relative(base, actual)
    if (relative.startsWith(`..${path.sep}`) || relative === ".." || path.isAbsolute(relative)) {
      throw new CatalogError("artifact-escape", file.path)
    }
    const bytes = await fs.readFile(actual)
    if (bytes.byteLength !== file.bytes || createHash("sha256").update(bytes).digest("hex") !== file.sha256) {
      throw new CatalogError("artifact-mismatch", file.path)
    }
  }
  return entry
}
