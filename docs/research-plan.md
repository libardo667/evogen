# Research plan

## Primary question

Can a meta-agent observe another agent failing in a partially understood world,
correctly infer that the failure arises from a missing capability rather than
poor use of existing capabilities, formulate the missing abstraction, engineer
it into the agent's body, and demonstrate a general improvement in autonomous
competence?

## Measurements

The project should not optimize only task reward. Useful measurements include:

- human semantic interventions per closed capability issue;
- correct failure-layer classification rate;
- issue-to-spec agreement with held-out human diagnoses;
- revealing-case closure;
- structural-variant generalization;
- regression severity;
- intervention-free runtime horizon;
- repeated deterministic failure rate;
- recovery success;
- commands with ambiguous outcomes;
- capability additions later removed as unsafe or misleading;
- implementation and evaluation cost; and
- lineage depth before competence stops accumulating.

## Staged autonomy

0. Record trajectories only.
1. Propose diagnoses.
2. Write capability specifications.
3. Implement in isolated worktrees.
4. Evaluate in disposable sandboxes.
5. Retain qualifying candidates automatically in the sandbox lineage.
6. Deploy retained generations to a live environment.

KAE should initially stop at level 4. The game actions are not the main risk; the
outer loop can invalidate tests, modify the evaluator, install the wrong native
binary, or specialize to fixtures.

## Experimental comparisons

- human diagnosis versus model diagnosis;
- raw logs versus distilled causal evidence;
- one general model versus role-separated contexts;
- source access versus trace-only diagnosis;
- single revealing case versus explicit variants;
- scalar reward selection versus metric-vector gates;
- ordinary conversational memory versus issue/lineage memory; and
- fixed action space versus evolvable semantic capabilities.
