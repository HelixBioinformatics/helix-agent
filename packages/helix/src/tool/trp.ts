import { Effect, Schema } from "effect"
import { TrpCatalog } from "../trp/catalog"
import { TrpSpecification } from "../trp/specification"
import { TrpWorkflow } from "../trp/workflow"
import { TrpResources } from "../trp/resources"
import { TrpStructural } from "../trp/structural"
import { InstanceState } from "../effect/instance-state"
import * as Tool from "./tool"

export const TrpInspectTool = Tool.define(
  "trp_inspect",
  Effect.succeed({
    description:
      "Inspect local mmCIF or PDB with explicit model, author chain and residue frame. Saves a per-instance report with values, thresholds, provenance and separate failed, non-evaluable and non-applicable checks. mmCIF requires Gemmi 0.7.5. Python selection: operator-configured HELIX_TRP_PYTHON, workspace .helix/trp-python/bin/python, then python3. Optional AFDB PAE and API JSON must match sequence, chain, entry and versioned URLs. Default engineering thresholds are pLDDT 70 and max bidirectional interunit PAE 5 angstrom; biological detection accuracy remains unevaluated. This inspection never authorizes execution, certifies a fold, trims residues, or invents a mapping. GeomeTRe execution remains the admitted experimental PDB route through trp_prepare/trp_run.",
    parameters: TrpStructural.Parameters,
    execute: (args: TrpStructural.Parameters, ctx: Tool.Context) =>
      Effect.gen(function* () {
        const directory = yield* InstanceState.directory
        const result = yield* Effect.promise(() => TrpStructural.inspectFiles(args, directory, ctx.abort))
        return {
          title: "TRP structural inspection",
          metadata: { directory: result.directory, manifestSha256: result.manifestSha256 },
          output: JSON.stringify(result, null, 2),
        }
      }),
  }),
)

export const TrpCatalogTool = Tool.define(
  "trp_catalog",
  Effect.succeed({
    description:
      "Inspect the bounded TRP catalogue and specification contract. Executable route: input.structure → pdb.select → geometre.geometry, with input.units → geometre.geometry. GeomeTRe requires supplied units; detection candidates cannot be executed by this route. Use trp_prepare then trp_run; do not bypass their validation or approval using the shell.",
    parameters: Schema.Struct({}),
    execute: () =>
      Effect.succeed({
        title: "TRP catalogue",
        metadata: {},
        output: JSON.stringify(
          {
            version: TrpSpecification.VERSION,
            catalogHash: TrpSpecification.catalogHash,
            entries: TrpCatalog.catalog.entries,
            internalAdapters: ["input.structure", "input.units", "pdb.select"],
            scope:
              "Legacy PDB, explicit model and author chain, positive author residue intervals without insertion codes or alternate locations. Optional coordinateMapping derives author units from matching mmCIF labels or archived residue-level SIFTS/UniProt mappings. GeomeTRe requires at least three supplied units. Experimental B-factor is not pLDDT.",
          },
          null,
          2,
        ),
      }),
  }),
)

export const TrpPrepareTool = Tool.define(
  "trp_prepare",
  Effect.gen(function* () {
    const workflow = yield* TrpWorkflow.Service
    return {
      description:
        "Validate a complete TRP specification against actual PDB bytes and catalogue evidence, and prepare immutable Nextflow code for review. Each parameter requires a declared source. Every edge must explicitly agree on protein, chain, format, numbering, insertion codes, confidence and scale. Optional coordinateMapping supplies hashed mmCIF plus authoritative label_seq_id intervals, or UniProt intervals with a hashed residue-level SIFTS XML archive and accession. Preparation verifies every residue identity and coordinate against the PDB and derives author units automatically. Original sources, mappings and versions are bound to approval and re-read after approval. Existing insertion intervals remain in author numbering. Use pdb/xyz:angstrom;B:angstrom^2 for structure, json/author-residue-interval for units, pdb-author numbering and none confidence. Source structure preserves insertion codes; checked selection and units exclude them. Replaces any previous draft in this session. Supply an explicit budget (CPU, memoryBytes, workBytes, wallSeconds, requireHardStorageLimit and its origin) for human review; omission is a typed refusal. Inventory is observed by the host or the operator-configured SSH/Slurm target (HELIX_TRP_REMOTE), never supplied by the model. Remote target, SSH trust, node placement and numerical profile enter the approval digest; remote memory must fit each task on one worker. Storage is estimated; a hard quota requires a verified operator XFS/cgroup allocation. Each such allocation permits one preparation; a replacement needs a fresh allocation. Does not execute scientific tasks. If invalid, report failed checks and clarify missing information with the user.",
      parameters: Schema.Struct({
        specification: TrpSpecification.Specification,
        budget: Schema.optional(TrpResources.Budget),
        evidence_root: Schema.String.annotate({
          description: "Root of the checkout or evidence package containing the catalogue reference artifacts",
        }),
      }),
      execute: (
        args: { specification: TrpSpecification.Specification; evidence_root: string; budget?: TrpResources.Budget },
        ctx: Tool.Context,
      ) =>
        Effect.gen(function* () {
          const preview = yield* workflow.prepare(args.specification, args.evidence_root, ctx.sessionID, args.budget)
          return {
            title: "TRP specification ready for review",
            metadata: { id: preview.id, digest: preview.digest },
            output: JSON.stringify(preview, null, 2),
          }
        }),
    }
  }),
)

export const TrpRunTool = Tool.define(
  "trp_run",
  Effect.gen(function* () {
    const workflow = yield* TrpWorkflow.Service
    return {
      description:
        "Show the prepared TRP specification, resource reservation, budget and protocol to the user through the question UI, then execute on the reviewed local or operator-configured SSH/Slurm backend. Remote jobs are tracked and cancelled by a run-specific owner-scoped Slurm comment; evidence is retrieved with hashes. Requires the draft id and digest returned by trp_prepare. The model cannot supply approval. Resources are observed again after approval; changed inputs/protocol, rejection or reuse prevent execution. Results, events and an offline-verifiable evidence copy are saved under .helix/trp/. Hard storage limits require an operator XFS/cgroup allocation; unverified limits are rejected.",
      parameters: Schema.Struct({ id: Schema.String, digest: Schema.String }),
      execute: (args: { id: string; digest: string }, ctx: Tool.Context) =>
        Effect.gen(function* () {
          const result = yield* workflow.run(args.id, args.digest, ctx)
          return {
            title: "TRP geometry completed",
            metadata: {
              directory: result.directory,
              digest: result.digest,
              manifestSha256: result.evidence.manifestSha256,
            },
            output: JSON.stringify(result, null, 2),
          }
        }),
    }
  }),
)
