# Backend metadata correction, staging only

Production and the frozen campaign inputs remain unchanged. `workflow.patch` changes the remote success branch to read `backend` from `fresh.files["execution.json"]` immediately after `N.verifyMaterialized`, then uses that value in the completion event, `run.json` and returned workflow/tool result. Ordinary SSH remains SSH; the optional strict co-located profile remains explicit local Python plus Slurm. The schema versions and field meanings remain unchanged.

`verify_bundle.patch` is a combined diff against the original verifier SHA `86aec3f5034483c94fd814bf39df62e237f26ac91ea90d37dd0617872f80a3f5`. It includes the previously staged mandatory strict methods/prose/gate checks plus backend consistency. Do not apply the old standalone verifier patch in addition to this combined patch.

## Historical compatibility

The new verifier rejects inconsistent run/completion backend metadata by default. Historical strict exports contain the generic `trp-slurm-ssh/1.0.0` family value in both records, while their approved execution and methods correctly declare `trp-slurm-colocated-strict/1.0.0`. These raw bytes are preserved. Compatibility requires both:

- The explicit CLI option `--allow-legacy-strict-backend`.
- A SHA-256 manifest anchor recorded outside the bundle, supplied using `--sha256`.

Only the recognized strict execution with both legacy SSH metadata values is allowed. Unknown backends, mixed mismatches and ordinary SSH inconsistencies remain rejected. Qualified output includes `legacyBackendMetadata: true`; it does not imply the metadata was corrected or authenticate a human or author. There are no experiment IDs or benchmark hashes in product code.

Cold reproduction of the unchanged 150-file historical export, from the repository root:

```sh
python3 /tmp/helix-backend-consistency-20261013/verify_bundle.py.txt \
  evaluation/trp/campaign-20261012/checks/strict-full-client-final-offline/attempt-2/copied-bundle \
  --sha256 a2fb5c236fbac84746aabaee6d44db4bd7844904764fe9aa2741a48f387c78c0 \
  --allow-legacy-strict-backend
```

The same command without the compatibility option must exit with failure. The historical bundled verifier and its trusted frozen source still reproduce the original campaign proof; they are not overwritten.

## Validation

- Functional candidate: two tests, 14 assertions, both pass. The actual workflow, tool adapter, preparation, digest checks, real Question.Service, resource admission, remote lifecycle and evidence pack execute. Only configured target, root-policy observation and OS/process transport boundaries are simulated. No scientific computation, real enforcement, cloud or model call is claimed.
- Red regression on the original workflow body: SSH passes, strict fails after the real tool invocation, returning the generic SSH value instead of the verified strict execution value. One pass and one expected failure demonstrate the test detects the original defect.
- Verifier: nine tests and 24 cases pass. These include default rejection of the historical strict150, explicit anchored qualification, a corrected metadata unit fixture accepted by default, five intact ordinary/mapped/cancel/negative bundles accepted by default, unknown and mixed backend mismatches, required anchor, three semantic gaps and actual CLI output.

The corrected metadata unit fixture is a copy with resealed metadata for the verifier test. It is not a new actual scientific run and is never substituted for historical evidence.

`workflow.runnable.ts` uses the same candidate body with import paths rewritten to original service modules, retaining its own self-export namespace. `workflow.original-runnable.ts` similarly executes the unmodified body for the red regression. `workflow-backend.production.test.ts` is the test prepared for `packages/helix/test/trp/workflow-backend.test.ts`; `test-addition.patch` adds it at that path. Its evidence output is optional via `TRP_BACKEND_TEST_OUTPUT`.

The initial fixture had an unavailable GiB constant and then did not supply strict total entitlement. Those harness issues were corrected without changing admission or enforcement code. The initial import rewrite also pointed the self-export namespace at the original workflow; this was corrected to execute the intended candidate. `summary.json` distinguishes these harness corrections from the genuine original red regression.

## Commands

```sh
python3 /tmp/helix-backend-consistency-20261013/test_backend_verifier.py
```

From `packages/helix`, use the existing pinned Gemmi interpreter:

```sh
HELIX_TRP_PYTHON=/home/webiwabou/.local/state/helix/freesasa-20261012/venv/bin/python \
  bun test --timeout 60000 --preload ./test/preload.ts \
  /tmp/helix-backend-consistency-20261013/workflow-backend.test.ts
```

Use `workflow-backend-original.test.ts` for the expected failing original regression. These are local tests only. Apply production changes only after the root confirms every live original, boundary and supplemental cohort is terminal, and preserve the source freeze before recording the post-campaign correction.

## Failed strict exports

`failed-strict-results.json` records read-only verification of copies of two actual strict failed exports: AGG-13-generous (98 files) and AGG-14-generous (86). Both pass the staged verifier by default, retain `status: failed` and report `legacyBackendMetadata: false`. Their manifest anchors come from automatic `evidence-location.json` sidecars outside the exported bundles. The containing tar files were also hashed against the external recovery records.

Both real failed packages contain the observed software and pre-execution structural report. An additional isolated fixture removes optional software metadata and regenerates methods with the unmodified production `TrpEvidence.methods`: 23 fields, an explicit unavailable-version reason, and failed status still verify. This is a unit test, not a change to what was observed in either actual failure. The structural report belongs to the approved1.4 bundle and remains mandatory; an absent structural report is not made acceptable merely because execution failed.

```sh
python3 /tmp/helix-backend-consistency-20261013/check_failed_strict.py
```
