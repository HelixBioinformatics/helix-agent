export * as TrpCoordinates from "./coordinates"

import fs from "node:fs/promises"
import path from "node:path"
import { TrpSpecification as S } from "./specification"
import { TrpStructural as C } from "./structural"
import SIFTS_SCRIPT from "./sifts_residues.py.txt"

type Residue = {
  label: number | null
  auth: string
  name: string
  alt: string
  insertion: string
  xyz: number[]
  b: number
}

function index<T, K>(rows: readonly T[], key: (row: T) => K) {
  const result = new Map<K, T[]>()
  for (const row of rows) {
    const k = key(row),
      existing = result.get(k)
    if (existing) existing.push(row)
    else result.set(k, [row])
  }
  return result
}

/** Require each observed residue to agree, never infer a numbering offset from endpoints. */
export function mapUnits(source: C.Report, target: C.Report, units: readonly { start: number; end: number }[]) {
  const fail = (message: string): never => {
    throw new S.WorkflowError("coordinate-mapping", message)
  }
  if (!source.summary.mechanicalAdmission || !target.summary.mechanicalAdmission) fail("Unadmitted structure")
  if (source.provenance.confidenceScale !== "Bfactor_A2" || target.provenance.confidenceScale !== "Bfactor_A2")
    fail("Experimental B-factor route only")
  if (
    !source.provenance.entry ||
    source.provenance.entry.toLowerCase() !== target.provenance.entry?.toLowerCase() ||
    source.provenance.authorChain !== target.provenance.authorChain ||
    source.provenance.model !== target.provenance.model
  )
    fail("Structure identity mismatch")
  const labels = index(source.mapping as Residue[], (row) => row.label),
    authors = index(target.mapping as Residue[], (row) => row.auth)
  const mapping: { label: number; author: number; residue: string }[] = []
  const ranges = units.map((unit) => {
    if (
      !Number.isSafeInteger(unit.start) ||
      !Number.isSafeInteger(unit.end) ||
      unit.start < 1 ||
      unit.end < unit.start ||
      unit.end - unit.start > 100_000
    )
      fail("Invalid label interval")
    const numbers: number[] = []
    for (let label = unit.start; label <= unit.end; label++) {
      const matches = labels.get(label) ?? []
      if (matches.length !== 1) fail("Missing or ambiguous label residue")
      const row = matches[0],
        author = Number(row.auth)
      if (!Number.isSafeInteger(author) || author <= 0) fail("Nonpositive or noninteger author residue")
      const targets = authors.get(row.auth) ?? []
      if (targets.length !== 1) fail("Missing or ambiguous author residue")
      const other = targets[0]
      if (row.alt || row.insertion || other.alt || other.insertion || row.name !== other.name)
        fail("Residue identity mismatch")
      if (
        row.xyz.length !== 3 ||
        other.xyz.length !== 3 ||
        row.xyz.some(
          (v, i) => !Number.isFinite(v) || !Number.isFinite(other.xyz[i]) || Math.abs(v - other.xyz[i]) > 0.0011,
        )
      )
        fail("Residue coordinate mismatch")
      if (!Number.isFinite(row.b) || !Number.isFinite(other.b) || Math.abs(row.b - other.b) > 0.011)
        fail("Displacement scale/value mismatch")
      if (numbers.length && author !== numbers[numbers.length - 1] + 1) fail("Noncontiguous author interval")
      numbers.push(author)
      mapping.push({ label, author, residue: row.name })
    }
    return { start: numbers[0], end: numbers[numbers.length - 1] }
  })
  return { ranges, mapping }
}

export async function prepare(spec: S.Specification, pdb: Uint8Array, workspace: string) {
  if (!spec.coordinateMapping) return { spec, files: {} as Record<string, string> }
  const input = spec.coordinateMapping.value
  const root = await fs.realpath(workspace),
    file = await fs.realpath(path.resolve(root, input.path))
  const rel = path.relative(root, file)
  if (rel === ".." || rel.startsWith(`..${path.sep}`) || path.isAbsolute(rel))
    throw new S.WorkflowError("input-escape", "Mapping source escapes workspace")
  const stat = await fs.stat(file)
  if (!stat.isFile() || stat.size > 20_000_000)
    throw new S.WorkflowError("input-size", "Mapping input must be a regular file <=20 MB")
  const bytes = await fs.readFile(file)
  if (bytes.length > 20_000_000 || S.sha256(bytes) !== input.sha256)
    throw new S.WorkflowError("mapping-hash", "Mapping source changed")
  const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes)
  const local = path.join(root, ".helix/trp-python/bin/python")
  const python =
    process.env.HELIX_TRP_PYTHON ??
    (await fs.access(local).then(
      () => local,
      () => "python3",
    ))
  const base = { chain: spec.chain.value, model: spec.model.value }
  let labelUnits = input.units
  const extra: Record<string, string> = {}
  if (input.frame === "uniprot") {
    if (!input.sifts)
      throw new S.WorkflowError("sifts-required", "UniProt intervals require archived residue-level SIFTS XML")
    const siftsFile = await fs.realpath(path.resolve(root, input.sifts.path)),
      relative = path.relative(root, siftsFile)
    if (relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative))
      throw new S.WorkflowError("input-escape", "SIFTS source escapes workspace")
    const stats = await fs.stat(siftsFile)
    if (!stats.isFile() || stats.size > 20_000_000) throw new S.WorkflowError("input-size", "SIFTS XML exceeds limit")
    const raw = await fs.readFile(siftsFile)
    if (raw.length > 20_000_000 || S.sha256(raw) !== input.sifts.sha256)
      throw new S.WorkflowError("sifts-hash", "SIFTS source changed")
    const xml = new TextDecoder("utf-8", { fatal: true }).decode(raw)
    const sifts = (await C.runParser(
      { xml, pdb: spec.structure.value.pdb, chain: base.chain, accession: input.sifts.accession },
      undefined,
      python,
      SIFTS_SCRIPT,
    )) as { rows: { author: number; uniprot: number; residue: string }[] }
    const probe = await C.inspect(
      { structure: text, options: { ...base, format: "mmcif", frame: "label_seq_id", units: input.units } },
      undefined,
      python,
    )
    const uniprotRows = index(sifts.rows, (row) => row.uniprot),
      authorRows = index(probe.mapping as Residue[], (row) => row.auth)
    labelUnits = input.units.map((unit) => {
      if (
        !Number.isSafeInteger(unit.start) ||
        !Number.isSafeInteger(unit.end) ||
        unit.start < 1 ||
        unit.end < unit.start ||
        unit.end - unit.start > 10_000
      )
        throw new S.WorkflowError("sifts-range", "Invalid UniProt interval")
      const labels: number[] = []
      for (let position = unit.start; position <= unit.end; position++) {
        const rows = uniprotRows.get(position) ?? []
        if (rows.length !== 1) throw new S.WorkflowError("sifts-coverage", "Missing or ambiguous UniProt residue")
        const matches = authorRows.get(String(rows[0].author)) ?? []
        if (matches.length !== 1 || matches[0].name !== rows[0].residue || !Number.isSafeInteger(matches[0].label))
          throw new S.WorkflowError("sifts-identity", "SIFTS residue disagrees with mmCIF")
        const label = matches[0].label!
        if (labels.length && label !== labels[labels.length - 1] + 1)
          throw new S.WorkflowError("sifts-contiguity", "UniProt interval is not contiguous in mmCIF")
        labels.push(label)
      }
      return { start: labels[0], end: labels[labels.length - 1] }
    })
    extra["sifts_source.xml"] = xml
    extra["sifts_mapping.json"] = S.canonical(sifts) + "\n"
    extra["sifts_residues.py"] = SIFTS_SCRIPT
  } else if (input.sifts) throw new S.WorkflowError("sifts-unused", "SIFTS archive requires UniProt frame")
  const source = await C.inspect(
    { structure: text, options: { ...base, format: "mmcif", frame: "label_seq_id", units: labelUnits } },
    undefined,
    python,
  )
  const sourceLabels = index(source.mapping as Residue[], (row) => row.label)
  const provisional = labelUnits.map((unit) => {
    return {
      start: Number(sourceLabels.get(unit.start)?.[0]?.auth),
      end: Number(sourceLabels.get(unit.end)?.[0]?.auth),
    }
  })
  const target = await C.inspect(
    {
      structure: new TextDecoder("utf-8", { fatal: true }).decode(pdb),
      options: { ...base, format: "pdb", frame: "auth_seq_id", units: provisional },
    },
    undefined,
    python,
  )
  const mapped = mapUnits(source, target, labelUnits)
  const effective = S.parse({
    ...spec,
    units: {
      ...spec.units,
      value: { ...spec.units.value, ranges: mapped.ranges },
      origin: {
        kind: "derived",
        reference: "coordinate_mapping.json",
        detail: "Exact mmCIF label to author residue identity and coordinate agreement",
      },
    },
  })
  const audit = {
    version: "trp-coordinate-adapter/1.1.0",
    sourceSha256: input.sha256,
    targetSha256: S.sha256(pdb),
    chain: base.chain,
    model: base.model,
    sourceFrame: input.frame,
    targetFrame: "pdb-author",
    inputUnits: input.units,
    units: mapped.ranges,
    mapping: mapped.mapping,
    biologicalValidity: "not_established",
  }
  return {
    spec: effective,
    files: {
      ...extra,
      "mapping_source.cif": text,
      "mapping_source_report.json": S.canonical(source) + "\n",
      "coordinate_mapping.json": S.canonical(audit) + "\n",
    },
  }
}
