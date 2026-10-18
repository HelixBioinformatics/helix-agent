#!/usr/bin/env python3
"""Capture the real TUI with mocked SDK/events. Outputs and state stay in tmp/."""
import argparse
import sys
sys.dont_write_bytecode = True
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
WORK = ROOT / 'tmp' / 'tui-identity'
SCENES = ['home', 'session', 'permission', 'question', 'menu', 'theme-menu', 'error', 'selector', 'confirm', 'prompt']
SIZES = [(80, 24), (120, 40), (160, 48), (60, 20)]
_spec = importlib.util.spec_from_file_location('helix_fixture_verification', HERE / 'run-verification.py')
helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helpers)

def prepare_runtime(baseline=None):
    WORK.mkdir(parents=True, exist_ok=True)
    helpers.ensure_dependency_link(WORK / 'node_modules')
    if baseline:
        if not (baseline / 'src').is_dir():
            raise SystemExit('Missing baseline; prepare it first with --prepare-baseline REVISION.')
        helpers.ensure_dependency_link(baseline / 'node_modules')
    shutil.copy2(HERE / 'capture.test.tsx', WORK / 'capture.test.tsx')
    env = os.environ.copy()
    env.update(TERM='xterm-256color', COLORTERM='truecolor', HELIX_ASCII='0')
    for kind in ['data', 'cache', 'config', 'state']:
        path = WORK / 'environment' / ('capture-' + kind)
        path.mkdir(parents=True, exist_ok=True)
        env['XDG_' + kind.upper() + '_HOME'] = str(path)
    return helpers.bun_path(), env

def run_case(bun, env, settings, output_log):
    job_env = {**env, **settings}
    cmd = [bun, '--conditions=browser', 'test', str(WORK / 'capture.test.tsx'), '--preload', '@opentui/solid/preload', '--timeout', '65000']
    try:
        p = subprocess.run(cmd, cwd=ROOT / 'packages' / 'tui', env=job_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90)
        code, log = p.returncode, p.stdout
    except subprocess.TimeoutExpired as error:
        code, log = 124, str(error)
    output_log.parent.mkdir(parents=True, exist_ok=True)
    output_log.write_text(log)
    return code

def sizes(value):
    try:
        result = [tuple(map(int, size.split('x'))) for size in value.split(',')]
        if any(len(size) != 2 or min(size) < 1 for size in result):
            raise ValueError()
        return result
    except ValueError:
        raise argparse.ArgumentTypeError('Use sizes such as 80x24,120x40.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', nargs='?', choices=['before', 'after', 'both'], default='both')
    parser.add_argument('scene_filter', nargs='?', help='Optional comma-separated scene filter')
    parser.add_argument('--scenes', help='Comma-separated scenes')
    parser.add_argument('--sizes', type=sizes)
    parser.add_argument('--themes', help='dark,light; omitted reproduces the recorded 52-case matrix')
    parser.add_argument('--plugins', choices=['stress', 'default'], default='stress', help='stress reproduces the recorded matrix including optional which-key; default respects enabled:false')
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--baseline', default='tmp/tui-identity/baseline/source')
    parser.add_argument('--prepare-baseline', metavar='REVISION', help='Create a missing commit-only baseline and exit')
    args = parser.parse_args()
    baseline = (ROOT / args.baseline).resolve()
    if args.prepare_baseline:
        WORK.mkdir(parents=True, exist_ok=True)
        helpers.prepare_baseline(args.prepare_baseline, baseline)
        return
    if args.workers < 1:
        parser.error('workers must be positive')
    scenes = (args.scenes or args.scene_filter or ','.join(SCENES)).split(',')
    if any(scene not in SCENES for scene in scenes):
        parser.error('Unknown scene; choose from ' + ','.join(SCENES))
    themes = args.themes.split(',') if args.themes else ['dark']
    if any(theme not in ['dark', 'light'] for theme in themes):
        parser.error('Themes must be dark or light')
    dims = args.sizes or SIZES
    grid = [(s,w,h,t) for s in scenes for w,h in dims for t in themes]
    if not args.sizes and not args.themes:
        grid += [(s,120,40,'light') for s in scenes]
        grid += [(s,80,24,'light') for s in scenes if s in ['home','session']]
    phases = ['before','after'] if args.phase == 'both' else [args.phase]
    bun, env = prepare_runtime(baseline if 'before' in phases else None)
    jobs = [(p,s,w,h,t) for p in phases for s,w,h,t in grid]
    def run(job):
        p,s,w,h,t = job
        phase = p + ('-default' if args.plugins == 'default' else '')
        out = WORK / 'captures' / phase
        settings = dict(CAPTURE_SOURCE=str(baseline if p == 'before' else ROOT / 'packages' / 'tui'), CAPTURE_PHASE=phase, CAPTURE_SCENARIO=s, CAPTURE_WIDTH=str(w), CAPTURE_HEIGHT=str(h), CAPTURE_THEME=t, CAPTURE_OPTIONAL_PLUGINS='0' if args.plugins == 'default' else '1')
        code = run_case(bun,env,settings,out / f'{s}-{w}x{h}-{t}.log')
        result = dict(phase=phase,scene=s,width=w,height=h,theme=t,plugins=args.plugins,exit=code)
        print(json.dumps(result),flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(run,jobs))
    for p in phases:
        phase = p + ('-default' if args.plugins == 'default' else '')
        report = WORK / 'captures' / phase / 'capture-results.json'
        current = [r for r in results if r['phase'] == phase]
        previous = json.loads(report.read_text()) if report.exists() else []
        by_key = {(r['scene'],r['width'],r['height'],r['theme']):r for r in previous}
        by_key.update({(r['scene'],r['width'],r['height'],r['theme']):r for r in current})
        report.write_text(json.dumps(list(by_key.values()),indent=2)+'\n')
    print(f'Complete: {sum(r["exit"] == 0 for r in results)} / {len(results)}')
    raise SystemExit(1 if any(r['exit'] for r in results) else 0)

if __name__ == '__main__':
    main()
