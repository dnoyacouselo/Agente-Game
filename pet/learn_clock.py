"""Development-only learn termination controls; no product rule or historical file changes.

Clock modes replace only learn's count-done predicate in the ordered morning update.
The remainder is copied from engine.PetAgent._update_goal_ordered at 2e663cde;
tests compare its AST after removing the documented learn-specific block.
"""
import math

from . import engine
from .diag_round13 import DiagPetAgent
from .lifestats import TracedSession

MODES = ('count12', 'clock2', 'clock3', 'no_count')


class LearnClockAgent(DiagPetAgent):
    def __init__(self, seed, world, rules=engine.RULES):
        super().__init__(seed, world, rules)
        self.learn_end_mode = 'count12'

    def _update_goal_ordered(self, day):
        if self.learn_end_mode not in MODES:
            raise ValueError('unknown learn termination mode')
        if self.learn_end_mode in ('count12', 'no_count'):
            old = self.learn_no_count_close
            self.learn_no_count_close = self.learn_end_mode == 'no_count'
            try:
                return super()._update_goal_ordered(day)
            finally:
                self.learn_no_count_close = old
        return self._clock_update(day)

    def _clock_update(self, day):
        """Ordered update; only the learn done predicate differs from engine's method."""
        before = self.goal
        g = self.goal
        if g is not None:
            prog = self.goal_progress(g)
            if prog > g.get('best_progress', -1.0) + 1e-9:
                g['best_progress'] = prog
                g['last_gain_day'] = day
            g['progress'] = prog
            # NEW: do not alter count progress, gains, stall timing or close side effects.
            done = prog >= 1.0
            if g['type'] == 'learn':
                limit = 2 if self.learn_end_mode == 'clock2' else 3
                done = day - g['created_day'] >= limit
            if done:
                self._plan_log(day, 'closed', g, reason='done')
                self._close_goal(day, 'done')
            elif day - g.get('last_gain_day', day) >= engine.core.GOAL_STALL_DAYS:
                self._plan_log(day, 'closed', g, reason='stalled')
                self._close_goal(day, 'stalled')
        cands = self.propose_goals(day)
        pri = {t: p for t, p, _ in cands}
        g = self.goal
        if (g is not None and self.home_interrupt and self.shelter < engine.HOME_INTERRUPT_BELOW
                and g['type'] in engine.LEISURE_GOALS
                and pri.get('improve_home', -math.inf) >= pri.get(g['type'], 0.0)
                + (0.0 if self.emergency_no_margin else engine.core.GOAL_SWITCH_MARGIN)):
            self._plan_log(day, 'ended', g, pri=pri, reason='interrupt')
            self._close_goal(day, 'switched')
            cands = self.propose_goals(day)
        if self.home_foresight and cands:
            cands = self._foresight_filter(cands, day)
        if cands:
            cands.sort(key=lambda x: -x[1])
            best_type, best_pri, best_src = cands[0]
            g = self.goal
            if g is None:
                self.goal = self._new_goal(best_type, best_pri, best_src, day)
            elif day - g['created_day'] < engine.core.GOAL_MIN_DAYS:
                pass
            elif best_type != g['type']:
                cur = next((p for t, p, _ in cands if t == g['type']), 0.0)
                if best_pri >= cur + engine.core.GOAL_SWITCH_MARGIN:
                    self._close_goal(day, 'switched')
                    self.goal = self._new_goal(best_type, best_pri, best_src, day)
            else:
                g['priority'] = best_pri
        if self.rules >= 5 and self.goal is not None and self.goal is not before:
            self.goal['pref_boost'] = round(getattr(self, 'goal_pref_boost', {}).get(self.goal['type'], 0.0), 4)


class LearnClockSession(TracedSession):
    def __init__(self, seed=42, rules=engine.RULES):
        super().__init__(seed, rules)
        self.agent = LearnClockAgent(seed, self.world, rules)
        self.birth_traits = dict(self.agent.traits)
