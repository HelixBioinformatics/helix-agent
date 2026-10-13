# Production validation after the frozen campaign

This directory records local checks after the three production amendments were applied at 2026-10-13 16:42:58 UTC. The original campaign, its thresholds, its exports and its denominators were preserved. These checks did not execute AWS, SSH, a language model or scientific jobs.

## Results

| Check | Actual result | Record |
|---|---:|---|
| Functional workflow backend propagation | 2 passed, 14 assertions | `backend-summary.json`, `backend-results/` |
| Backend and cold-verifier compatibility | 9 tests, 24 contrasts passed | `backend-verifier-portable-test-results.json` |
| Mandatory methods, gates and source binding | 7 tests, 56 contrasts passed, including 50 malformed fixtures rejected | `semantic-regression-results.json` |
| Real failed strict exports | 98-file and 86-file packages verify as failed without legacy option | `failed-strict-results.json` |
| Relevant Bun regression, one round | 543 passed, 63 opt-in skipped, 0 failed; 1601 assertions, 57 files | `broad-summary.json`, `broad.log` |
| Type checking | exit 0 | `typecheck-summary.json`, `typecheck.log` |
| Peer-owned native tracking regression | 20 native tests plus 12 existing strict tests passed | `native/summary.json` |

The functional test exercises the actual workflow, tool, Question service, prepared-file verification, resource admission, remote-result parsing and evidence packaging. Its configuration, observation and process boundaries are simulated. It does not demonstrate physical resource enforcement or a real scheduler transition.

The verifier checks load the actual applied production source. The schema name `helix-backend-verifier-staging-test/1.0` remains in the reused backend test report; its `candidateSha256` is the production verifier hash recorded below. The initial backend-verifier report and log are retained; a narrow repetition with the same 9 tests and 24 contrasts replaced a report-only temporary patch path with the archived repository path. Malformed cases are isolated copies with resealed manifests. Their manufactured anchors are test inputs, never replacements for the external anchors of the real exports.

## Sources and environment

| Applied source | SHA-256 |
|---|---|
| `packages/helix/src/trp/workflow.ts` | `986f4b13e1c2661ede6f42114ec23bc4a5e891872a401d1874c992e9ba3b5cc7` |
| `packages/helix/src/trp/verify_bundle.py.txt` | `952e79d5cecae707954ed667d231838569323dffdd068ab43edd770284841eb9` |
| `packages/helix/src/trp/remote_runner.py.txt` | `f2aa0d714848da79726bf1126ed5611e999b941cd0ee653067a901a9873e1805` |
| `packages/helix/test/trp/workflow-backend.test.ts` | `46ead7759736ac5ca4b1aa1fad6c3b1729b9080f6d250e87bab2daad86b011a6` |

Bun was 1.3.14, Python was 3.14.7 and Node was v26.10.0. The Bun checks used `HELIX_TRP_PYTHON=/home/webiwabou/.local/state/helix/freesasa-20261012/venv/bin/python`, with observed Gemmi 0.7.5. The driver removed all inherited `TRP_` and `HELIX_TRP_` variables before setting the pinned interpreter; no inherited live switches were present. Exact commands, environment, wall times and log hashes appear in the per-command JSON records.

The parent owns `source-amendment.json`. Its phase can advance as separate cloud verification completes, so this review's file index excludes that evolving record. Peer-owned files under `native/` are also excluded from this review's owned index and have their own source anchors.

## Historical strict metadata

The original 150-file strict success export records a generic SSH backend in `run.json` and its completion event, while verified `execution.json` declares the strict cohost backend. The raw export remains unchanged. Production rejects it by default. Compatibility requires both an external manifest SHA and the explicit `--allow-legacy-strict-backend` option; successful output reports `legacyBackendMetadata: true`. Unknown or mixed backend mismatches remain rejected with that option.

The ordinary 144-file export, mapped 156-file export, cancelled 143-file export and two negative 25-file exports verify by default. The two actual failed strict packages also verify by default and retain `status: failed`. An additional isolated failed fixture removes optional software metadata and regenerates methods through unchanged production `TrpEvidence.methods`; its 23-field result verifies with an explicit unavailable-version reason. This fixture does not change what the actual failed executions observed.

## Reproduce without overwriting these records

The following cold check only reads the historical bundle and emits JSON to standard output. Run from the repository root with the matching production verifier source hash:

```bash
python3 packages/helix/src/trp/verify_bundle.py.txt \
  evaluation/trp/campaign-20261012/checks/strict-full-client-final-offline/attempt-2/copied-bundle \
  --sha256 a2fb5c236fbac84746aabaee6d44db4bd7844904764fe9aa2741a48f387c78c0 \
  --allow-legacy-strict-backend
```

Omit `--allow-legacy-strict-backend` to reproduce the expected default rejection. Its exit code is 1; this is a passing negative test, not a successful bundle verification.

For the two Python test suites and failed-package compatibility check, copy their scripts to a new directory first. They write reports next to the copied scripts, and use temporary copies of the bundles:

```bash
review_dir=$(mktemp -d /tmp/helix-post-campaign-review.XXXXXX)
cp evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/test_backend_verifier_portable.py "$review_dir/"
cp evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/test_semantic_regression.py "$review_dir/"
cp evaluation/trp/campaign-20261012/checks/post-campaign-production-20261013/check_failed_strict.py "$review_dir/"
python3 "$review_dir/test_backend_verifier_portable.py" > "$review_dir/backend-verifier.log" 2>&1
python3 "$review_dir/test_semantic_regression.py" > "$review_dir/semantic-regression.log" 2>&1
python3 "$review_dir/check_failed_strict.py" > "$review_dir/failed-strict.log" 2>&1
```

The scripts reference this checkout and retained campaign paths explicitly. Moving the checkout requires adjusting their `ROOT` value. The portable backend suite reads the archived combined patch in `checks/backend-metadata-staged-20261013/` only to report its hash; it does not execute that patch. The semantic suite compares against the separately frozen original verifier.

The exact Bun commands run from `packages/helix` were:

```text
bun test test/trp/workflow-backend.test.ts --timeout 60000
bun test test/trp test/bio test/nfcore test/tool/trp-detect.test.ts test/tool/trp-detect-question.test.ts test/tool/trp-predicted.test.ts test/plugin/codex.test.ts --timeout 30000
bun run typecheck
```

Clear inherited `TRP_` and `HELIX_TRP_` variables and set only the pinned interpreter when repeating the local Bun checks. Store any new logs in a new directory. `run_checks.py` refuses to overwrite the original command logs or summaries and should not be rerun in this directory.

## Limits and remaining work

The 63 opt-in tests were not executed by the broad local round. These local checks do not establish scientific correctness, human agreement or cloud execution of the amended native runner. The parent owns the separately frozen final cloud smoke, Word installation and final account stop checks. Expert reference labels, labels for real human turns and a validated physical failure rule remain separate scientific dependencies.
