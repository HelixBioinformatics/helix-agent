#!/usr/bin/env python3
"""Run capability, resizing, text-entry, motion and idle capture fixtures."""
import argparse
import sys
sys.dont_write_bytecode = True
import concurrent.futures
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('helix_capture', HERE / 'run-captures.py')
capture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(capture)
BASE = {'CAPTURE_SOURCE': '../../packages/tui', 'CAPTURE_SCENARIO': 'home', 'CAPTURE_WIDTH': '80', 'CAPTURE_HEIGHT': '24', 'CAPTURE_THEME': 'dark', 'TERM': 'xterm-256color', 'COLORTERM': 'truecolor', 'HELIX_ASCII': '0'}
CASES = {'ascii-home': {'HELIX_ASCII': '1', 'TERM': 'dumb', 'COLORTERM': '', 'CAPTURE_COLOR': '16'}, 'ascii-session': {'HELIX_ASCII': '1', 'TERM': 'dumb', 'COLORTERM': '', 'CAPTURE_COLOR': '16', 'CAPTURE_SCENARIO': 'session'}, 'limited256': {'CAPTURE_COLOR': '256', 'COLORTERM': '', 'CAPTURE_SCENARIO': 'session', 'CAPTURE_WIDTH': '120', 'CAPTURE_HEIGHT': '40'}, 'limited16': {'CAPTURE_COLOR': '16', 'COLORTERM': '', 'CAPTURE_SCENARIO': 'session', 'CAPTURE_WIDTH': '120', 'CAPTURE_HEIGHT': '40'}, 'wcwidth': {'CAPTURE_WIDTH_METHOD': 'wcwidth'}, 'system-home': {'CAPTURE_THEME_NAME': 'system'}, 'system-session': {'CAPTURE_THEME_NAME': 'system', 'CAPTURE_SCENARIO': 'session', 'CAPTURE_WIDTH': '120', 'CAPTURE_HEIGHT': '40'}, 'resize-home': {'CAPTURE_FROM_WIDTH': '160', 'CAPTURE_FROM_HEIGHT': '48', 'CAPTURE_WIDTH': '60', 'CAPTURE_HEIGHT': '20'}, 'resize-session': {'CAPTURE_FROM_WIDTH': '160', 'CAPTURE_FROM_HEIGHT': '48', 'CAPTURE_SCENARIO': 'session'}, 'unicode': {'CAPTURE_INPUT': 'Inspect hígado Δ RNA sample_01 🧬'}, 'paste': {'CAPTURE_PASTE': 'Compare hígado Δ RNA\npaired sample_01 🧬\nNo pipeline execution'}, 'motion': {'CAPTURE_ANIMATIONS': '1', 'CAPTURE_MOTION_SECONDS': '11'}, 'quiet-typing': {'CAPTURE_ANIMATIONS': '1', 'CAPTURE_INPUT': 'Inspect paired inputs', 'CAPTURE_MOTION_SECONDS': '11'}, 'draft-six-lines': {'CAPTURE_WIDTH': '60', 'CAPTURE_HEIGHT': '20', 'CAPTURE_PASTE_SUMMARY': '0', 'CAPTURE_PASTE': 'one: inspect paired FASTQ inputs\ntwo: preserve the current reference\nthree: summarize input filenames\nfour: do not run a pipeline\nfive: report missing pairs\nsix: wait for approval'}, 'permission80-final': {'CAPTURE_SCENARIO': 'permission'}, 'before-idle-home': {'CAPTURE_SOURCE': 'baseline/source', 'CAPTURE_IDLE_PROBE': '1'}, 'before-idle-session': {'CAPTURE_SOURCE': 'baseline/source', 'CAPTURE_IDLE_PROBE': '1', 'CAPTURE_SCENARIO': 'session', 'CAPTURE_WIDTH': '120', 'CAPTURE_HEIGHT': '40'}, 'idle-home': {'CAPTURE_IDLE_PROBE': '1'}, 'idle-session': {'CAPTURE_IDLE_PROBE': '1', 'CAPTURE_SCENARIO': 'session', 'CAPTURE_WIDTH': '120', 'CAPTURE_HEIGHT': '40'}}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cases',nargs='?',help='Comma-separated case names; omitted runs all cases')
    parser.add_argument('--workers',type=int,default=2)
    args=parser.parse_args()
    names=args.cases.split(',') if args.cases else list(CASES)
    if any(name not in CASES for name in names):
        parser.error('Unknown case; choose from '+','.join(CASES))
    if args.workers<1:
        parser.error('workers must be positive')
    baseline=capture.WORK/'baseline'/'source'
    bun,env=capture.prepare_runtime(baseline if any('before-' in n for n in names) else None)
    output=capture.WORK/'captures'/'after-extras'
    output.mkdir(parents=True,exist_ok=True)
    def run(name):
        opts=CASES[name]
        settings={**BASE,**opts,'CAPTURE_OPTIONAL_PLUGINS':'1','CAPTURE_PHASE':'after-extras/'+name}
        code=capture.run_case(bun,env,settings,output/(name+'.log'))
        result={'case':name,'exit':code,'options':opts,'evidence':name+'.log'}
        print(json.dumps(result),flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        current=list(pool.map(run,names))
    report=output/'capture-results.json'
    previous=json.loads(report.read_text()) if report.exists() else []
    updated={r['case']:r for r in previous}
    updated.update({r['case']:r for r in current})
    report.write_text(json.dumps(list(updated.values()),indent=2)+'\n')
    print(f'Complete: {sum(r["exit"]==0 for r in current)} / {len(current)}')
    raise SystemExit(1 if any(r['exit'] for r in current) else 0)

if __name__=='__main__':
    main()
