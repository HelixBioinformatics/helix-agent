"""Offline behavioral contracts. Scheduler outputs are fixtures, subprocesses are real.
Only captured PENDING312 is primary; FAILED53 transition below is explicitly synthetic.
"""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
DEFAULT_SOURCE = BASE / 'remote_runner.py.txt'
if not DEFAULT_SOURCE.exists():
    DEFAULT_SOURCE = BASE.parents[1] / 'src/trp/remote_runner.py.txt'
SOURCE = Path(os.environ.get('HELIX_NATIVE_RUNNER_UNDER_TEST', DEFAULT_SOURCE))
loader = importlib.machinery.SourceFileLoader('native_controller_staged', str(SOURCE))
runner = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(runner)
# Public captured AGG-13 PENDING record; no original author coordinates or secrets.
CAPTURED = {'id': '312', 'nodes': None, 'source': 'JobId=312 JobName=nf-GEOMETRY UserId=ubuntu(1000) GroupId=ubuntu(1000) MCS_label=N/A Priority=1 Nice=0 Account=(null) QOS=(null) JobState=PENDING Reason=InvalidAccount Dependency=(null) Requeue=0 Restarts=0 BatchFlag=1 Reboot=0 ExitCode=0:0 RunTime=00:00:00 TimeLimit=00:03:00 TimeMin=N/A SubmitTime=2026-10-13T06:20:23 EligibleTime=2026-10-13T06:20:23 AccrueTime=2026-10-13T06:20:23 StartTime=Unknown EndTime=Unknown Deadline=N/A SuspendTime=None SecsPreSuspend=0 LastSchedEval=2026-10-13T06:20:24 Scheduler=Main Partition=helix AllocNode:Sid=helix-head:84149 ReqNodeList=helix-worker2 ExcNodeList=(null) NodeList= NumNodes=1 NumCPUs=2 NumTasks=1 CPUs/Task=2 ReqB:S:C:T=0:0:*:* ReqTRES=cpu=2,mem=2G,node=1,billing=2 AllocTRES=(null) Socks/Node=* NtasksPerN:B:S:C=0:0:*:* CoreSpec=* MinCPUsNode=2 MinMemoryNode=2G MinTmpDiskNode=0 Features=(null) DelayBoot=00:00:00 OverSubscribe=OK Contiguous=0 Licenses=(null) Network=(null) Command=.command.run WorkDir=/shared/helix-strict/hrsb40f55c1826c4c12/remote/trp-8703dfca7b1a-a8a4d2eb-8601-4c0a-a1c9-ba96d1abcf87/dry-run/work/e0/5e1d06623358bd7909bef90d3c33f3 Comment=helix:a8a4d2eb-8601-4c0a-a1c9-ba96d1abcf87  StdErr=/shared/helix-strict/hrsb40f55c1826c4c12/remote/trp-8703dfca7b1a-a8a4d2eb-8601-4c0a-a1c9-ba96d1abcf87/dry-run/work/e0/5e1d06623358bd7909bef90d3c33f3/.command.log StdIn=/dev/null StdOut=/shared/helix-strict/hrsb40f55c1826c4c12/remote/trp-8703dfca7b1a-a8a4d2eb-8601-4c0a-a1c9-ba96d1abcf87/dry-run/work/e0/5e1d06623358bd7909bef90d3c33f3/.command.log Power= TresPerTask=cpu:2', 'state': 'PENDING'}
# CI UIDs can differ. Only the owner UID token is adapted to the test process.
CAPTURED['source'] = CAPTURED['source'].replace('ubuntu(1000)', f'synthetic({os.getuid()})')
OWNER = 'a8a4d2eb-8601-4c0a-a1c9-ba96d1abcf87'
REQ = {'id': OWNER, 'digest': 'a'*64, 'target': {'root': '/unused', 'version': runner.VERSION}}


def native(job='312', state='PENDING', exit_code='0:0', owner=OWNER, reason='InvalidAccount', uid=None, root=None):
    uid = os.getuid() if uid is None else uid
    work = str(root / 'dry-run/work/e0/task') if root else '/synthetic/stub/work'
    return (f'JobId={job} JobName=nf-GEOMETRY UserId=synthetic({uid}) GroupId=synthetic({uid}) '
            f'JobState={state} ExitCode={exit_code} Reason={reason} WorkDir={work} '
            f'Comment=helix:{owner} NodeList= NumCPUs=2')


class Scheduler:
    def __init__(self, root):
        self.root, self.active, self.raw = root, True, native(root=root)
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[0] == 'squeue':
            text = f'312|helix:{OWNER}|PENDING|nf-GEOMETRY|\n' if self.active else ''
            return subprocess.CompletedProcess(argv, 0, text, '')
        if argv[:3] == ['scontrol', 'show', 'job']:
            return subprocess.CompletedProcess(argv, 0 if self.raw else 1, self.raw, '' if self.raw else 'Invalid job id specified')
        raise AssertionError('Unexpected scheduler command: ' + repr(argv))


class TrackingContracts(unittest.TestCase):
    def test_observed_job_survives_empty_queue_and_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); scheduler = Scheduler(root)
            with patch.object(runner, 'invoke', side_effect=scheduler):
                runner.snapshot_jobs(REQ, root)
                scheduler.active = False
                scheduler.raw = native(state='FAILED', exit_code='53:0', reason='NonZeroExitCode', root=root)
                runner.snapshot_jobs(REQ, root)
            observations = [json.loads(line) for line in (root/'remote-native-jobs.jsonl').read_text().splitlines()]
            latest = {row['id']: row for snapshot in observations for row in snapshot['records']}
            self.assertEqual(latest['312']['state'], 'FAILED', 'Observed job must not disappear with squeue/traces')
            self.assertIn('ExitCode=53:0', latest['312']['source'])
            self.assertEqual([argv[3] for argv in scheduler.calls if argv[:3]==['scontrol','show','job']], ['312','312'])

    def test_scontrol_transport_timeout_cannot_erase_seen_owned_queue_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root)
            def invoke(argv,**kwargs):
                if argv[0]=='scontrol': raise subprocess.TimeoutExpired(argv,20)
                return scheduler(argv,**kwargs)
            with patch.object(runner,'invoke',side_effect=invoke):
                with self.assertRaises(subprocess.TimeoutExpired): runner.snapshot_jobs(REQ,root,'stub')
            actual=runner.native_status(REQ,root)
            self.assertEqual(actual['stateUnknown'],['312'])
            self.assertEqual(actual['nativeFailures'],[])
            self.assertEqual(actual['nativeJobs'][0]['queueState'],'PENDING')

    def test_captured_pending_only_migrates_after_owner_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root)
            (root/'remote-native-jobs.jsonl').write_text(json.dumps({'at':'2026-10-13T06:20:48Z','records':[CAPTURED]})+'\n')
            scheduler.active=False
            scheduler.raw=native(state='FAILED',exit_code='53:0',root=root)
            with patch.object(runner, 'invoke', side_effect=scheduler):
                runner.snapshot_jobs(REQ,root,'stub')
            actual=runner.native_status(REQ,root)
            self.assertEqual(actual['nativeFailures'][0]['exitCode'],'53:0')
            self.assertEqual(actual['nativeFailures'][0]['traversal'],'stub')
            self.assertEqual(actual['stateUnknown'],[])

    def test_missing_record_stays_unknown_and_keeps_earlier_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root)
            with patch.object(runner,'invoke',side_effect=scheduler):
                runner.snapshot_jobs(REQ,root,'stub')
                scheduler.active=False; scheduler.raw=''
                runner.snapshot_jobs(REQ,root,'stub')
            actual=runner.native_status(REQ,root)
            self.assertEqual(actual['stateUnknown'],['312'])
            self.assertEqual(actual['nativeFailures'],[])
            self.assertEqual(actual['nativeJobs'][0]['state'],'UNKNOWN')
            self.assertEqual(actual['nativeJobs'][0]['previousState'],'PENDING')
            state=json.loads((root/'remote-native-state.json').read_text())
            self.assertIn('JobState=PENDING',state['jobs']['312']['lastConfirmed']['source'])
            self.assertEqual(state['jobs']['312']['ownership'],'confirmed')

    def test_prior_failed53_is_not_erased_by_later_missing_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root)
            scheduler.raw=native(state='FAILED',exit_code='53:0',root=root)
            with patch.object(runner,'invoke',side_effect=scheduler):
                runner.snapshot_jobs(REQ,root,'stub')
                scheduler.active=False; scheduler.raw=''
                runner.snapshot_jobs(REQ,root,'stub')
            actual=runner.native_status(REQ,root)
            self.assertEqual(actual['stateUnknown'],['312'])
            self.assertEqual(actual['nativeFailures'][0]['state'],'FAILED')
            self.assertEqual(actual['nativeFailures'][0]['exitCode'],'53:0')

    def test_foreign_comment_trace_candidate_rejected_before_adoption(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root)
            scheduler.active=False; scheduler.raw=native(owner='b'*36,root=root)
            (root/'trace.tsv').write_text('native_id\tstatus\n312\tSUBMITTED\n')
            with patch.object(runner,'invoke',side_effect=scheduler):
                with self.assertRaisesRegex(ValueError,'ownership differs'):
                    runner.snapshot_jobs(REQ,root,'science')
            self.assertFalse((root/'remote-native-state.json').exists())
            self.assertFalse((root/'remote-native-jobs.jsonl').exists())

    def test_same_comment_wrong_uid_or_jobid_is_rejected(self):
        for raw in [native(uid=os.getuid()+1),native(job='313')]:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                root=Path(directory); scheduler=Scheduler(root); scheduler.raw=raw
                with patch.object(runner,'invoke',side_effect=scheduler):
                    with self.assertRaisesRegex(ValueError,'ownership differs'):
                        runner.snapshot_jobs(REQ,root)

    def test_unconfirmed_missing_trace_id_is_unknown_never_owned_completed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root); scheduler.active=False; scheduler.raw=''
            (root/'trace.tsv').write_text('native_id\tstatus\n312\tCOMPLETED\n')
            with patch.object(runner,'invoke',side_effect=scheduler):
                runner.snapshot_jobs(REQ,root,'science')
            actual=runner.native_status(REQ,root)
            self.assertEqual(actual['nativeJobs'][0]['state'],'UNKNOWN')
            self.assertEqual(actual['nativeJobs'][0]['ownership'],'unconfirmed')
            self.assertEqual(actual['nativeFailures'],[])

    def test_pending_invalid_account_is_not_terminal_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root)
            with patch.object(runner,'invoke',side_effect=scheduler):
                runner.snapshot_jobs(REQ,root,'stub')
            actual=runner.native_status(REQ,root)
            self.assertEqual(actual['nativeFailures'],[])
            self.assertEqual(actual['nativeJobs'][0]['nodes'],'')
            self.assertEqual(actual['nativeJobs'][0]['state'],'PENDING')
            self.assertEqual(actual['nativeJobs'][0]['reason'],'InvalidAccount')

    def test_completed_nonzero_exit_cannot_be_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root); scheduler.raw=native(state='COMPLETED',exit_code='0:9',root=root)
            with patch.object(runner,'invoke',side_effect=scheduler): runner.snapshot_jobs(REQ,root)
            self.assertEqual(runner.native_status(REQ,root)['nativeFailures'][0]['exitCode'],'0:9')

    def test_unchanged_poll_does_not_duplicate_raw_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root)
            with patch.object(runner,'invoke',side_effect=scheduler):
                runner.snapshot_jobs(REQ,root,'stub'); runner.snapshot_jobs(REQ,root,'stub')
            self.assertEqual(len((root/'remote-native-jobs.jsonl').read_text().splitlines()),1)

    def test_approval_binding_and_symlink_tracker_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root)
            with patch.object(runner,'invoke',side_effect=scheduler): runner.snapshot_jobs(REQ,root)
            with patch.object(runner,'invoke',side_effect=scheduler):
                with self.assertRaisesRegex(ValueError,'approval differs'):
                    runner.snapshot_jobs({**REQ,'digest':'b'*64},root)
            original=(root/'remote-native-state.json').read_bytes()
            external=root/'external'; external.write_bytes(original)
            (root/'remote-native-state.json').unlink(); (root/'remote-native-state.json').symlink_to(external)
            with patch.object(runner,'invoke',side_effect=scheduler):
                with self.assertRaises(OSError): runner.snapshot_jobs(REQ,root)
            self.assertEqual(external.read_bytes(),original)

    def test_cancellation_scancels_only_fresh_owned_queue_jobs(self):
        calls=[]
        def invoke(argv,**kwargs):
            calls.append(argv)
            if argv[0]=='squeue':
                text=f'312|helix:{OWNER}|PENDING|own|\n313|helix:foreign|RUNNING|foreign|n\n' if len(calls)==1 else '313|helix:foreign|RUNNING|foreign|n\n'
                return subprocess.CompletedProcess(argv,0,text,'')
            return subprocess.CompletedProcess(argv,0,'','')
        with patch.object(runner,'invoke',side_effect=invoke): actual=runner.cancel_jobs(REQ)
        self.assertTrue(actual['confirmed'])
        self.assertEqual([argv for argv in calls if argv[0]=='scancel'],[['scancel','312']])

    def test_monitor_stops_real_owned_process_early_on_synthetic_failed53(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root); count=0
            def invoke(argv,**kwargs):
                nonlocal count
                if argv[0]=='squeue':
                    count+=1
                    scheduler.active=count==1
                    scheduler.raw=native(state='PENDING' if count==1 else 'FAILED',exit_code='0:0' if count==1 else '53:0',root=root)
                return scheduler(argv,**kwargs)
            code="import pathlib,time; print('ready',flush=True); time.sleep(10); pathlib.Path('escaped-monitor').write_text('wrong')"
            began=time.monotonic()
            with patch.object(runner,'invoke',side_effect=invoke):
                with self.assertRaisesRegex(runner.NativeJobFailure,'Verified native Slurm failure'):
                    runner.process_run(root,[sys.executable,'-c',code],root,20,REQ,'stub')
            self.assertLess(time.monotonic()-began,4)
            self.assertFalse((root/'escaped-monitor').exists())
            self.assertIn('ready',(root/'remote-stdout.log').read_text())
            observation=json.loads((root/'remote-native-failure.json').read_text())
            self.assertEqual(observation['nativeFailures'][0]['exitCode'],'53:0')
            process=json.loads((root/'remote-processes.jsonl').read_text())
            self.assertEqual(process['exitCode'],-15)

    def test_pending_monitor_allows_real_subprocess_to_finish(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root)
            with patch.object(runner,'invoke',side_effect=scheduler):
                result=runner.process_run(root,[sys.executable,'-c',"print('finished')"],root,5,REQ,'stub')
            self.assertEqual(result,'finished\n')
            self.assertFalse((root/'remote-native-failure.json').exists())

    def test_trace_completed_and_missing_native_record_cannot_confirm_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root); scheduler.active=False; scheduler.raw=''
            (root/'trace.tsv').write_text('native_id\tstatus\n312\tCOMPLETED\n313\tCOMPLETED\n')
            with patch.object(runner,'invoke',side_effect=scheduler): runner.snapshot_jobs(REQ,root,'science')
            with self.assertRaisesRegex(ValueError,'completion unknown'): runner.ensure_native_completion(REQ,root,'science')

    def test_success_requires_two_distinct_owned_zero_exit_terminal_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'trace.tsv').write_text('native_id\tstatus\n312\tCOMPLETED\n313\tCOMPLETED\n')
            def invoke(argv,**kwargs):
                if argv[0]=='squeue': return subprocess.CompletedProcess(argv,0,'','')
                return subprocess.CompletedProcess(argv,0,native(job=argv[3],state='COMPLETED',root=root),'')
            with patch.object(runner,'invoke',side_effect=invoke): runner.snapshot_jobs(REQ,root,'science')
            runner.ensure_native_completion(REQ,root,'science')
            (root/'trace.tsv').write_text('native_id\tstatus\n312\tCOMPLETED\n312\tCOMPLETED\n')
            with self.assertRaisesRegex(ValueError,'two distinct'): runner.ensure_native_completion(REQ,root,'science')

    def test_controller_preserves_failed_signal53_after_owned_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); scheduler=Scheduler(root)
            scheduler.raw=native(state='FAILED',exit_code='0:53',root=root)
            (root/'execution.json').write_text('{"container":"synthetic-image"}')
            req={**REQ,'budget':{'wallSeconds':480}}
            def invoke(argv,**kwargs):
                if argv[0]=='docker':
                    return subprocess.CompletedProcess(argv,0,'unix:///run/docker.sock' if argv[1]=='context' else 'synthetic-image','')
                if argv==['scontrol','--version']: return subprocess.CompletedProcess(argv,0,'slurm-fixture','')
                return scheduler(argv,**kwargs)
            def process(root,argv,cwd,timeout,req=None,traversal=None):
                if '-version' in argv: return 'nextflow version 25.10.4\n'
                if 'config' in argv: return 'config\n'
                runner.snapshot_jobs(req,root,'stub')
                (root/'remote-cancel-request.json').write_text('{}')
                raise InterruptedError('External monitor cancelled after native failure')
            with patch.object(runner,'run_root',return_value=root), patch.object(runner,'verify',return_value={'files':{}}), \
                 patch.object(runner,'observe',return_value={'synthetic':'inventory'}), patch.object(runner,'invoke',side_effect=invoke), \
                 patch.object(runner,'process_run',side_effect=process), patch.object(runner.signal,'signal'), \
                 patch.object(runner,'cancel_jobs',return_value={'confirmed':True,'requested':[{'id':'312'}]}) as cancel:
                runner.controller(req)
            terminal=json.loads((root/'remote-terminal.json').read_text())
            self.assertEqual(terminal['status'],'failed')
            self.assertEqual(terminal['nativeFailures'][0]['exitCode'],'0:53')
            self.assertIn('External monitor',terminal['error'])
            cancel.assert_called_once_with(req)
            self.assertTrue(json.loads((root/'remote-job-cancellation.json').read_text())['confirmed'])

    def test_probe_process_without_native_monitor_preserves_existing_interface(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result=runner.process_run(root,[sys.executable,'-c',"print('probe')"],root,5)
            self.assertEqual(result,'probe\n')
            process=json.loads((root/'remote-processes.jsonl').read_text())
            self.assertEqual(process['exitCode'],0)
            self.assertNotIn('monitoredNativeJobs',process)


if __name__=='__main__': unittest.main(verbosity=2)
