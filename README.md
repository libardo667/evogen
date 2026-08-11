# EvoGen

Agents usually learn within a fixed body. EvoGen changes the body.

EvoGen is an outer-loop capability engineering harness for autonomous agents.
It observes an agent operating in a partially understood environment, converts
repeated failures into evidence-backed capability issues, coordinates isolated
implementation work, and retains only changes that generalize under revealing,
variant, regression, and long-horizon evaluation.

A **generation** is a reproducible version of the complete agent system: source,
models, prompts, tools, memory, policies, capability manifests, configuration,
and build artifacts. EvoGen does not require model-weight training or a genetic
algorithm.

## What exists in this repository

This is a runnable alpha, not only a scaffold. It includes:

- strict Pydantic contracts for generations, trajectories, capabilities, issues,
  specifications, candidates, experiments, and lineage decisions;
- append-only JSONL trajectories with explicit observation, affordance, binding,
  dispatch, receipt, and later-outcome events;
- a content-addressed artifact store and SQLite ledger;
- a conservative reference diagnostician that fails closed into probe work when
  the evidence is insufficient;
- environment investigation and capability specification boundaries;
- isolated Python capability candidates and adversarial static review;
- deterministic retention gates that require issue closure, structural variants,
  regression preservation, long-horizon success, and matched predictions;
- JSON-over-stdio interfaces for substituting real coding-agent roles;
- a Git worktree adapter for real subject repositories;
- a small KAE JSONL normalization adapter; and
- a complete deterministic microworld proof.

## Run the proof

```bash
uv run --frozen --extra dev python scripts/verify.py
```

This single command installs the locked development environment, runs Ruff and
strict mypy, checks the committed schemas, runs the full test suite, reproduces
the deterministic microworld retention result in a disposable workspace, and
checks the diff for whitespace errors.

The demonstration starts with an intentionally impoverished agent. The world
supports inspecting opaque containers, but the baseline agent body exposes only
movement and acquisition of already-visible items.

The complete cycle then:

1. runs the baseline through three independent hidden-container scenarios;
2. records normalized causal trajectories;
3. diagnoses an absent `reveal_contents` effect rather than an execution error;
4. inspects the actual environment operation surface;
5. writes an evidence-backed `inspect_container` capability specification;
6. generates real Python plugin code in an isolated candidate workspace;
7. compiles and reviews the candidate for revealing-case shortcuts;
8. reruns baseline and candidate on one revealing case, three structural
   variants, two regressions, and one longer chain;
9. applies deterministic retention rules; and
10. records the retained generation and lineage.

Expected result:

```text
Revealing success      0% -> 100%
Variant success        0% -> 100%
Regression success   100% -> 100%
Long-horizon success   0% -> 100%
Verdict: retain
```

The workspace contains:

```text
.evogen-demo/
  artifacts/              content-addressed immutable objects
  candidates/             generated candidate source
  traces/                 raw normalized JSONL trajectories
  subjects/               baseline subject configuration
  evogen.sqlite3          generations, runs, issues, experiments, lineage
  cycle-result.json       complete typed result
  report.md               human-readable evidence report
```

## The two planes

```text
runtime plane

world -> observation -> affordances -> decision -> binding -> execution
      -> later causal evidence -> continuity -> next observation
```

```text
evolution plane

trajectories -> diagnosis -> investigation/probe -> capability specification
             -> isolated implementation -> review/evaluation
             -> retain | revise | reject -> next generation
```

The executor does not rewrite itself casually during a run. Candidate changes
are produced outside the runtime plane, evaluated against the unchanged parent,
and promoted only through lineage gates.

## What the reference demo does not prove

The offline demo uses deterministic role implementations so the orchestration,
evidence contracts, code-generation boundary, and retention logic can be tested
without API credentials. It does **not** prove that a general model can yet infer
arbitrary missing capabilities from arbitrary environments.

For open-ended use, replace one or more reference roles with
`JsonStdioRoleBackend`, or implement the protocols in `evogen.adapters`. The
external process receives one typed role packet and must return one typed JSON
result. Candidate deployment authority remains separate from agent authorship.

## Integrating a subject

Inspect installed subjects without loading them, or run the subject-neutral
API 1.1 conformance kit in disposable scratch storage. An explicit doctor
workspace must be a brand-new path; existing paths, symlinks, repositories,
and protected locations are refused:

```bash
evogen subject list
evogen subject doctor microworld
evogen subject doctor microworld --json
```

The doctor checks authority manifests, deterministic capabilities, trajectory
and scenario isolation, candidate workspace safety, evaluation symmetry, and
direct retained-generation materialization. Subject doctor output is
additional evidence only and cannot certify generic checks.

A practical first integration uses observer mode:

1. normalize the subject's trajectory events;
2. publish a generation and capability manifest;
3. expose scenario execution through `SubjectRunner`;
4. expose environment/source investigation through `EnvironmentInvestigator`;
5. create candidates through a project-specific builder or Git worktree; and
6. evaluate them through `ExperimentEvaluator`.

See [docs/contracts.md](docs/contracts.md) and
[docs/kenshi-integration.md](docs/kenshi-integration.md).

## Project status

The codebase completes one honest deterministic end-to-end prototype and
supplies extension boundaries for external roles. It does not yet prove a real
game integration or model-generated diagnosis. Its local cycle is resumable at
completed persisted stage boundaries, with typed receipts and content-addressed
outputs; arbitrary instruction-level crash recovery is not claimed.

For a human-readable view of what is closed, what is next, what can run, and
which claims remain withheld, open the offline
[project evidence cockpit](docs/cockpit/index.html). It is deterministically
rebuilt from the checked-in plan, checkpoint, and reviewed capability narrative:

```bash
python scripts/build_project_cockpit.py
python scripts/build_project_cockpit.py --check
```

The current repository authority and next unstarted bounded goal are recorded
in [docs/INTEGRATION_CHECKPOINT.md](docs/INTEGRATION_CHECKPOINT.md).
The cross-repository delegation and evidence handoff protocol is recorded in
[docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md](docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md).
