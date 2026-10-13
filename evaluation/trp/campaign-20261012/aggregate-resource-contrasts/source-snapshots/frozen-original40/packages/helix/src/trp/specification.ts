export * as TrpSpecification from "./specification"

import { Schema } from "effect"
import { createHash } from "node:crypto"
import { TrpCatalog } from "./catalog"

export const VERSION = "trp-spec/1.0.0"
export const ENGINE = "trp-nextflow/1.4.0"

export class WorkflowError extends Error {
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = "WorkflowError"
  }
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && Object.getPrototypeOf(value) === Object.prototype
}

/** Object keys are sorted; array order is meaningful. Only JSON values are accepted. */
export function canonical(value: unknown): string {
  if (value === null || typeof value === "boolean" || typeof value === "string") return JSON.stringify(value)
  if (typeof value === "number" && Number.isFinite(value)) return JSON.stringify(value)
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`
  if (isPlainRecord(value)) {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`)
      .join(",")}}`
  }
  throw new WorkflowError("non-json", "A specification must contain finite JSON values")
}

export const sha256 = (value: string | Uint8Array) => createHash("sha256").update(value).digest("hex")
export const catalogHash = sha256(canonical(TrpCatalog.catalog))

const Origin = Schema.Struct({
  kind: Schema.Literals(["user", "reference", "derived"]),
  reference: Schema.String.annotate({
    description:
      "Message ID, reference URI or derivation artifact. This is a declared source, not an independently verified attribution.",
  }),
  detail: Schema.String,
})
const sourced = <S extends Schema.Top>(value: S) => Schema.Struct({ value, origin: Origin })
const Range = Schema.Struct({ start: Schema.Number, end: Schema.Number })
export const Contract = Schema.Struct({
  protein: Schema.String,
  chain: Schema.String,
  format: Schema.String,
  numbering: Schema.String,
  insertionCodes: Schema.String,
  confidence: Schema.String,
  scale: Schema.String,
})
export type Contract = typeof Contract.Type

export const Specification = Schema.Struct({
  version: Schema.String,
  catalogHash: Schema.String,
  intent: sourced(Schema.String),
  structure: sourced(Schema.Struct({ path: Schema.String, sha256: Schema.String, pdb: Schema.String })),
  chain: sourced(Schema.String),
  model: sourced(Schema.Number.annotate({ description: "One-based ordinal of the model in the source PDB" })),
  units: sourced(Schema.Struct({ contract: Contract, ranges: Schema.Array(Range) })),
  insertions: sourced(Schema.Array(Range)),
  coordinateMapping: Schema.optional(
    sourced(
      Schema.Struct({
        path: Schema.String,
        sha256: Schema.String,
        frame: Schema.Literals(["label_seq_id", "uniprot"]),
        units: Schema.Array(Range),
        sifts: Schema.optional(Schema.Struct({ path: Schema.String, sha256: Schema.String, accession: Schema.String })),
      }).annotate({
        description:
          "Optional automatic conversion: units here are authoritative source intervals; units.value.ranges is replaced by verified author intervals. Existing insertion intervals remain in author numbering. SIFTS XML is required for UniProt numbering.",
      }),
    ),
  ),
  graph: Schema.Struct({
    nodes: Schema.Array(Schema.Struct({ id: Schema.String, operation: Schema.String })),
    edges: Schema.Array(
      Schema.Struct({ from: Schema.String, to: Schema.String, input: Schema.String, contract: Contract }),
    ),
  }),
})
export type Specification = typeof Specification.Type

export function parse(raw: unknown): Specification {
  // Reject additional fields, including invented "approved" and executable script fields.
  try {
    if (canonical(raw).length > 64_000) throw new Error("Specification exceeds 64 KB")
    return Schema.decodeUnknownSync(Specification, { onExcessProperty: "error" })(raw)
  } catch (error) {
    throw new WorkflowError("schema", String(error))
  }
}

export function contract(spec: Specification, operation: string): Contract {
  const base = {
    protein: spec.structure.value.pdb,
    chain: spec.chain.value,
    numbering: "pdb-author",
    confidence: "none",
  }
  if (operation === "input.units")
    return { ...base, format: "json", insertionCodes: "excluded", scale: "author-residue-interval" }
  return {
    ...base,
    format: "pdb",
    insertionCodes: operation === "input.structure" ? "preserved" : "excluded",
    scale: "xyz:angstrom;B:angstrom^2",
  }
}

/** A proposed graph. Validation still checks its declarations and the actual PDB bytes. */
export function geometryGraph(spec: Specification): Specification["graph"] {
  return {
    nodes: [
      { id: "structure", operation: "input.structure" },
      { id: "units", operation: "input.units" },
      { id: "select", operation: "pdb.select" },
      { id: "geometry", operation: "geometre.geometry" },
    ],
    edges: [
      { from: "structure", to: "select", input: "structure", contract: contract(spec, "input.structure") },
      { from: "select", to: "geometry", input: "structure", contract: contract(spec, "pdb.select") },
      { from: "units", to: "geometry", input: "units", contract: contract(spec, "input.units") },
    ],
  }
}
