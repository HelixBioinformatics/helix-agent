#!/usr/bin/env python3
"""One owner-checked native cancellation after actual approval and admission."""
import argparse, hashlib, json, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allocation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--deadline', type=float, required=True)
    args = parser.parse_args()
    allocation = json.loads(args.allocation.read_text())
    policy = allocation['policy']
    report = {'schema': 'helix-one-owned-native-injection/1.0', 'sourceSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'allocationSha256': hashlib.sha256(args.allocation.read_bytes()).hexdigest(),
              'policySha256': allocation['policySha256'], 'injected': False, 'attempts': 0, 'observations': []}
    def save():
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    save()
    remote = Path(policy['paths']['remoteRoot'])
    client = Path(policy['paths']['clientWorkspace'])
    while time.time() < args.deadline:
        for approved in remote.glob('trp-*/remote-approved.json'):
            try:
                bound = json.loads(approved.read_text())
                if (approved.parent / 'remote-terminal.json').exists():
                    report['notInjectedReason'] = 'The same owned controller became terminal before a scientific RUNNING task could be cancelled; this is not a demonstrated injected negative.'
                    save()
                    return
                scientific = approved.parent / 'remote-analysis-approval.json'
                if not scientific.exists():
                    continue
                analysis = json.loads(scientific.read_text())
                if analysis.get('decision', {}).get('accepted') is not True:
                    continue
                local = client / '.helix/trp' / approved.parent.name.removeprefix('trp-')
                if not (local / 'approval.json').exists():
                    continue
                actual_approval = json.loads((local / 'approval.json').read_text())
                if actual_approval.get('digest') != bound.get('digest'):
                    continue
                owner = 'helix:' + bound['id']
                observation = subprocess.run(['squeue', '-h', '-o', '%i|%T|%j|%k'], capture_output=True, text=True)
                if observation.returncode:
                    continue
                for line in observation.stdout.splitlines():
                    parts = line.split('|')
                    if len(parts) != 4:
                        continue
                    job, state, name, comment = parts
                    if state != 'RUNNING' or name != 'nf-GEOMETRY' or comment != owner or not job.isdigit():
                        continue
                    before = subprocess.run(['scontrol', 'show', 'job', job, '-o'], capture_output=True, text=True)
                    if before.returncode or 'JobState=RUNNING' not in before.stdout or 'Comment=' + owner not in before.stdout:
                        continue
                    report.update({'attempts': 1, 'at': datetime.now(timezone.utc).isoformat(), 'job': job,
                                   'exactOwnerComment': owner, 'uuid': bound['id'], 'before': {'exitCode': before.returncode, 'stdout': before.stdout, 'stderr': before.stderr},
                                   'actualLocalApprovalSha256': hashlib.sha256((local / 'approval.json').read_bytes()).hexdigest(),
                                   'analysisApprovalSha256': hashlib.sha256(scientific.read_bytes()).hexdigest()})
                    save()  # Bind the intent before issuing precisely one scancel.
                    cancelled = subprocess.run(['scancel', job], capture_output=True, text=True)
                    report['cancellation'] = {'exitCode': cancelled.returncode, 'stdout': cancelled.stdout, 'stderr': cancelled.stderr}
                    report['injected'] = cancelled.returncode == 0
                    save()
                    for _ in range(80):
                        terminal = subprocess.run(['scontrol', 'show', 'job', job, '-o'], capture_output=True, text=True)
                        report['observations'].append({'at': datetime.now(timezone.utc).isoformat(), 'exitCode': terminal.returncode, 'stdout': terminal.stdout, 'stderr': terminal.stderr})
                        save()
                        if any('JobState=' + state in terminal.stdout for state in ['CANCELLED', 'FAILED', 'COMPLETED', 'TIMEOUT']):
                            break
                        time.sleep(.1)
                    return
            except (FileNotFoundError, json.JSONDecodeError):
                continue
        time.sleep(.05)
    report['notInjectedReason'] = 'No matching approved and analysis-admitted own scientific GEOMETRY job observed RUNNING before the frozen deadline; never fabricate a native failure or resubmit.'
    save()

if __name__ == '__main__':
    main()
