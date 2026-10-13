export * as TrpEvidence from "./evidence"

import fs from "node:fs/promises"
import path from "node:path"
import { TrpSpecification as S } from "./specification"
import type { TrpNextflow as N } from "./nextflow"
import { TrpCatalog } from "./catalog"
import VERIFIER from "./verify_bundle.py.txt"

export interface Event {
  sequence: number
  previous: string | null
  at: string
  source: "permission" | "admission" | "protocol" | "approval" | "execution"
  outcome: string
  detail: unknown
}

export async function parent(workspace: string): Promise<string> {
  const root = await fs.realpath(workspace)
  let current = root
  for (const name of [".helix", "trp"]) {
    current = path.join(current, name)
    await fs.mkdir(current, { recursive: true })
    if (!(await fs.lstat(current)).isDirectory() || (await fs.realpath(current)) !== current)
      throw new S.WorkflowError("output-escape", current)
  }
  return current
}

export async function write(directory: string, name: string, value: unknown): Promise<void> {
  await fs.writeFile(path.join(directory, name), S.canonical(value) + "\n", { mode: 0o600 })
}

export function ledger(directory: string) {
  const events: Event[] = []
  return async (source: Event["source"], outcome: string, detail: unknown) => {
    const entry: Event = {
      sequence: events.length,
      previous: events.length ? S.sha256(S.canonical(events.at(-1))) : null,
      at: new Date().toISOString(),
      source,
      outcome,
      detail,
    }
    await fs.appendFile(path.join(directory, "events.jsonl"), S.canonical(entry) + "\n", { mode: 0o600 })
    events.push(entry)
  }
}

/** Every asserted value has a JSON pointer to an actual record. Unknown versions
 * are omitted with an explicit reason; no generative model writes this paragraph. */
export async function methods(directory: string): Promise<void> {
  const read = async (name: string) => JSON.parse(await fs.readFile(path.join(directory, name), "utf8"))
  const spec = await read("specification.json"),
    run = await read("run.json"),
    admission = await read("admission.json")
  const execution = await read("execution.json")
  const catalogue = await read("catalogue.json")
  const index = TrpCatalog.catalog.entries.findIndex((entry) => entry.id === "geometre.geometry")
  const fields: { name: string; artifact: string; pointer: (string | number)[]; value: unknown }[] = [
    {
      name: "protein",
      artifact: "specification.json",
      pointer: ["structure", "value", "pdb"],
      value: spec.structure.value.pdb,
    },
    { name: "chain", artifact: "specification.json", pointer: ["chain", "value"], value: spec.chain.value },
    { name: "model", artifact: "specification.json", pointer: ["model", "value"], value: spec.model.value },
    {
      name: "units",
      artifact: "specification.json",
      pointer: ["units", "value", "ranges"],
      value: spec.units.value.ranges,
    },
    {
      name: "insertions",
      artifact: "specification.json",
      pointer: ["insertions", "value"],
      value: spec.insertions.value,
    },
    {
      name: "coordinate contract",
      artifact: "specification.json",
      pointer: ["units", "value", "contract"],
      value: spec.units.value.contract,
    },
    {
      name: "GeomeTRe revision",
      artifact: "catalogue.json",
      pointer: ["entries", index, "source", "revision"],
      value: catalogue.entries[index].source.revision,
    },
    {
      name: "parameter contract",
      artifact: "catalogue.json",
      pointer: ["entries", index, "parameters"],
      value: catalogue.entries[index].parameters,
    },
    {
      name: "input hash",
      artifact: "specification.json",
      pointer: ["structure", "value", "sha256"],
      value: spec.structure.value.sha256,
    },
    { name: "engine", artifact: "execution.json", pointer: ["engine"], value: execution.engine },
    { name: "image", artifact: "execution.json", pointer: ["container"], value: execution.container },
    { name: "command", artifact: "execution.json", pointer: ["run"], value: execution.run },
    { name: "counts", artifact: "admission.json", pointer: ["demand", "counts"], value: admission.demand.counts },
    {
      name: "storage estimate",
      artifact: "admission.json",
      pointer: ["demand", "workBytes"],
      value: admission.demand.workBytes,
    },
    { name: "status", artifact: "run.json", pointer: ["status"], value: run.status },
  ]
  const software = await read("software.json").catch(() => undefined)
  const structural = await read("structural_report.json").catch(() => undefined)
  const enforcement = await read("enforcement.json").catch(() => undefined)
  const remoteStrict = await read("remote_strict_policy.json").catch(() => undefined)
  if (remoteStrict) {
    fields.push({
      name: "co-located Slurm transport",
      artifact: "execution.json",
      pointer: ["transport"],
      value: execution.transport,
    })
    fields.push({
      name: "remote strict allocation",
      artifact: "remote_strict_policy.json",
      pointer: [],
      value: remoteStrict,
    })
    fields.push({ name: "worker input staging", artifact: "execution.json", pointer: ["inputStaging"], value: execution.inputStaging })
    fields.push({ name: "client storage estimate", artifact: "admission.json", pointer: ["demand", "storage"], value: admission.demand.storage })
  }
  if (enforcement)
    fields.push({ name: "resource enforcement", artifact: "enforcement.json", pointer: [], value: enforcement })
  if (structural)
    fields.push({
      name: "structural controls",
      artifact: "structural_report.json",
      pointer: ["summary"],
      value: structural.summary,
    })
  if (software)
    fields.push({
      name: "Nextflow version output",
      artifact: "software.json",
      pointer: ["nextflowVersionOutput"],
      value: software.nextflowVersionOutput,
    })
  if (execution.backend)
    fields.push(
      { name: "execution backend", artifact: "execution.json", pointer: ["backend"], value: execution.backend },
      { name: "remote infrastructure", artifact: "execution.json", pointer: ["target"], value: execution.target },
      {
        name: "numerical profile",
        artifact: "execution.json",
        pointer: ["numericalProfile"],
        value: execution.numericalProfile,
      },
    )
  const limitations = [
    "Author-PDB numbering; supplied units, not repeat detection; experimental B-factor is not pLDDT.",
    remoteStrict
      ? "The real Helix client runs on the verified head. Local Python transport invokes the controller; Slurm executes worker jobs. This is not an SSH transport experiment."
      : execution.backend
        ? "The first-unit geometry zeros are placeholders. Remote Slurm execution is recorded for this run; external annotation and held-out scientific evaluation remain separate requirements."
        : "The first-unit geometry zeros are placeholders. External annotator and held-out evaluation remain separate requirements. This run uses local execution.",
    remoteStrict
      ? "Root-owned policy and kernel receipts bind one XFS project quota covering declared client work/temp/state/cache/export and NFS remote work. Real Helix and Python/Nextflow share 1 CPU/2 GiB/swap-zero controller cgroup; sequential worker containers use 2 CPU/2 GiB. Root sampler records current usage separately from total-run entitlement. Preloaded read-only software/image caches and external root-supervisor records are infrastructure outside workBytes."
      : execution.backend
        ? "Slurm requests resources per job; container observations record effective CPU, memory and swap limits. Controller resources and aggregate storage use estimates and admission, without a hard controller limit or disk quota. Memory is not pooled between workers."
        : enforcement
          ? "Operator XFS quota and cgroup v2 bound controller and task resources. CPU quota is bandwidth, not exclusive cores. Full-run peaks are preserved by the external supervisor."
          : "Host resource admission uses estimates and reservations; aggregate disk quota and controller memory enforcement are unavailable.",
    "Offline verification checks bytes and declared links, not scientific truth or an authenticated human identity.",
    "Agent provider/model/cost are not observed by this workflow; task software is identified by the pinned catalogue reference and image.",
  ]
  await write(directory, "methods.json", {
    version: "trp-methods/1.0.0",
    fields,
    limitations,
    unavailable: software
      ? []
      : ["Nextflow version probe did not complete successfully; see run.json and process records"],
  })
  await fs.writeFile(
    path.join(directory, "methods.md"),
    [
      "# Métodos de la ejecución registrada",
      "",
      `Se procesó ${spec.structure.value.pdb}, cadena autora ${spec.chain.value}, modelo ${spec.model.value}, con ${spec.units.value.ranges.length} unidades suministradas. La entrada se identifica mediante SHA-256 ${spec.structure.value.sha256}.`,
      "",
      `El adaptador ${execution.engine} generó la orden ${JSON.stringify(execution.run)} y fijó la imagen ${execution.container}. La revisión de GeomeTRe es ${catalogue.entries[index].source.revision}; su contrato de parámetros es ${JSON.stringify(catalogue.entries[index].parameters)}. Se planificaron dos tareas simuladas y dos reales, sin reintentos; tareas científicas en infraestructura remota: ${admission.demand.counts.remoteScientificCalls}. Estado registrado: ${run.status}.`,
      "",
      software
        ? `Salida observada de la consulta de versión de Nextflow: ${JSON.stringify(software.nextflowVersionOutput)}.`
        : "No se dispone de una consulta de versión de Nextflow completada correctamente.",
      "",
      `La reserva estimada de almacenamiento fue ${admission.demand.workBytes} bytes. Los campos y sus fuentes se encuentran en methods.json; el inventario, el presupuesto, las decisiones y los eventos se conservan en archivos separados.`,
      "",
      ...limitations.map((line) => `- ${line}`),
      "",
    ].join("\n"),
  )
}

/** Copy all run files, including Nextflow work/cache/logs. Internal file symlinks
 * become ordinary copied files; external/directory symlinks and special files fail.
 * Image layers and distribution caches outside this run are declared exclusions. */
export async function pack(directory: string, bundle: N.Bundle, validationBytes: number) {
  const target = path.join(directory, "evidence")
  await fs.mkdir(target, { mode: 0o700 })
  const root = await fs.realpath(directory)
  const files: { path: string; bytes: number; sha256: string; sourceKind: string }[] = []
  async function copy(from: string, relative: string) {
    for (const entry of (await fs.readdir(from, { withFileTypes: true })).sort((a, b) =>
      a.name.localeCompare(b.name),
    )) {
      if (!relative && entry.name === "evidence") continue
      const source = path.join(from, entry.name),
        name = [relative, entry.name].filter(Boolean).join("/")
      if (entry.isDirectory()) {
        await copy(source, name)
        continue
      }
      const resolved = await fs.realpath(source)
      const rel = path.relative(root, resolved)
      if (rel === ".." || rel.startsWith(`..${path.sep}`) || path.isAbsolute(rel) || !(await fs.stat(source)).isFile())
        throw new S.WorkflowError("evidence-escape", name)
      const bytes = await fs.readFile(source),
        destination = path.join(target, "run", name)
      await fs.mkdir(path.dirname(destination), { recursive: true, mode: 0o700 })
      await fs.writeFile(destination, bytes, { flag: "wx", mode: 0o600 })
      files.push({
        path: `run/${name}`,
        bytes: bytes.length,
        sha256: S.sha256(bytes),
        sourceKind: entry.isSymbolicLink() ? "internal-file-symlink-dereferenced" : "file",
      })
    }
  }
  await copy(directory, "")
  await fs.writeFile(path.join(target, "verify.py"), VERIFIER, { flag: "wx", mode: 0o600 })
  files.push({
    path: "verify.py",
    bytes: Buffer.byteLength(VERIFIER),
    sha256: S.sha256(VERIFIER),
    sourceKind: "bundled-verifier",
  })
  const manifest = {
    version: "trp-evidence/1.0.0",
    createdAt: new Date().toISOString(),
    files,
    bundle: {
      engine: S.ENGINE,
      digest: bundle.digest,
      files: Object.fromEntries(Object.entries(bundle.files).map(([n, s]) => [n, S.sha256(s)])),
    },
    countInputs: { validationBytes },
    exclusions: [
      "Docker image layers and shared Nextflow distribution caches are identified, not embedded. Offline verification does not require them; re-execution does.",
      "The evidence directory excludes itself. Each internal symlink is copied as ordinary bytes. No file within the completed run is otherwise omitted.",
    ],
    inputMapping: { declared: bundle.spec.structure.value.path, portable: "run/source.pdb" },
  }
  const content = S.canonical(manifest) + "\n"
  await fs.writeFile(path.join(target, "manifest.json"), content, { flag: "wx", mode: 0o600 })
  return {
    directory: target,
    manifestSha256: S.sha256(content),
    files: files.length,
    bytes: files.reduce((n, item) => n + item.bytes, Buffer.byteLength(content)),
  }
}
