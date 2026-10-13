# Native Slurm job tracking candidate

This directory is an offline staging review. No production files, AWS jobs, frozen
campaign data, Word, canonical thesis metadata or scanner files were modified.

## Observed defect and scope

The captured AGG-13 observer saw native job 312 eleven times as PENDING, last at
06:20:48.871979 UTC, with the run UUID in its Comment. Later captured snapshots
retain job 311 and lose 312. A worker daemon report records job312 stdout opening
with ESTALE at06:20:51, IO setup failure and signal53; controller logs corroborate
WTERMSIG53. **There is no captured scontrol FAILED/ExitCode terminal for312.**
The PENDING→FAILED/53:0 fixture is explicitly synthetic. An additional controller
test uses FAILED/0:53 to exercise the signal-code representation. Neither test
changes the historical case outcome or treats this infrastructure incident as a
scientific physical-failure case.

## Candidate behavior

- Persist every queue-owned native ID and its exact UUID before scontrol queries,
  so a query timeout cannot erase an ID that was actually seen.
- Union the persistent IDs, currently owned queue IDs and trace candidates. Query
  each ID even after it leaves squeue and has no Nextflow trace.
- Validate JobId, exact Comment and current UserId before adopting native raw
  sources. Trace-only candidates without native ownership stay unconfirmed.
- Record traversal stub/science/unknown and raw scheduler state, node, reason and
  exit code. Missing native queries remain UNKNOWN and retain previous evidence.
- Keep a proven native failure even after Slurm purges it. PENDING with
  InvalidAccount is a scheduling observation, never a terminal failure.
- Serialize updates with flock. Append only changed native observations to the
  existing JSONL format, reducing duplicate raw output in bounded workspaces.
- Monitor both actual Nextflow traversal processes. A native terminal failure
  stops the separate Nextflow process group and uses existing bounded cancellation
  of freshly observed jobs with this UUID. No submission or retry is introduced.
- Require two distinct owned zero-exit native completion sources for each
  traversal before accepting successful Nextflow output. A true preserved raw
  COMPLETED/0:0 source remains usable after Slurm retention removes its live row;
  UNKNOWN or the Nextflow trace alone cannot establish completion.
- Return additive nativeJobs/nativeFailures/stateUnknown fields. Queue jobs field
  retains its original meaning. Terminal receipts preserve native failure facts.

Native-state ledger stores owner id/digest/Comment and jobs by numeric ID. Each job
has ownership, firstSeenAt, traversals, current and optional lastQueue,
lastConfirmed and failure. Owner-controlled ordinary files and a lock are required.
The approval digest binds the runner bytes, so integration requires new approval
for future work; no historical source bytes or receipts are rewritten.

## Reproduction

Run:

    python3 /tmp/helix-native-job-tracking-stage-20261013/test_native_job_tracking.py

The test file selects the adjacent staged runner; its optional
HELIX_NATIVE_RUNNER_UNDER_TEST override supports the immutable original regression.
Once copied to packages/helix/test/trp/test_remote_native_tracking.py, it selects the
production runner. Only the captured fixture UID token adapts to the local CI UID;
scientific data and real scheduler identifiers are not generated or resubmitted.

The frozen original fails test_observed_job_survives_empty_queue_and_trace because
its latest312 state stays PENDING. See baseline-regression.txt and checks.json.
Existing strict-reader contracts run with this staged runner too. These are offline
contracts and real local subprocess cleanup checks, not a cloud-validation claim.

production.patch changes only remote_runner.py.txt and adds the behavioral test.
Root owns review and eventual application, after all frozen cloud batches finish.
