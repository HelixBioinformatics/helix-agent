export * as TrpGraph from "./graph"

import { TrpSpecification as S } from "./specification"

export interface Check {
  code: string
  status: "passed" | "failed" | "omitted"
  detail: string
}
export interface Report {
  valid: boolean
  checks: Check[]
  order: string[]
  selected?: string
  residues?: number
}

const operations = ["input.structure", "input.units", "pdb.select", "geometre.geometry"]
const contractFields = ["protein", "chain", "format", "numbering", "insertionCodes", "confidence", "scale"] as const
const required: Record<string, Record<string, string>> = {
  "input.structure": {},
  "input.units": {},
  "pdb.select": { structure: "input.structure" },
  "geometre.geometry": { structure: "pdb.select", units: "input.units" },
}

/** Closed, fail-closed composition for the admitted geometry route. No inferred residue offsets. */
export function validate(raw: unknown, pdb: Uint8Array): Report {
  const checks: Check[] = []
  const check = (code: string, pass: boolean, detail: string) =>
    checks.push({ code, status: pass ? "passed" : "failed", detail })
  let spec: S.Specification
  try {
    spec = S.parse(raw)
  } catch (error) {
    return { valid: false, checks: [{ code: "schema", status: "failed", detail: String(error) }], order: [] }
  }
  check(
    "version",
    spec.version === S.VERSION && spec.catalogHash === S.catalogHash,
    "Specification and catalogue revisions match the executing engine",
  )
  for (const key of ["intent", "structure", "chain", "model", "units", "insertions"] as const) {
    check(
      "parameter-origin",
      !!spec[key].origin.reference.trim() && !!spec[key].origin.detail.trim(),
      `${key}: declared source is present`,
    )
  }
  if (spec.coordinateMapping)
    check(
      "parameter-origin",
      !!spec.coordinateMapping.origin.reference.trim() && !!spec.coordinateMapping.origin.detail.trim(),
      "coordinateMapping: declared source is present",
    )
  check("intent", !!spec.intent.value.trim(), "An explicit scientific intent is required")
  check("protein-identifier", /^[0-9][a-z0-9]{3}$/.test(spec.structure.value.pdb), "Legacy PDB identifier, lowercase")
  check("chain", /^[A-Za-z0-9]$/.test(spec.chain.value), "One explicit, case-sensitive author chain")
  check("model", Number.isSafeInteger(spec.model.value) && spec.model.value >= 1, "One-based model ordinal")
  check(
    "artifact-hash",
    /^[a-f0-9]{64}$/.test(spec.structure.value.sha256) && S.sha256(pdb) === spec.structure.value.sha256,
    "Source bytes match the declared SHA-256",
  )

  const nodes = spec.graph.nodes
  const byId = new Map(nodes.map((node) => [node.id, node]))
  check(
    "node-id",
    nodes.every((node) => /^[a-z][a-z0-9_]{0,31}$/.test(node.id)) && byId.size === nodes.length,
    "Unique, safe node identifiers",
  )
  check(
    "excluded-operation",
    nodes.every((node) => operations.includes(node.operation)),
    "Every operation has a tested adapter",
  )
  check(
    "required-step",
    operations.every((op) => nodes.filter((node) => node.operation === op).length === 1) &&
      nodes.length === operations.length,
    "Exactly one source, annotation input, checked selection and geometry operation",
  )
  const degree = new Map(nodes.map((node) => [node.id, 0]))
  const outgoing = new Map(nodes.map((node) => [node.id, [] as string[]]))
  const targets = new Set<string>()
  for (const edge of spec.graph.edges) {
    const from = byId.get(edge.from),
      to = byId.get(edge.to)
    check("missing-dependency", !!from && !!to, `${edge.from} → ${edge.to}`)
    if (!from || !to) continue
    degree.set(to.id, degree.get(to.id)! + 1)
    outgoing.get(from.id)!.push(to.id)
    const key = `${edge.to}:${edge.input}`
    check("duplicate-input", !targets.has(key), key)
    targets.add(key)
    check(
      "port-binding",
      required[to.operation]?.[edge.input] === from.operation,
      `${key} must be connected to its declared producer`,
    )
    const expected = S.contract(spec, from.operation)
    for (const field of contractFields) {
      check(`edge-${field}`, edge.contract[field] === expected[field], `${key}.${field}: expected ${expected[field]}`)
    }
  }
  for (const node of nodes)
    for (const input of Object.keys(required[node.operation] ?? {})) {
      check("required-input", targets.has(`${node.id}:${input}`), `${node.id}.${input}`)
    }
  const queue = nodes.filter((node) => degree.get(node.id) === 0).map((node) => node.id),
    order: string[] = []
  for (let cursor = 0; cursor < queue.length; cursor++) {
    const id = queue[cursor]
    order.push(id)
    for (const next of outgoing.get(id) ?? []) {
      degree.set(next, degree.get(next)! - 1)
      if (degree.get(next) === 0) queue.push(next)
    }
  }
  check(
    "cycle",
    order.length === nodes.length && byId.size === nodes.length,
    "Kahn topological traversal visits every node once",
  )
  const annotation = S.contract(spec, "input.units")
  for (const field of contractFields) {
    check(
      `units-${field}`,
      spec.units.value.contract[field] === annotation[field],
      `Annotation ${field} matches the selected structure frame`,
    )
  }

  const lines = new TextDecoder("utf-8", { fatal: false }).decode(pdb).split(/\r?\n/)
  const header = lines.find((line) => line.startsWith("HEADER"))
  check(
    "pdb-format",
    !!header && lines.some((line) => line.startsWith("ATOM  ")),
    "A legacy PDB HEADER and ATOM records are required",
  )
  check(
    "protein-identity",
    header?.slice(62, 66).trim().toLowerCase() === spec.structure.value.pdb,
    "PDB HEADER identity equals the requested protein",
  )
  const hasModels = lines.some((line) => line.startsWith("MODEL "))
  let ordinal = hasModels ? 0 : 1
  let active = !hasModels
  const atoms: string[] = [],
    residues = new Map<number, number>()
  let inserted = false,
    alternate = false,
    finite = true,
    integerResidues = true
  for (const line of lines) {
    if (line.startsWith("MODEL ")) {
      ordinal++
      active = true
      continue
    }
    if (line.startsWith("ENDMDL")) {
      active = false
      continue
    }
    if (!active || ordinal !== spec.model.value || !line.startsWith("ATOM  ") || line[21] !== spec.chain.value) continue
    inserted ||= line[26] !== " "
    alternate ||= line[16] !== " "
    const res = Number(line.slice(22, 26).trim())
    integerResidues &&= /^\s*\d+\s*$/.test(line.slice(22, 26)) && Number.isSafeInteger(res) && res > 0
    finite &&= [
      line.slice(30, 38),
      line.slice(38, 46),
      line.slice(46, 54),
      line.slice(54, 60),
      line.slice(60, 66),
    ].every((v) => v.trim() !== "" && Number.isFinite(Number(v)))
    if (line.slice(12, 16).trim() === "CA") residues.set(res, (residues.get(res) ?? 0) + 1)
    atoms.push(line)
  }
  check("selected-model-chain", atoms.length > 0, "Requested model and author chain contain atoms")
  check("insertion-codes", !inserted, "GeomeTRe adapter excludes author insertion codes; none may be discarded")
  check(
    "alternate-locations",
    !alternate && [...residues.values()].every((count) => count === 1),
    "Unambiguous atom conformers and one CA per residue",
  )
  check(
    "coordinate-scale",
    finite && integerResidues,
    "Finite PDB coordinates, occupancy and displacement values; supported positive author residue numbers",
  )
  const ranges = [...spec.units.value.ranges, ...spec.insertions.value]
  const goodRanges = ranges.every(
    (r) =>
      Number.isSafeInteger(r.start) && Number.isSafeInteger(r.end) && r.start > 0 && r.end <= 9999 && r.end >= r.start,
  )
  check(
    "unit-count",
    spec.units.value.ranges.length >= 3 && spec.units.value.ranges.length <= 1000,
    "At least three, at most 1000 supplied units; GeomeTRe circle fitting requires three centers",
  )
  check("unit-range", goodRanges, "Finite, positive, inclusive author intervals within legacy PDB bounds")
  for (const [label, values] of [
    ["units", spec.units.value.ranges],
    ["insertions", spec.insertions.value],
  ] as const) {
    check(
      "range-order",
      values.every((r, i) => i === 0 || values[i - 1].end < r.start),
      `${label} must be ordered and nonoverlapping`,
    )
  }
  if (goodRanges) {
    const occupied = new Set<number>()
    let overlap = false,
      present = true
    for (const r of ranges)
      for (let i = r.start; i <= r.end; i++) {
        overlap ||= occupied.has(i)
        occupied.add(i)
        present &&= residues.get(i) === 1
      }
    check("range-overlap", !overlap, "Units and declared insertions do not overlap")
    check(
      "residue-coverage",
      present,
      "Every requested residue has one observed CA; no silent omission or guessed offset",
    )
    check(
      "unit-length",
      spec.units.value.ranges.every((r) => r.end - r.start + 1 >= 6),
      "Units meet the admitted default geometry window of six residues",
    )
  }
  checks.push(
    {
      code: "source-attribution",
      status: "omitted",
      detail: "Origins are declared by the proposer; source authorship is not independently authenticated",
    },
    {
      code: "repeat-detection",
      status: "omitted",
      detail: "Units are supplied; GeomeTRe does not detect or validate repeat membership",
    },
    {
      code: "structural-confidence",
      status: "omitted",
      detail:
        "Static graph validation is not a structural assessment; preparation must attach the separate versioned structural report",
    },
    {
      code: "resource-admission",
      status: "omitted",
      detail:
        "Static graph validation does not observe resources; TrpWorkflow must attach dated inventory and budget admission",
    },
    {
      code: "external-annotation",
      status: "omitted",
      detail: "Independent annotator and held-out evaluation remain pending",
    },
  )
  const valid = checks.every((item) => item.status !== "failed")
  return {
    valid,
    checks,
    order,
    ...(valid ? { selected: `${header}\n${atoms.join("\n")}\nTER\nEND\n`, residues: residues.size } : {}),
  }
}
