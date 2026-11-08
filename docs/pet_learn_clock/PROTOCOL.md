# Learn termination: preregistered development diagnosis

Date: 2026-11-02. Base: veroshgd/Agente-Game, commit
2e663cde3f3b3b94295e18d92a26aab7d963c77e. No confirmatory data are used.
This protocol, implementation and tests must be sealed before any new simulated
group effect. Unit tests may use synthetic states and development seed 3001 only.

## One hypothesis and one primary contrast

On B2, with count completion absent in both conditions, allowing learn until
age 3 rather than age 2 days improves reading adaptation:
R1(clock3) - R1(clock2) <= -0.005 (shares, i.e. -0.5 percentage points),
with the upper 95% paired birth-seed bootstrap limit < 0.
R1 is the clear-grown minus hard-grown reading-share difference in read_change
minus the same difference in keep, common days 30-60. Reuse round 11's formula.
This tests a deadline policy, not a pure mediated effect of actual duration.
Even a positive result cannot decompose round 13's -2.03 pp into independent
duration and session-limit components. Failure does not establish a cap effect.

## Four diagnostic conditions

count12: B2 unchanged. no_count: round 13 no_close, unchanged stall exit.
clock2/clock3: first morning with day - created_day >= 2/3 closes learn as done,
using the original _close_goal and thus its done memory and satiation. The clock
predicate replaces count-done, including when count progress is still < 1.
All earlier natural switches and stall exits remain possible. Done has priority
over stalled on the same morning, as in the historical ordered update.
Every other goal retains its original count completion. Progress remains the
original clamped count progress, with original best_progress and last_gain_day.
In no_count, plateau at 1 can therefore still lead to stalled four days later.
No changed weights, memory rates, boredom, home safety or social entry A.

## Paired diagnostic design

Only development birth seeds 3001-3010 and 6001-6010. The original continuation
plus five reseeded continuations (seed * 1000 + rep, rep 1..5), four history cells
(clear/hard x warm/cold), growth 20 days with experimental entries off, common
environment 30 days, then keep/read_change 30 days. The four conditions branch
from identical copies at common day 30. Both clocks are off until that branch.
Existing open plans keep their original created_day; there is no reset.
Average neighbor levels and continuations within each birth seed before
bootstrap (lifestats.describe, 10000 draws, RNG 12345). Never resample hours.
Instrumented and uninstrumented copies must have identical trace fingerprints
AND agent random-generator states in every diagnostic life.

Duration manipulation gate: for each condition/pet, collect learn plans
overlapping the branch window; for each plan measure the time within that
window, including right-censored open plans and left-truncated incoming plans.
Take the mean over these plans (0 if no learn plan), then mean across cells and
continuations within birth seed. For BOTH keep and read_change, clock3-clock2
must have a positive mean and a 95% CI lower bound > 0. This is a restricted
observed plan-span measure, not uncensored mean lifetime. Also report full
closed-plan durations, incoming/open counts, outcomes and plan frequency.
If either duration gate fails: 'duration manipulation not established', even if
the primary R1 contrast passes. No substitution of completed-only duration.

## Existing standard development evaluation and full safety catalogue

Separately run the original validate_social design for ref, none, count12,
clock2, clock3, no_count and a frozen-memory arm of each non-ref/non-none arm.
Here termination modes apply FROM BIRTH, including growth, as a conservative
development/product stress test. It is NOT the matched-state primary contrast.
For each candidate apply the ORIGINAL validate_social.CRITERIA and evaluate
function with candidate/frozen identities changed at runtime only. All P1-P4,
G, R1/R2, L1/L2, N0/N1, H1/H2, M/S/D remain unchanged. ref is round 8's validated
configuration, not B2. Evaluate reference and count12 reproduction per seed
against round 12's saved ref/none/B2 standard effects.

For ref/count12/clock2/clock3/no_count reuse the full round 11 catalogue:
route_life over every v5.ROUTES entry, pair_lives, plastic_lives, matched_lives;
plus safe_job on SAFE_SEEDS (1,42,901,7,123,2024) x SAFE_ITEMS (garden;
garden+book+music). Safety is whole-life AND phase union after trajectory
deduplication, using the historical safety_union. Also union in matched-state
diagnostic lives for the same condition, reporting that combined safety apart.
Do not exclude a failed life or substitute a successful seed. Report all fails.
Standard eligibility requires ALL original criteria, compatibility, combined
safety (zero whole-life failures, no more phase failures than count12), and a
new predeclared keep reading-budget ratio <= 1.5 relative to count12 over the
matched diagnostic window (zero baseline -> fail). This is a proposed budget,
not an old standard. Clocks remain diagnostic controls, not adopted products.

## Records, provenance and stopping

Record daily reading inside/outside learn, S/I and plan/boredom contributions,
memory promote/suppress hours, satiation, hunger/energy, per-life full action
budget, home/condition minima, plan outcomes/progress, seed-level endpoints.
Report R1 for all arms; only clock3-clock2 is the primary contrast. More reading
alone is not adaptation. Report secondary contrasts without changing verdicts.
If primary or safety fails: retain the result, close the round, no tuning.

All tracked base files are hashed before/after, including sim.py, engine.py,
frozen directories, earlier experiments, results, preregistrations and locks.
Never edit/regenerate their manifests or delete their locks. Seal this protocol,
new source and tests before simulation. Store Python/platform and exact seeds.
Write STARTED.lock exclusively before the first trajectory; never remove it,
even after crash. No resume or overwrite; checkpoint each completed stage.
Reject custom seed arguments: only the named development/safe/compatibility
cases may run. No 7001-7060, 7061+, nor paper FINAL blocks 50000-51499,
60000-61499,70000-71499,80000-81499 are simulated as new evidence. No final_*
runner or paper replay is invoked. Existing v1-v6 compatibility fixtures are
replayed only for compatibility, never reported as independent evidence.

Command (from repository root, Python 3.10+, pytest installed):

```bash
PYTHONUTF8=1 python -m pytest tests/test_pet_learn_clock.py
PYTHONUTF8=1 python -m pet.diag_learn_clock --workers 4
```

Default results: docs/pet_learn_clock/run/. Output directories already containing
STARTED.lock or any result/checkpoint are refused. A separate completed.md may
be added after execution; neither sealed protocol nor code is edited afterward.
