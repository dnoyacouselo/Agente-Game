"""Run the sealed, development-only protocol in docs/pet_learn_clock/PROTOCOL.md.

python -m pet.diag_learn_clock --workers 4
No custom seeds, final mode, overwrite or resume. Historical files are read-only.
"""
import argparse
import copy
import gzip
import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from multiprocessing import get_context
from pathlib import Path

from . import diag_round13 as DR
from . import lifestats as L
from . import recheck_read_phases as RP
from . import validate_read as VR
from . import validate_social as VS
from .learn_clock import LearnClockSession, MODES

ROOT = Path(__file__).resolve().parents[1]
BASE = '2e663cde3f3b3b94295e18d92a26aab7d963c77e'
SEEDS = tuple(range(3001, 3011)) + tuple(range(6001, 6011))
BRANCHES = ('keep', 'read_change')
CAT_ARMS = ('ref',) + MODES
ARMS = {'ref': {}, 'none': {'no_read_term': True}}
ARMS.update({m: {'entry': 'B2'} for m in MODES})
ARMS.update({m + '_frozen': {'entry': 'B2', 'freeze': True} for m in MODES})
PROTOCOL = ROOT / 'docs/pet_learn_clock/PROTOCOL.md'
SEALED_FILES = ('docs/pet_learn_clock/PROTOCOL.md', 'pet/learn_clock.py',
                'pet/diag_learn_clock.py', 'tests/test_pet_learn_clock.py')


def require_seed(seed, safe=False):
    if seed not in (VR.SAFE_SEEDS if safe else SEEDS):
        raise ValueError('only preregistered development/safe birth seeds are allowed')


def new_pet(seed, arm):
    # Catalogue safe cases are the only extra seed namespace; no FINAL factories.
    if seed not in SEEDS + tuple(VR.SAFE_SEEDS):
        raise ValueError('forbidden birth seed')
    s = VS.configure(LearnClockSession(seed, 5), arm)
    s.agent.learn_end_mode = arm.removesuffix('_frozen') if arm not in ('ref', 'none') else 'count12'
    return s


@contextmanager
def patched():
    keys = ('new_pet', 'ARMS', 'CATALOGUE_ARMS', 'CANDIDATE', 'FROZEN')
    old = {k: getattr(VS, k) for k in keys}
    VS.new_pet, VS.ARMS, VS.CATALOGUE_ARMS = new_pet, ARMS, CAT_ARMS
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(VS, k, v)


def plan_records(agent, start, end):
    records = [dict(g) for g in agent.goal_history]
    if agent.goal is not None:
        records.append(dict(agent.goal, outcome='open'))
    out = []
    for g in records:
        a, b = g['created_day'], g.get('closed_day', end)
        if b < start or a >= end:
            continue
        out.append({'type': g['type'], 'start': a - start,
                    'end': g.get('closed_day', None), 'outcome': g['outcome'],
                    'progress': g.get('progress'), 'incoming': a < start,
                    'right_censored': 'closed_day' not in g,
                    'duration': b - a if 'closed_day' in g else None,
                    'observed_span': max(0, min(b, end) - max(a, start))})
    return out


def diagnostic_job(seed):
    require_seed(seed)
    with patched():
        pets, same, _ = VS.grow(seed, 'count12')
    result = {'seed': seed, 'same_growth': same, 'instrument_ok': True, 'reps': []}
    for rep in range(VS.REPS + 1):
        cur = {}
        for cell, p in pets.items():
            x = copy.deepcopy(p)
            if rep:
                x.agent.rng.seed(seed * 1000 + rep)
            VR.run_hours(x, VS.COMMON1 * 24)
            cur[cell] = x
        conditions = {}
        for mode in MODES:
            conditions[mode] = {}
            for branch in BRANCHES:
                cells = conditions[mode][branch] = {}
                for (book, neighbor), x in cur.items():
                    pair = []
                    for instrument in (True, False):
                        y = copy.deepcopy(x)
                        y.agent.learn_end_mode = mode
                        if branch == 'read_change':
                            y.world.p['book_clarity'] = VS.HARD if book == 'clear' else VS.CLEAR
                        y.phase(branch)
                        start, i0 = y.tick // 24, len(y.trace)
                        days = DR.run_branch(y, VS.COMMON2, instrument)
                        pair.append((y, days))
                    (y, days), (z, _) = pair
                    result['instrument_ok'] &= (L.fingerprint(y.trace) == L.fingerprint(z.trace)
                                               and y.agent.rng.getstate() == z.agent.rng.getstate())
                    rec = L.life_record(y, life_id=f'{mode}|diag|{seed}|rep{rep}|{book}|{neighbor}|{branch}')
                    plans = plan_records(y.agent, start, y.tick // 24)
                    learn = [p for p in plans if p['type'] == 'learn']
                    cells[f'{book}|{neighbor}'] = {
                        'days': days, 'plans': plans, 'metrics': L.metrics(y.trace[i0:]),
                        'read': L.metrics(y.trace[i0:])['read'],
                        'observed_plan_span': VR.mean([p['observed_span'] for p in learn]) if learn else 0.0,
                        'life': VS.slim(rec)}
        result['reps'].append(conditions)
    return result


def standard_job(arg):
    seed, arm = arg
    require_seed(seed)
    with patched():
        return VS.design_job(arg)


def catalogue_job(arg):
    require_seed(arg[0])
    with patched():
        return VS.catalogue_job(arg)


def safe_job(arg):
    seed, items, arm = arg
    require_seed(seed, safe=True)
    if items not in VR.SAFE_ITEMS:
        raise ValueError('unregistered safe-home objects')
    with patched():
        return VS.safe_job(arg)


def records(job, mode, branch):
    return [p for r in job['reps'] for p in r[mode][branch].values()]


def average(job, mode, branch, key):
    return VR.mean([p[key] for p in records(job, mode, branch)])


def book_effect(job, mode, branch):
    return VR.mean([r[mode][branch][f'clear|{n}']['read'] - r[mode][branch][f'hard|{n}']['read']
                    for r in job['reps'] for n in ('warm', 'cold')])


def summarise_diagnostic(jobs):
    jobs = sorted(jobs, key=lambda j: j['seed'])
    r1 = {m: [book_effect(j, m, 'read_change') - book_effect(j, m, 'keep') for j in jobs] for m in MODES}
    contrast = L.describe([a - b for a, b in zip(r1['clock3'], r1['clock2'])])
    spans = {br: L.describe([average(j, 'clock3', br, 'observed_plan_span')
                             - average(j, 'clock2', br, 'observed_plan_span') for j in jobs]) for br in BRANCHES}
    manipulation = all(v['mean'] > 0 and v['ci95'][0] > 0 for v in spans.values())
    effect = contrast['mean'] <= -0.005 and contrast['ci95'][1] < 0
    out = {'seeds': [j['seed'] for j in jobs], 'R1': {m: L.describe(v) for m, v in r1.items()},
           'primary_clock3_minus_clock2': contrast, 'duration_clock3_minus_clock2': spans,
           'duration_manipulation_established': manipulation, 'primary_effect_threshold_met': effect,
           'same_growth': all(j['same_growth'] for j in jobs),
           'instrumentation_pure': all(j['instrument_ok'] for j in jobs), 'conditions': {}}
    out['hypothesis_supported'] = effect and manipulation and out['same_growth'] and out['instrumentation_pure']
    for mode in MODES:
        for br in BRANCHES:
            pets = [p for j in jobs for p in records(j, mode, br)]
            plans = [g for p in pets for g in p['plans'] if g['type'] == 'learn']
            closed = [g['duration'] for g in plans if g['duration'] is not None]
            sat = [d['learn_sat'] > 0 for p in pets for d in p['days']]
            out['conditions'][f'{mode}|{br}'] = {
                'reading_share': L.describe([average(j, mode, br, 'read') for j in jobs]),
                'observed_plan_span': L.describe([average(j, mode, br, 'observed_plan_span') for j in jobs]),
                'closed_duration_mean_descriptive': VR.mean(closed) if closed else None,
                'plans': len(plans), 'outcomes': dict(Counter(p['outcome'] for p in plans)),
                'incoming_plans': sum(p['incoming'] for p in plans),
                'right_censored_plans': sum(p['right_censored'] for p in plans),
                'satiated_day_share': VR.mean(sat),
                'budget': {a: VR.mean([p['metrics']['counts'].get(a, 0) / p['metrics']['hours'] for p in pets])
                           for a in L.CATEGORIES},
                'safety': RP.safety_union([p['life'] for p in pets])}
    baseline = out['conditions']['count12|keep']['reading_share']['mean']
    out['reading_budget_ratio'] = {
        m: out['conditions'][f'{m}|keep']['reading_share']['mean'] / baseline if baseline else None for m in MODES}
    historical = json.loads((ROOT / 'docs/pet_round13/round13_result.json').read_text(encoding='utf-8'))
    out['reproduction_round13'] = {
        m: r1[m] == historical['R1_per_seed'][old] for m, old in (('count12', 'current'), ('no_count', 'no_close'))}
    out['hypothesis_supported'] &= all(out['reproduction_round13'].values())
    return out


def summarize_standard(designs, catalogues, safe, diag_jobs, diag_summary):
    with patched():
        summary = VS.summarise(designs, catalogues, safe, SEEDS)
        verdicts = {}
        for mode in MODES:
            VS.CANDIDATE, VS.FROZEN = mode, mode + '_frozen'
            v = VS.evaluate(summary, SEEDS)
            v['original_criteria_pass'] = all(x is True for k, x in v.items() if not k.startswith('_'))
            v['reading_budget_pass'] = (diag_summary['reading_budget_ratio'][mode] is not None
                                        and diag_summary['reading_budget_ratio'][mode] <= 1.5)
            # Existing union includes full catalogue and standard design. Add matched-state diagnostic lives.
            standard_lives = [m for j in designs if j['arm'] == mode for m in j['lives']]
            standard_lives += [m for j in catalogues if j['arm'] == mode for m in j['lives']]
            standard_lives += [m for m in safe if m['life_id'].startswith(mode + '|')]
            diagnostic_lives = [p['life'] for j in diag_jobs for br in BRANCHES for p in records(j, mode, br)]
            v['combined_safety'] = RP.safety_union(standard_lives + diagnostic_lives)
            verdicts[mode] = v
        baseline_fails = verdicts['count12']['combined_safety']['phase_fails']
        for mode, v in verdicts.items():
            s = v['combined_safety']
            v['combined_safety_pass'] = s['pass'] == s['unique_trajectories'] and s['phase_fails'] <= baseline_fails
            v['eligible_before_compat_and_integrity'] = (v['original_criteria_pass'] and v['reading_budget_pass']
                                                         and v['combined_safety_pass'])
    old = json.loads((ROOT / 'docs/pet_social_b2/social_b2_dev_result.json').read_text(encoding='utf-8'))
    reproduction = {}
    for now, before in (('ref', 'ref'), ('none', 'none'), ('count12', 'B2')):
        reproduction[now] = all(summary[now]['per_seed'][s] == old['per_seed'][before][str(s)] for s in SEEDS)
    return {'criteria_unchanged': VS.CRITERIA, 'reproduction_round12': reproduction, 'verdicts': verdicts,
            'summary': {a: {k: v for k, v in d.items() if k != 'catalogue_fps'} for a, d in summary.items()}}


def hashes(paths):
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


def write_json(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=1)


def checkpoint(path, value):
    with gzip.open(path, 'xt', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, separators=(',', ':'))


def prepare_run(dst):
    # Only the original tracked snapshot is protected; these new files are sealed separately.
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, head], cwd=ROOT, check=True, capture_output=True)
    original = subprocess.check_output(['git', 'ls-tree', '-rz', '--name-only', BASE], cwd=ROOT).decode().rstrip('\0').split('\0')
    subprocess.run(['git', 'diff', '--exit-code', BASE, '--', *original], cwd=ROOT, check=True, capture_output=True)
    dst.mkdir(parents=True, exist_ok=True)
    if any(dst.iterdir()):
        raise FileExistsError('run directory is not empty; no overwrite or resume permitted')
    seal = {'base_commit': BASE, 'source_commit': head, 'utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
            'platform': platform.platform(), 'birth_seeds': SEEDS, 'safe_seeds': VR.SAFE_SEEDS,
            'original_sha256': hashes(original), 'new_sha256': hashes(SEALED_FILES)}
    # Exclusive lock is created before any simulation. Never remove on success or failure.
    write_json(dst / 'STARTED.lock', seal)
    return seal


def verify_seal(seal):
    return {'original_files_unchanged': hashes(seal['original_sha256']) == seal['original_sha256'],
            'protocol_code_tests_unchanged': hashes(seal['new_sha256']) == seal['new_sha256']}


def map_progress(pool, fn, args, stage):
    out = []
    for i, job in enumerate(pool.imap(fn, args, chunksize=1), 1):
        out.append(job)
        print(f'{stage}: {i}/{len(args)}', flush=True)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--out', type=Path, default=ROOT / 'docs/pet_learn_clock/run')
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 8:
        parser.error('--workers must be between 1 and 8')
    seal = prepare_run(args.out)
    try:
        with get_context('spawn').Pool(args.workers) as pool:
            jobs = map_progress(pool, diagnostic_job, SEEDS, 'paired diagnosis')
            checkpoint(args.out / 'diagnostic_raw.json.gz', jobs)
            diagnostic = summarise_diagnostic(jobs)
            write_json(args.out / 'diagnostic_summary.json', diagnostic)
            print(json.dumps({k: diagnostic[k] for k in ('primary_clock3_minus_clock2',
                  'duration_manipulation_established', 'hypothesis_supported')}, ensure_ascii=False), flush=True)
            designs = map_progress(pool, standard_job, [(s, a) for a in ARMS for s in SEEDS], 'standard design')
            checkpoint(args.out / 'standard_raw.json.gz', designs)
            catalogues = map_progress(pool, catalogue_job, [(s, a) for a in CAT_ARMS for s in SEEDS], 'safety catalogue')
            checkpoint(args.out / 'catalogue_raw.json.gz', catalogues)
            safe = map_progress(pool, safe_job, [(s, it, a) for a in CAT_ARMS for s in VR.SAFE_SEEDS
                                                for it in VR.SAFE_ITEMS], 'safe homes')
            checkpoint(args.out / 'safe_raw.json.gz', safe)
        standard = summarize_standard(designs, catalogues, safe, jobs, diagnostic)
        write_json(args.out / 'standard_summary.json', standard)
        compat = L.compat_check()
        integrity = verify_seal(seal)
        for v in standard['verdicts'].values():
            v['eligible'] = (v['eligible_before_compat_and_integrity'] and compat['pass']
                             and all(integrity.values()) and all(standard['reproduction_round12'].values())
                             and all(diagnostic['reproduction_round13'].values())
                             and diagnostic['same_growth'] and diagnostic['instrumentation_pure'])
        report = {'standing': 'development diagnosis only; no product adopted; no confirmatory block used',
                  'diagnostic': diagnostic, 'standard': standard, 'compat': compat, 'integrity': integrity}
        write_json(args.out / 'result.json', report)
        print(json.dumps({'hypothesis_supported': diagnostic['hypothesis_supported'], 'integrity': integrity,
                          'compat': compat, 'eligible': {m: v['eligible'] for m, v in standard['verdicts'].items()}},
                         ensure_ascii=False, indent=1), flush=True)
        if not all(integrity.values()) or not compat['pass'] or not all(standard['reproduction_round12'].values()):
            raise RuntimeError('integrity, compatibility or reference reproduction failed; inspect retained results')
        if not all(diagnostic['reproduction_round13'].values()):
            raise RuntimeError('round 13 reference reproduction failed; inspect retained results')
    except BaseException as exc:
        write_json(args.out / 'FAILED.json', {'error': repr(exc), 'integrity': verify_seal(seal)})
        raise


if __name__ == '__main__':
    main()
