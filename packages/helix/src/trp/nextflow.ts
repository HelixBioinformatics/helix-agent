export * as TrpNextflow from "./nextflow"

import fs from "node:fs/promises"
import path from "node:path"
import { TrpCatalog } from "./catalog"
import { TrpSpecification as S } from "./specification"
import { TrpGraph } from "./graph"
import { TrpStructural } from "./structural"
import { TrpEnforcement } from "./enforcement"
import { TrpCoordinates } from "./coordinates"

export interface Bundle {
  spec: S.Specification
  report: TrpGraph.Report
  files: Record<string, string>
  digest: string
  image: string
}

export const command = [
  "nextflow",
  "-C",
  "nextflow.config",
  "run",
  "main.nf",
  "-ansi-log",
  "false",
  "-with-trace",
  "trace.tsv",
] as const
export const configCommand = ["nextflow", "-C", "nextflow.config", "config", "-flat"] as const
export const dryCommand = [...command, "-stub-run"] as const

/** A caller-provided evidence root makes verification work from a copied checkout too. */
export async function prepare(raw: unknown, evidenceRoot: string, workspace: string): Promise<Bundle> {
  const enforced = await TrpEnforcement.observe(workspace)
  let spec = S.parse(raw)
  const file = await fs.realpath(path.resolve(workspace, spec.structure.value.path))
  const base = await fs.realpath(workspace)
  const relative = path.relative(base, file)
  if (relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative))
    throw new S.WorkflowError("input-escape", "Structure must be inside the current workspace")
  if ((await fs.stat(file)).size > 20_000_000)
    throw new S.WorkflowError("input-size", "Legacy PDB input exceeds the 20 MB adapter limit")
  const bytes = await fs.readFile(file)
  const mapped = await TrpCoordinates.prepare(spec, bytes, workspace)
  spec = mapped.spec
  const report = TrpGraph.validate(spec, bytes)
  if (!report.valid || !report.selected) throw new S.WorkflowError("invalid-composition", JSON.stringify(report))
  const structural = await TrpStructural.legacy(spec, bytes)
  if (!structural.summary.mechanicalAdmission)
    throw new S.WorkflowError("structural-refusal", JSON.stringify(structural))
  const entry = await TrpCatalog.resolve("geometre.geometry", evidenceRoot)
  const image = entry.reference!.image!
  const reference = entry.reference!
  const evidence = await Promise.all(
    [reference.record, ...reference.inputs, ...reference.outputs].map(async (artifact) => {
      const bytes = await fs.readFile(path.join(evidenceRoot, artifact.path))
      if (bytes.length !== artifact.bytes || S.sha256(bytes) !== artifact.sha256)
        throw new S.WorkflowError("reference-changed", artifact.path)
      return { ...artifact, base64: bytes.toString("base64") }
    }),
  )
  const selection = report.selected
  const { selected: _selected, ...publicReport } = report
  const settings = {
    pdb: spec.structure.value.pdb,
    chain: spec.chain.value,
    units: spec.units.value.ranges,
    insertions: spec.insertions.value,
    inputHash: spec.structure.value.sha256,
    selectionHash: S.sha256(selection),
  }
  // Only identifiers accepted by validate() enter DSL text. Free text, paths and
  // parameter provenance remain JSON data, never shell or Groovy expressions.
  const select = spec.graph.nodes.find((node) => node.operation === "pdb.select")!.id.toUpperCase()
  const geometry = spec.graph.nodes.find((node) => node.operation === "geometre.geometry")!.id.toUpperCase()
  const files: Record<string, string> = {
    ...mapped.files,
    "catalogue.json": S.canonical(TrpCatalog.catalog) + "\n",
    "catalogue_evidence.json": S.canonical(evidence) + "\n",
    "execution.json":
      S.canonical({
        engine: S.ENGINE,
        config: configCommand,
        dryRun: dryCommand,
        run: command,
        container: image,
        scientificTasks: 2,
        stubTasks: 2,
      }) + "\n",
    "specification.json": S.canonical(spec) + "\n",
    "validation.json": S.canonical(publicReport) + "\n",
    "structural_report.json": S.canonical(structural) + "\n",
    "structural_catalogue.json": S.canonical(TrpStructural.catalog) + "\n",
    "inspect_structure.py": TrpStructural.SCRIPT,
    "source.pdb": new TextDecoder().decode(bytes),
    "selection.pdb": selection,
    "settings.json": S.canonical(settings) + "\n",
    "trp_select.py": `import hashlib, json, pathlib
s = json.loads(pathlib.Path('settings.json').read_text())
for name, expected in [('source.pdb', s['inputHash']), ('selection.pdb', s['selectionHash'])]:
    if hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() != expected:
        raise ValueError('Approved input changed: ' + name)
pathlib.Path(s['pdb'] + '.pdb').write_bytes(pathlib.Path('selection.pdb').read_bytes())
`,
    "trp_geometry.py": `import hashlib, json, pathlib, subprocess
s = json.loads(pathlib.Path('settings.json').read_text())
name = s['pdb'] + '.pdb'
if hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() != s['selectionHash']:
    raise ValueError('Selected structure changed')
intervals = lambda values: ','.join(str(r['start']) + '_' + str(r['end']) for r in values)
args = ['geometre', 'single', name, s['chain'], 'geometry.csv', intervals(s['units'])]
if s['insertions']:
    args.extend(['-ins_def', intervals(s['insertions'])])
subprocess.run(args, check=True, timeout=120)
if not pathlib.Path('geometry.csv').is_file():
    raise ValueError('GeomeTRe exited without a CSV')
`,
    "main.nf": `nextflow.enable.dsl=2

process ${select} {
    input:
    path source, name: 'source.pdb'
    path selection, name: 'selection.pdb'
    path settings, name: 'settings.json'
    path adapter, name: 'trp_select.py'
    output:
    path '${settings.pdb}.pdb'
    script:
    '''
    python trp_select.py
    '''
    stub:
    '''
    cp selection.pdb ${settings.pdb}.pdb
    '''
}

process ${geometry} {
    publishDir 'results', mode: 'copy', overwrite: false
    input:
    path structure, name: '${settings.pdb}.pdb'
    path settings, name: 'settings.json'
    path adapter, name: 'trp_geometry.py'
    output:
    path 'geometry.csv'
    script:
    '''
    python trp_geometry.py
    '''
    stub:
    '''
    echo 'STUB_ONLY_NO_SCIENTIFIC_RESULT' > geometry.csv
    '''
}

workflow {
    selected = ${select}(file('source.pdb', checkIfExists: true), file('selection.pdb', checkIfExists: true), file('settings.json', checkIfExists: true), file('trp_select.py', checkIfExists: true))
    ${geometry}(selected, file('settings.json', checkIfExists: true), file('trp_geometry.py', checkIfExists: true))
}
`,
    "nextflow.config": `manifest.nextflowVersion = '25.10.4'
process.executor = 'local'
process.container = '${image}'
process.cpus = 2
process.memory = '2 GB'
process.time = '3 min'
process.errorStrategy = 'terminate'
process.maxRetries = 0
process.maxForks = 1
${enforced ? "executor.cpus = 2\nexecutor.memory = '2 GB'\n" : ""}docker.enabled = true
docker.runOptions = '--entrypoint="" --user $(id -u):$(id -g) --network none --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 128 --cpus 2 --tmpfs /tmp:rw,nosuid,size=256m${enforced ? TrpEnforcement.dockerOptions(enforced.config) : ""}'
env.OPENBLAS_NUM_THREADS = '1'
env.OMP_NUM_THREADS = '1'
env.MKL_NUM_THREADS = '1'
`,
  }
  const physical = structural.checks.find((check) => check.id === "fold-plausibility")?.value as Record<
    string,
    unknown
  > | null
  if (physical?.stericDiagnostic) files["steric_diagnostic.py"] = TrpStructural.STERIC_SCRIPT
  if (physical?.surfaceDiagnostic) files["surface_diagnostic.py"] = TrpStructural.SURFACE_SCRIPT
  if (physical?.physicalDiagnostic) files["physical_diagnostic.py"] = TrpStructural.PHYSICAL_SCRIPT
  if (enforced) files["enforcement.json"] = S.canonical(enforced.config) + "\n"
  const digest = bundleDigest(files)
  return { spec, report: publicReport, files, digest, image }
}

export function bundleDigest(files: Record<string, string>): string {
  return S.sha256(
    S.canonical({
      engine: S.ENGINE,
      files: Object.fromEntries(Object.entries(files).map(([name, content]) => [name, S.sha256(content)])),
    }),
  )
}

export async function materialize(bundle: Bundle, directory: string): Promise<void> {
  if (bundleDigest(bundle.files) !== bundle.digest)
    throw new S.WorkflowError("bundle-changed", "Prepared bundle no longer matches the approval digest")
  await fs.mkdir(directory, { recursive: false, mode: 0o700 })
  for (const [name, text] of Object.entries(bundle.files)) {
    if (!/^[a-z][a-z0-9_.]*$/.test(name)) throw new S.WorkflowError("bundle-path", name)
    await fs.writeFile(path.join(directory, name), text, {
      flag: "wx",
      mode: 0o600,
    })
  }
}

export async function verifyMaterialized(bundle: Bundle, directory: string): Promise<void> {
  for (const [name, content] of Object.entries(bundle.files)) {
    const file = path.join(directory, name)
    if (!(await fs.lstat(file)).isFile() || S.sha256(await fs.readFile(file)) !== S.sha256(content)) {
      throw new S.WorkflowError("bundle-changed", `Approved file changed: ${name}`)
    }
  }
}

export function validateGeometry(csv: string, spec: S.Specification) {
  const lines = csv
    .trim()
    .split(/\r?\n/)
    .map((line) => line.split(","))
  const header = "pdb_id,chain,unit_start,unit_end,curvature,twist,twist_hand,pitch,pitch_hand,tmscore,yaw"
  if (lines[0].join(",") !== header || lines.length !== spec.units.value.ranges.length + 3)
    throw new S.WorkflowError("output-shape", "Unexpected geometry CSV header or unit count")
  for (let i = 1; i < lines.length; i++) {
    const row = lines[i]
    if (
      row.length !== 11 ||
      row[0] !== spec.structure.value.pdb ||
      row[1] !== spec.chain.value ||
      row.slice(4).some((v) => !v.trim() || !Number.isFinite(Number(v)))
    )
      throw new S.WorkflowError("output-values", `Invalid identity or numeric values in CSV row ${i}`)
    const range = spec.units.value.ranges[i - 1]
    if (range && (row[2] !== String(range.start) || row[3] !== String(range.end)))
      throw new S.WorkflowError("output-numbering", `Unit boundaries changed in CSV row ${i}`)
    if (range && (Number(row[9]) < 0 || Number(row[9]) > 1))
      throw new S.WorkflowError("output-scale", "TM-score outside [0,1]")
  }
  if (lines.at(-2)![2] !== "mean" || lines.at(-1)![2] !== "std")
    throw new S.WorkflowError("output-summary", "Missing labelled summary rows")
  if (lines[1].slice(4).some((v) => Number(v) !== 0))
    throw new S.WorkflowError("output-placeholder", "Unexpected first-unit placeholder")
  return {
    units: spec.units.value.ranges.length,
    firstUnit: "zero placeholder; not an observed alignment",
    summaries: ["mean", "std"],
    sha256: S.sha256(csv),
  }
}
