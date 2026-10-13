import fs from "node:fs/promises"
import path from "node:path"
import { TrpCoordinates as M } from "../../packages/helix/src/trp/coordinates"
import { TrpStructural as C } from "../../packages/helix/src/trp/structural"
import { TrpSpecification as S } from "../../packages/helix/src/trp/specification"
import SIFTS_SCRIPT from "../../packages/helix/src/trp/sifts_residues.py.txt"

const root = path.resolve(import.meta.dir, "../..")
const base = path.join(root, "evaluation/trp/campaign-20261012/mapping-public-contrasts")
const id = process.argv[2]
const oracle = JSON.parse(await fs.readFile(path.join(base, "oracle", id + ".json"), "utf8"))
const fixture = JSON.parse(
  await fs.readFile(path.join(root, "evaluation/trp/development/f3-reference-spec.json"), "utf8"),
)
const source = await fs.readFile(path.join(root, oracle.sources.cif.path), "utf8")
const target = await fs.readFile(path.join(root, oracle.sources.pdb.path), "utf8")
const xml = await fs.readFile(path.join(root, oracle.sources.sifts.xmlPath), "utf8")
const { pdb, chain, accession } = oracle.case
const singleton = (n: number) => ({ start: n, end: n })
const error = (caught: unknown) =>
  caught instanceof Error
    ? { name: caught.name, message: caught.message, code: (caught as any).code ?? null }
    : { message: String(caught) }
const report: any = {
  case: oracle.case,
  version: "public-mapping-production-contrast/1.0.0",
  sourceHashes: { cif: S.sha256(source), pdb: S.sha256(target), sifts: S.sha256(xml) },
  labelOutcomes: [],
}
try {
  report.sifts = {
    status: "mapped",
    value: await C.runParser({ xml, pdb, chain, accession }, undefined, process.env.HELIX_TRP_PYTHON, SIFTS_SCRIPT),
  }
} catch (caught) {
  report.sifts = { status: "rejected", error: error(caught) }
}
let from: C.Report | undefined, to: C.Report | undefined
try {
  from = await C.inspect({
    structure: source,
    options: {
      format: "mmcif",
      model: 1,
      chain,
      frame: "label_seq_id",
      units: oracle.probeLabelPositions.map(singleton),
    },
  })
  to = await C.inspect({
    structure: target,
    options: {
      format: "pdb",
      model: 1,
      chain,
      frame: "auth_seq_id",
      units: oracle.probeAuthorPositions.map(singleton),
    },
  })
  report.inspection = { status: "completed", source: from, target: to }
} catch (caught) {
  report.inspection = { status: "rejected", error: error(caught) }
}
for (const expected of oracle.labelRows) {
  if (!from || !to) {
    report.labelOutcomes.push({ label: expected.label, status: "unavailable-inspection" })
    continue
  }
  try {
    report.labelOutcomes.push({
      label: expected.label,
      status: "mapped",
      value: M.mapUnits(from, to, [singleton(expected.label)]),
    })
  } catch (caught) {
    report.labelOutcomes.push({ label: expected.label, status: "rejected", error: error(caught) })
  }
}
try {
  const origin = {
    kind: "reference",
    reference: oracle.sources.cif.path,
    detail: "Frozen public numbering probes; not biological repeat annotation or held-out evaluation",
  }
  const contract = { ...fixture.units.value.contract, protein: pdb, chain }
  const spec = S.parse({
    ...fixture,
    catalogHash: S.catalogHash,
    intent: { value: "Verify public observed residue numbering correspondences", origin },
    structure: { value: { path: oracle.sources.pdb.path, pdb, sha256: S.sha256(target) }, origin },
    chain: { value: chain, origin },
    model: { value: 1, origin },
    units: { value: { contract, ranges: oracle.probeAuthorPositions.map(singleton) }, origin },
    insertions: { value: [], origin },
    graph: {
      ...fixture.graph,
      edges: fixture.graph.edges.map((edge: any) => ({ ...edge, contract: { ...edge.contract, protein: pdb, chain } })),
    },
    coordinateMapping: {
      value: {
        path: oracle.sources.cif.path,
        sha256: S.sha256(source),
        frame: "uniprot",
        units: oracle.uniprotIntervals,
        sifts: { path: oracle.sources.sifts.xmlPath, sha256: S.sha256(xml), accession },
      },
      origin,
    },
  })
  const prepared = await M.prepare(spec, new TextEncoder().encode(target), root)
  report.prepared = {
    status: "mapped",
    audit: JSON.parse(prepared.files["coordinate_mapping.json"]),
    sifts: JSON.parse(prepared.files["sifts_mapping.json"]),
    effectiveUnits: prepared.spec.units.value.ranges,
  }
} catch (caught) {
  report.prepared = { status: "rejected", error: error(caught) }
}
await fs.mkdir(path.join(base, "reports"), { recursive: true })
await fs.writeFile(path.join(base, "reports", id + ".json"), JSON.stringify(report, null, 2) + "\n")
console.log(
  JSON.stringify({
    id,
    sifts: report.sifts.status,
    labelsMapped: report.labelOutcomes.filter((r: any) => r.status === "mapped").length,
    prepared: report.prepared.status,
  }),
)
