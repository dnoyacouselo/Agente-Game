"""Before-run mechanism, isolation, statistics and guard checks. No holdout seeds."""
import ast
import copy
import inspect
import json
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests/fixtures'))
from make_rules_baseline_v5 import behavior_digest
from pet import engine, diag_round13 as DR, validate_read as VR, validate_social as VS
from pet import validate_social_b2 as VB, diag_learn_clock as D
from pet.learn_clock import LearnClockAgent, LearnClockSession


def synthetic(mode, reads=0, created=10):
    with D.patched():
        s = D.new_pet(3001, 'count12')
    s.apply({'kind': 'object', 'value': 'book'})
    a = s.agent
    a.learn_end_mode = mode
    a.goal = a._new_goal('learn', 0.8, 'test', created)
    a.goal.update(best_progress=0, last_gain_day=created)
    a.action_log['read'] += reads
    # Constant priorities isolate completion/stall from legitimate switches.
    a.propose_goals = lambda day: [('learn', 0.8, 'test')]
    a.home_foresight = False
    return a


@pytest.mark.parametrize('mode,limit', [('clock2', 2), ('clock3', 3)])
def test_clock_ignores_count_and_closes_with_original_done_effects(mode, limit):
    a = synthetic(mode, reads=12)
    goal = a.goal
    a._update_goal_ordered(11)
    assert a.goal is goal and a.goal['progress'] == 1
    assert not a.goal_history
    a._update_goal_ordered(10 + limit)
    assert a.goal_history[-1]['outcome'] == 'done'
    assert a.goal_satiation['learn'] == 10 + limit
    assert a.goal_history[-1]['progress'] == 1


def test_clock_can_close_below_twelve_reads_without_fabricating_progress():
    a = synthetic('clock2', reads=2)
    a._update_goal_ordered(12)
    assert a.goal_history[-1]['outcome'] == 'done'
    assert a.goal_history[-1]['progress'] == pytest.approx(2 / 12)
    assert a.action_log['read'] == 2


def test_incoming_plan_keeps_age_and_done_precedes_simultaneous_stall():
    a = synthetic('clock2', created=1)
    a._update_goal_ordered(10)
    assert a.goal_history[-1]['outcome'] == 'done'
    assert a.goal_history[-1]['created_day'] == 1


@pytest.mark.parametrize('mode', ['clock2', 'clock3', 'no_count'])
def test_stall_exit_survives(mode):
    # Adversarial stale last_gain_day also exercises the clock's pre-deadline path.
    a = synthetic(mode, created=10)
    a.goal['last_gain_day'] = 0
    a._update_goal_ordered(11)
    assert a.goal_history[-1]['outcome'] == 'stalled'
    assert a.goal_satiation['learn'] == 11


def test_no_count_still_stalls_four_days_after_saturating_progress():
    a = synthetic('no_count', reads=12)
    a._update_goal_ordered(11)
    assert not a.goal_history
    a._update_goal_ordered(15)
    assert a.goal_history[-1]['outcome'] == 'stalled'
    assert a.goal_satiation['learn'] == 15


def test_natural_switch_and_other_goal_count_completion_are_unchanged():
    a = synthetic('clock3')
    a.propose_goals = lambda day: [('stock_food', 9, 'test'), ('learn', 0.1, 'test')]
    a._update_goal_ordered(12)
    assert a.goal_history[-1]['outcome'] == 'switched'
    assert a.goal['type'] == 'stock_food'
    b = synthetic('clock3')
    b.goal = b._new_goal('see_the_world', 0.8, 'test', 10)
    action, target = b.GOAL_COUNT_TARGET['see_the_world']
    b.action_log[action] += target
    b._update_goal_ordered(11)
    assert b.goal_history[-1]['type'] == 'see_the_world'
    assert b.goal_history[-1]['outcome'] == 'done'


def test_copied_morning_update_differs_only_in_learn_done_predicate():
    old = ast.parse(textwrap.dedent(inspect.getsource(engine.PetAgent._update_goal_ordered)))
    new_source = textwrap.dedent(inspect.getsource(LearnClockAgent._clock_update))
    for name in ('core', 'HOME_INTERRUPT_BELOW', 'LEISURE_GOALS'):
        new_source = new_source.replace('engine.' + name, name)
    new = ast.parse(new_source)
    for tree in (old, new):
        f = tree.body[0]
        f.name = 'update'
        f.body.pop(0)  # docstring
    body = new.body[0].body[2].body
    assert isinstance(body[3], ast.Assign) and body[3].targets[0].id == 'done'
    del body[3:5]  # new done assignment + learn-specific override
    body[3].test = ast.parse('prog >= 1.0', mode='eval').body
    assert ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False)


@pytest.mark.parametrize('mode', ['count12', 'no_count'])
def test_reference_modes_reproduce_historical_agents(mode):
    with D.patched():
        x = D.new_pet(3001, mode)
    saved = (VS.new_pet, VS.ARMS, VS.CATALOGUE_ARMS, VS.CANDIDATE, VS.FROZEN)
    try:
        DR.patch()
        y = DR.new_pet(3001, 'B2')
        y.agent.learn_no_count_close = mode == 'no_count'
        for p in (x, y):
            p.apply({'kind': 'object', 'value': 'book'})
            p.apply({'kind': 'object', 'value': 'garden'})
            VR.run_hours(p, 15 * 24, invite_daily=True)
        assert behavior_digest(x) == behavior_digest(y)
        assert x.agent.rng.getstate() == y.agent.rng.getstate()
    finally:
        VS.new_pet, VS.ARMS, VS.CATALOGUE_ARMS, VS.CANDIDATE, VS.FROZEN = saved


def test_instrumentation_does_not_change_clock_trajectory_or_rng():
    with D.patched():
        x = D.new_pet(3001, 'clock3')
    x.apply({'kind': 'object', 'value': 'book'})
    x.apply({'kind': 'object', 'value': 'garden'})
    y = copy.deepcopy(x)
    DR.run_branch(x, 10, True)
    DR.run_branch(y, 10, False)
    assert behavior_digest(x) == behavior_digest(y)
    assert x.agent.rng.getstate() == y.agent.rng.getstate()


def test_runtime_configuration_is_restored_even_after_exception():
    old = VS.new_pet, VS.ARMS, VS.CATALOGUE_ARMS, VS.CANDIDATE, VS.FROZEN
    with pytest.raises(RuntimeError), D.patched():
        assert VS.new_pet is D.new_pet
        raise RuntimeError('test')
    assert old == (VS.new_pet, VS.ARMS, VS.CATALOGUE_ARMS, VS.CANDIDATE, VS.FROZEN)


def test_censoring_and_incoming_plan_spans_are_included():
    a = synthetic('clock2')
    a.goal_history = [dict(type='learn', created_day=8, closed_day=11, outcome='done', progress=1),
                      dict(type='learn', created_day=1, closed_day=5, outcome='done')]
    a.goal = dict(type='learn', created_day=12)
    rows = D.plan_records(a, 10, 15)
    assert len(rows) == 2
    assert rows[0]['observed_span'] == 1 and rows[0]['incoming']
    assert rows[1]['observed_span'] == 3 and rows[1]['right_censored']


@pytest.mark.parametrize('seed', [7001, 7021, 7041, 7061, 50000, 60000, 70000, 80000])
def test_reserved_and_consumed_birth_blocks_rejected_before_simulation(seed):
    with pytest.raises(ValueError):
        D.diagnostic_job(seed)
    with pytest.raises(ValueError):
        D.standard_job((seed, 'clock2'))
    with pytest.raises(ValueError):
        D.new_pet(seed, 'count12')


def test_run_directory_and_lock_cannot_be_reused(tmp_path):
    seal = D.prepare_run(tmp_path / 'run')
    assert D.verify_seal(seal) == {'original_files_unchanged': True, 'protocol_code_tests_unchanged': True}
    with pytest.raises(FileExistsError):
        D.prepare_run(tmp_path / 'run')
    assert (tmp_path / 'run/STARTED.lock').exists()


def test_artifact_writes_are_exclusive(tmp_path):
    for name, fn in [('result.json', D.write_json), ('raw.json.gz', D.checkpoint)]:
        fn(tmp_path / name, {'original': True})
        original = (tmp_path / name).read_bytes()
        with pytest.raises(FileExistsError):
            fn(tmp_path / name, {'original': False})
        assert (tmp_path / name).read_bytes() == original


def test_defaults_and_criteria_remain_original():
    s = LearnClockSession(3001, 5)
    assert s.agent.learn_end_mode == 'count12'
    assert not s.agent.learn_no_count_close
    assert engine.RULES == 5
    assert VS.CRITERIA['R1_max'] == -0.01
    with pytest.raises(SystemExit):
        D.main(['--seed', '7061'])
