#!/usr/bin/env python3
"""Audit new integration outcomes without changing the original campaign."""
import csv, hashlib, json, runpy, sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def load(path):
    return json.loads(path.read_text())

def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

def main():
    freeze = load(HERE / 'inputs/freeze.json')
    amendment = load(HERE / 'inputs-amendment-r2/freeze.json')
    checks, results = [], {}
    def require(name, condition, detail=None):
        checks.append({'name':name,'ok':bool(condition),'detail':detail})
        if not condition:
            raise ValueError(name + ': ' + str(detail))
    for name, digest in freeze['sourceHashes'].items():
        require('frozen-source:' + name, sha(ROOT / name) == digest)
    for name, digest in amendment['sourceHashes'].items():
        require('amended-frozen-source:' + name, sha(ROOT / name) == digest)
    trusted_path = ROOT / 'packages/helix/src/trp/verify_bundle.py.txt'
    trusted = runpy.run_path(str(trusted_path),run_name='trusted_new_default')
    require('amendment-terminal',load(HERE / 'outcomes-amendment-r2/terminal.json')['allFrozenCasesObserved'])
    initial_failure = load(HERE / 'outcomes/POST-02-native-cancellation/harness-prelaunch-failure.json')
    require('initial-harness-failure-preserved',initial_failure['nativeJobsSubmitted']==0 and initial_failure['clientStarted'] is False)
    old_parse = HERE / 'outcomes-amendment/POST-03-native-cancellation-1000'
    old_recovery = load(old_parse / 'recovery.json')
    old_base = old_parse / 'recovered' / Path(load(old_parse / 'dispatch-intent.json')['guest']).name
    old_telemetry = (old_base / 'experiment-telemetry.stdout').read_text()
    require('large-display-parse-failure-preserved',old_recovery['actualExitCode']==1 and not old_recovery['ownedComments'] and 'JSON Parse error' in old_telemetry and 'HELIX_OWNED_UUID:' not in old_telemetry)
    offline = load(HERE / 'offline-large-prepare.json')
    require('durable-preparation-prospectively-verified',offline['verified'] and offline['units']==1000 and offline['runToolCalled'] is False and sha(HERE/'offline-large-prepare.json')==amendment['offlineLargePreparationSha256'])
    for item in [freeze['cases'][0], amendment['cases'][0]]:
        case = item['id']
        local = HERE / ('outcomes' if item['id']=='POST-01-positive' else 'outcomes-amendment-r2') / case
        recovery = load(local / 'recovery.json')
        require('raw-archive:' + case,sha(local / 'actual-allocation-and-supervisor.tar') == recovery['archiveSha256'])
        guest = Path(load(local / 'dispatch-intent.json')['guest']).name
        base = local / 'recovered' / guest
        supervision = load(base / 'supervision.json')
        require('same-observed-exit:' + case,supervision['actualExitCode'] == recovery['actualExitCode'])
        require('owned-cleanup:' + case,not supervision['nativeCleanup']['remaining'] and supervision['controllerAndTracerReaped'] and not supervision['finalCgroup']['cgroup.procs'].strip() and 'populated 0' in supervision['finalCgroup']['cgroup.events'])
        tree = base / 'retained-allocation'
        if not item['faultInjection']:
            bundle = tree / 'export/portable-evidence'
            run = bundle / 'run'
            anchor = sha(bundle / 'manifest.json')
            cold = trusted['verify'](bundle,anchor)  # No legacy option.
            require('positive-default-cold',cold['ok'] and not cold.get('legacyBackendMetadata',False))
            execution = load(run / 'execution.json')
            recorded = load(run / 'run.json')
            events = [json.loads(line) for line in (run / 'events.jsonl').read_text().splitlines()]
            completion = [event for event in events if event['source']=='execution' and event['outcome']=='completed']
            backend = 'trp-slurm-colocated-strict/1.0.0'
            require('positive-backend-consistency',execution['backend'] == recorded['backend'] == completion[0]['detail']['backend'] == backend and len(completion)==1)
            ids = set()
            for name in ['trace.tsv','dry-run/trace.tsv']:
                rows = list(csv.DictReader((run / name).read_text().splitlines(),delimiter='\t'))
                require('positive-two-completed:' + name,len(rows)==2 and all(row['status']=='COMPLETED' and row['exit']=='0' for row in rows))
                ids.update(row['native_id'] for row in rows)
            ledger = load(run / 'remote-native-state.json')
            require('positive-four-owned-native',len(ids)==4 and ids==set(ledger['jobs']) and all(ledger['jobs'][job]['current']['state']=='COMPLETED' and ledger['jobs'][job]['current']['ownership']=='confirmed' and ledger['jobs'][job]['current']['comment']==ledger['comment'] for job in ids))
            require('positive-own-input-gold',sha(run / 'results/geometry.csv') == item['goldCsvSha256'])
            database = tree / 'state/data/helix/helix-local.db'
            before = sha(database)
            with sqlite3.connect(database.resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as connection:
                healthy = connection.execute('PRAGMA quick_check').fetchall()==[('ok',)]
                projects = connection.execute('SELECT COUNT(*) FROM project').fetchone()[0]
            require('positive-real-sqlite',healthy and projects>=1 and sha(database)==before)
            results['positive'] = {'verified':True,'defaultCold':cold,'defaultColdFileCount':cold['files'],
                'manifestSha256':anchor,'backendConsistent':True,'backend':backend,'nativeIds':sorted(ids),
                'fourRealNativeTasks':True,'ownInputGoldEqual':True,'goldCsvSha256':item['goldCsvSha256'],
                'actualExitCode':supervision['actualExitCode'],'elapsedSecondsObserved':supervision['elapsedSeconds'],
                'realPersistentSqlite':True,'sourcePackage':str(bundle.relative_to(ROOT)),
                'supervisionSha256':sha(base / 'supervision.json')}
        else:
            fault = load(local / 'native-fault-external.json')
            require('one-owned-injection',fault['injected'] and fault['attempts']==1 and fault['cancellation']['exitCode']==0 and 'JobState=RUNNING' in fault['before']['stdout'] and 'Comment='+fault['exactOwnerComment'] in fault['before']['stdout'])
            folders = list((tree / 'client/.helix/trp').glob('*'))
            runs = [path for path in folders if path.is_dir() and (path / 'remote-approved.json').is_file() and load(path / 'remote-approved.json')['id']==fault['uuid']]
            require('one-owned-production-run',len(runs)==1)
            run = runs[0]
            require('negative-real-approval-hash-binding',sha(run/'approval.json')==fault['actualLocalApprovalSha256'] and sha(run/'remote-analysis-approval.json')==fault['analysisApprovalSha256'])
            bundle = run / 'evidence'
            location = load(run / 'evidence-location.json')
            cold = trusted['verify'](bundle,location['manifestSha256'])
            require('negative-default-cold',cold['ok'] and cold['status']=='failed' and not cold.get('legacyBackendMetadata',False))
            state = load(run / 'remote-native-state.json')
            current = state['jobs'][fault['job']]['current']
            require('negative-retained-native-terminal',current['state'] in ['CANCELLED','FAILED'] and current['ownership']=='confirmed' and current['comment']==fault['exactOwnerComment'] and current['exitCode']!='0:0')
            require('negative-own-id-binding',state['id']==fault['uuid'] and state['comment']==fault['exactOwnerComment'])
            producer_snapshots = [json.loads(line) for line in (run / 'remote-native-jobs.jsonl').read_text().splitlines()]
            observed = [row for row in producer_snapshots if any(str(record['id'])==fault['job'] and record['state'] in ['CANCELLED','FAILED'] for record in row['records'])]
            require('negative-terminal-retained-after-queue-loss',bool(observed))
            events = [json.loads(line) for line in (run / 'events.jsonl').read_text().splitlines()]
            automatic = [event for event in events if event['source']=='execution' and event['outcome']=='failed-or-rejected']
            require('negative-automatic-failed-event',len(automatic)==1 and supervision['actualExitCode']!=0)
            external_terminal = [row for row in fault['observations'] if any('JobState='+label in row['stdout'] for label in ['CANCELLED','FAILED'])]
            late = load(local / 'native-terminal-live-observation.json')
            late_records = [line for line in late['stdout'].splitlines() if line.startswith('JobId='+fault['job']+' ') and 'Comment='+fault['exactOwnerComment'] in line and any('JobState='+label in line for label in ['CANCELLED','FAILED'])]
            require('negative-independent-late-terminal-confirmation',late['exitCode']==0 and bool(late_records))
            # The bounded 80-query fault watcher saw COMPLETING. Its original
            # output is retained; this later independent observation corroborates
            # the genuine terminal instead of inventing a watcher measurement.
            if not external_terminal:
                external_terminal = [{'at':late['at'],'stdout':late_records[0],'source':'independent later native-terminal-live-observation.json'}]
            require('negative-external-terminal-confirmation',bool(external_terminal))
            requested = stamp(fault['at'])
            results['negative'] = {'verified':True,'actualNativeId':fault['job'],'actualState':current['state'],
                'actualExitCode':current['exitCode'],'exactOwnerComment':fault['exactOwnerComment'],
                'requestAt':fault['at'],'externalTerminalObservedAt':external_terminal[0]['at'],
                'producerTerminalObservedAt':observed[0]['at'],
                'producerObservationDelayMilliseconds':(stamp(observed[0]['at'])-requested).total_seconds()*1000,
                'latencyScope':'Difference between recorded observer timestamps on this head, not an internal scheduler latency bound or P95. Slurm StartTime/EndTime retain seconds resolution.',
                'automaticFailedPackage':True,'defaultCold':cold,'defaultColdFileCount':cold['files'],
                'manifestSha256':location['manifestSha256'],'nativeLedgerFreshSourceConfirmed':True,
                'actualClientExitCode':supervision['actualExitCode'],'elapsedSecondsObserved':supervision['elapsedSeconds'],
                'ownedControllerAndTracerReaped':True,'sourcePackage':str(bundle.relative_to(ROOT)),
                'nativeFaultSha256':sha(local / 'native-fault-external.json'),'lateIndependentTerminalSha256':sha(local/'native-terminal-live-observation.json'),'boundedFaultWatcherTerminalObserved':any('JobState=CANCELLED' in row['stdout'] or 'JobState=FAILED' in row['stdout'] for row in fault['observations']),'nativeLedgerSha256':sha(run / 'remote-native-state.json'),
                'supervisionSha256':sha(base / 'supervision.json'),
                'inducedFaultOnly':True,'physicalFeasibilityLabel':None}
    report = {'schema':'helix-post-campaign-default-integration/1.0','verified':True,
              'auditedAt':datetime.now(timezone.utc).isoformat(),'auditSourceSha256':sha(Path(__file__)),'positive':results['positive'],'negative':results['negative'],
              'checks':checks,'checksPassed':len(checks),'freezeSha256':sha(HERE / 'inputs/freeze.json'),
              'amendmentFreezeSha256':sha(HERE / 'inputs-amendment-r2/freeze.json'),
              'producerCommit':freeze['producerCommit'],'verifierSha256':sha(trusted_path),
              'sourceFrozenCount':len(freeze['sourceHashes']),'amendmentSourceFrozenCount':len(amendment['sourceHashes']),'legacyOptionUsed':False,
              'initialHarnessPrelaunchFailurePreserved':True,'largeDisplayParseFailurePreserved':True,'offlineDurablePreparationVerified':True,'newNativeFailureCaseId':amendment['cases'][0]['id'],
              'original50Changed':False,'reservedScientificMetrics':None,
              'scope':'Two new integration runs after repairs; real co-located client and Slurm worker tasks, synthetic approval, one intentionally cancelled own task. Original resource matrix/calibration/thresholds untouched.'}
    quiescence = load(HERE / 'post-quiescence.json')
    require('three-node-independent-final-quiescence',quiescence['verified'] and len(quiescence['nodes'])==3 and quiescence['allNativeJobsEmpty'] and quiescence['allContainersEmpty'] and quiescence['ownedProcessesEmpty'] and quiescence['controllerCgroupsEmpty'])
    report['postQuiescence']=quiescence
    report['postQuiescenceSha256']=sha(HERE/'post-quiescence.json')
    report['checksPassed']=len(checks)
    (HERE / 'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'verified':True,'positiveNativeIds':results['positive']['nativeIds'],'negativeNativeId':results['negative']['actualNativeId'],'negativeState':results['negative']['actualState'],'checks':len(checks)}))

if __name__=='__main__':
    main()
