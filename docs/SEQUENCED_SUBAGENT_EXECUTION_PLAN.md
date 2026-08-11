# EvoGen sequenced subagent execution plan

Status: checked-in operational companion to
`EVOGEN_KENSHI_OPENTTD_BOUNDED_GOALS.md`

Source plan:

- Drive file ID: `1IcZkzsjmsdtPqxxj4NxSiKWIBzB8In3D`
- Source revision observed: `2026-08-10T21:25:08.835Z`
- Source size observed: 37,532 bytes
- This companion does not replace or weaken the source plan. When they differ,
  the numbered goal, its `Done when`, and its `Do not` clauses in the source
  plan win.

Current execution state:

- Goal 1 local completion commit: `9c8d94c59a95222a719e20fac5a61d2ec712743d`
- Annotated tag: `v0.1.0`
- Alpha source parent: `88c169d46e3eaf5c0b0cc87f31e05c95ea9356b4`
- Local proof: CPython 3.11 and 3.12, Ruff, strict mypy, 20 tests,
  schema/checkpoint freshness, full microworld retention cycle, whitespace,
  and a clean `git clone --no-local` reproduction
- Public remote: `https://github.com/libardo667/evogen`
- Hosted proof: branch run `31439981915` and tag run `31439981992` each passed
  Python 3.11, 3.12, and 3.13 at the exact release commit
- Goal 3 state: completed in the current bounded goal commit
- Next unstarted goal: Goal 4

## 1. What this plan controls

The source plan says to give one goal to a coding agent at a time. This document
keeps that rule and defines how a root agent may use subagents *inside* that one
goal without blurring authorship, authority, evidence, or completion.

The root agent is the only process allowed to:

1. declare a goal started or complete;
2. assign the repository write lock;
3. accept or reject subagent findings;
4. alter the integration checkpoint;
5. make the final goal commit;
6. select or retain an EvoGen candidate; and
7. unlock the next numbered goal.

Subagents increase scrutiny and bounded throughput. They never turn the roadmap
into 49 concurrent tasks.

## 2. Non-negotiable execution rules

1. **One numbered goal is active globally.** No work from the next goal is
   smuggled into the current diff.
2. **Current checkout beats plan memory.** Every goal begins by resolving the
   current branch, commit, dirty status, checkpoint, architecture authority,
   generated authorities, and recent relevant commits.
3. **One writer per repository.** Read-only agents may fan out. Concurrent
   writers require separate worktrees and explicit, disjoint ownership.
4. **Candidate authors do not certify.** The writer's tests are diagnostics.
   Independent review and verification determine acceptance.
5. **Evidence lanes remain separate.** Source, static test, portable, replay,
   headless, built, installed, live, and withheld claims are named separately.
6. **Dispatch is not effect evidence.** A request, receipt, return value, or
   process exit cannot establish a later world effect.
7. **Unknown is not empty.** Missing, truncated, unknown, and complete-empty
   observations retain distinct typed representations.
8. **Generated authority has one owner.** Schemas, catalogs, indexes, and other
   projections are regenerated from source and freshness-tested; they are not
   hand-maintained mirrors.
9. **Cross-repository goals are one transaction.** Each repository records the
   exact counterpart commit. A goal is incomplete while either side refers to
   an uncommitted or mismatched state.
10. **Failures remain evidence.** Rejected candidates, failed experiments,
    malformed role responses, negative probes, and no-change diagnoses are not
    erased to make the lineage look successful.
11. **Live and installation boundaries stay human-visible.** The root pauses at
    every gate the source goal says requires human approval.
12. **Every goal ends in a stop.** After checkpoint, commit, clean-tree proof,
    and handoff, no agent begins the next goal automatically.

## 3. Global goal state machine

```text
UNSTARTED
  -> ORIENTING
  -> ORIENTED
  -> PROOF_DESIGNED
  -> IMPLEMENTING
  -> CANDIDATE_GREEN
  -> INDEPENDENT_REVIEW
  -> VERIFIED
  -> CHECKPOINTED
  -> COMMITTED
  -> STOPPED
```

Allowed reverse transitions:

- `ORIENTING -> UNSTARTED` when repository authority cannot be resolved.
- `INDEPENDENT_REVIEW -> IMPLEMENTING` when review finds a correctable defect.
- `VERIFIED -> IMPLEMENTING` when any required gate fails.
- `CHECKPOINTED -> IMPLEMENTING` when the checkpoint overclaims the evidence.

No transition may skip `INDEPENDENT_REVIEW` for a candidate-producing goal.
No failed state unlocks the next goal.

## 4. Repository locks and workspaces

The root maintains three logical locks:

```text
lock:evogen
lock:kenshi-agent-env
lock:openttd-agent-env
```

Lock modes:

- `read`: any number of read-only agents may inspect a repository.
- `write`: exactly one ordinary writer may edit the checkout.
- `worktree-write`: several candidate writers may edit separate Git worktrees
  only when the goal explicitly asks for isolated candidates.
- `live`: one root-supervised process may install, launch, or control a subject.

Rules:

- A root checkout never hosts two concurrent writers.
- A reviewer never edits the candidate it reviews. Findings return to the root.
- Cross-repository goals take write locks in this order to avoid split-brain:
  `evogen`, `kenshi-agent-env`, `openttd-agent-env`.
- Live runs require clean committed source, exact binary/scenario identity, and
  an explicit rollback path before the `live` lock is granted.

## 5. Standard goal packet

The root creates this packet before delegation:

```yaml
goal_packet:
  goal_id: G02
  title: Give subjects a real plugin boundary
  source_plan_revision: 2026-08-10T21:25:08.835Z
  repositories:
    evogen:
      branch: main
      parent_commit: <full-sha>
      dirty: false
      checkpoint: docs/INTEGRATION_CHECKPOINT.md
  authority_files: []
  behavioral_change: ""
  predicted_observable_effects: []
  falsifiers: []
  evidence_required: []
  withheld_claims: []
  allowed_paths: []
  protected_paths: []
  explicit_do_not: []
  assigned_roles: []
  required_handbacks: []
  full_gate: ""
  stop_condition: ""
```

The packet is immutable after implementation starts. If scope changes, the root
records a revised packet and restarts specification/review rather than silently
broadening the current assignment.

## 6. Reusable subagent roles

### Authority cartographer — read only

Purpose: establish what currently owns the concept and where the plan has
drifted.

Required handback:

- exact checkout and recent relevant commits;
- authority map from source to generated artifacts, tests, and docs;
- current invariants and compatibility surfaces;
- stale or competing authorities;
- files likely to change and files that must not change;
- unresolved questions, with no implementation.

### Proof designer — read only

Purpose: translate `Done when` into executable falsification.

Required handback:

- positive, negative, malformed, stale, and boundary cases;
- evidence class for each claim;
- baseline/candidate symmetry requirements;
- fixtures required before implementation;
- exact expected failing test or missing proof before the change;
- how a superficially successful but invalid implementation would be caught.

### Implementer — one write lock

Purpose: make only the frozen goal change.

Required handback:

- changed-file list and authority migration;
- implementation summary tied to the predicted behavior;
- targeted test results;
- generated artifacts refreshed from their owners;
- remaining uncertainty and any worthwhile follow-on work;
- no certification language.

### Isolated candidate author — worktree write

Purpose: implement a frozen capability specification without access to sealed
answers, held-out evaluators, deployment credentials, or retention authority.

Required handback:

- exact parent generation/worktree commit;
- complete transcript;
- patch and build artifacts;
- resource/time/byte usage;
- self-reported tests clearly labeled author-reported;
- no retain/reject recommendation.

### Adversarial reviewer — read only

Purpose: attack the semantic and authority boundaries of the proposed change.

Required handback:

- blocking/nonblocking findings with file/evidence references;
- hard-coded identifier, expected-answer, scenario, and evaluator leakage audit;
- compatibility/fallback and duplicate-authority audit;
- unknown/empty and receipt/effect collapse audit;
- path-policy and scope audit;
- explicit pass/fail recommendation, but no lineage mutation.

### Verifier and evidence auditor — read only execution

Purpose: independently reproduce the required proof from the candidate state.

Required handback:

- exact commands and exit codes;
- focused and full gate results;
- generated-artifact byte freshness;
- baseline/candidate or before/after evidence where applicable;
- hashes, manifests, run IDs, sequences, and final disposition;
- claims that remain withheld.

### Release recommender — read only

Purpose: synthesize independent review/evaluation artifacts into a typed
recommendation. This role never authors the candidate and never changes the
selection rule.

### Live operator — root-supervised only

Purpose: perform an already approved install/run/rollback procedure.

Required handback:

- approval record;
- process/game/save/scenario identity immediately before dispatch;
- built/staged/installed artifact hashes;
- raw run/crash artifacts;
- later engine evidence and final safe state;
- rollback result.

## 7. Standard intra-goal schedule

```text
Phase A — root orientation
  lock repositories read-only
  resolve checkout/checkpoint/plan/authority
  issue immutable goal packet

Phase B — parallel read-only fan-out
  authority cartographer
  proof designer
  optional provenance/security specialist

Phase C — root synthesis
  reconcile findings
  freeze allowed paths and falsifiers
  assign one writer or isolated candidate worktree

Phase D — implementation
  writer edits
  writer runs focused diagnostics
  writer returns handback

Phase E — parallel independent fan-out
  adversarial reviewer
  verifier/evidence auditor
  optional cross-repository or provenance auditor

Phase F — correction loop
  root decides findings
  writer fixes within frozen scope
  independent roles rerun affected checks

Phase G — root closure
  run authoritative full gate
  update checkpoint with exact evidence and withheld claims
  review final diff
  commit one coherent goal
  prove clean checkpoint mode and clean tree
  stop all subagents
```

Parallelism is optional. The root uses it only when roles are genuinely
independent and the extra handoff creates more evidence than coordination risk.

## 8. Journey I routing — make EvoGen ready

### G01 — Freeze and publish the alpha honestly

- State: complete at public commit `9c8d94c`, tag `v0.1.0`.
- Fan-out used: provenance/history audit, CI/gate audit, independent fresh clone.
- Hosted evidence: both the `main` and `v0.1.0` push matrices passed on Python
  3.11, 3.12, and 3.13.
- Stop: satisfied at the Goal 1 release boundary.

### G02 — Subject plugin boundary

- State: completed in the current bounded goal commit.
- Depends on: G01.
- Pre-write fan-out: import graph/authority map; entry-point and conformance
  falsifier design.
- Writer: one EvoGen writer moves microworld composition behind the versioned
  public contract and entry-point path.
- Independent proof: install/discover through package metadata; prove identical
  demo outcome; prove core modules contain no microworld imports.
- Special rule: no built-in fallback that lets tests bypass the public loader.

### G03 — Trajectory identity

- State: completed in the current bounded goal commit.
- Depends on: G02 and current trajectory/schema authority.
- Pre-write fan-out: event identity audit; backward-fixture designer.
- Required fixtures before migration: several events at one subject step,
  missing source fields in alpha fixtures, duplicate source IDs, and preserved
  receipt/outcome separation.
- Independent proof: unique monotonic EvoGen order plus exact source metadata.
- Special rule: version the envelope; do not infer ordering from step index.

### G04 — Resumable stages

- State: next; implementation remains unstarted.
- Depends on: G03.
- Effectively serial writer: orchestration ownership changes are high fan-out.
- Pre-write fan-out: stage-state map; crash/resume/hash-mismatch proof design.
- Independent proof: stop after diagnosis, new process resume, identical final
  lineage and artifacts to one-shot execution.
- Special rule: no essential state survives only in Python memory or stdout.

### G05 — First-class probes

- Depends on: G04 artifact/resume state.
- Pre-write fan-out: current insufficient-evidence path audit; probe/permanent
  capability separation threat model.
- Independent proof: probe resolves named uncertainty while retained capability
  manifest stays byte-identical.
- Special rule: `BUILD_PROBE` never reaches the permanent-capability architect.

### G06 — Typed external reasoning roles

- Depends on: G04–G05.
- Pre-write fan-out: role inventory; ledger/transcript completeness audit;
  malformed-output/timeout test design.
- Independent proof: swap exactly one role backend; all other stages unchanged;
  request/response/provider/model/digest/failure retained.
- Special rule: prose never bypasses the typed result.

### G07 — Frozen evaluation authority

- Depends on: G06 and persisted artifacts.
- Pre-write fan-out: evaluator threat model; suite-manifest contract design.
- Independent proof: candidate tampering with evaluator or held-out scenario is
  rejected even when reported metrics improve; pre/post hashes match otherwise.
- Special rule: candidate tests never become retention authority.

### G08 — Subject conformance and doctor

- Depends on: G02–G07.
- Pre-write fan-out: public plugin contract matrix; doctor diagnostic UX.
- Independent proof: microworld passes the kit and each deliberately broken
  specimen names the exact violated boundary.
- Special rule: core doctor has no game-specific checks.

Journey I exit gate: G01–G08 clean, checkpointed, committed, conformance green,
and no real subject imports in core.

## 9. Journey II routing — Kenshi

### G09–G13 — Exact KAE export authorities

- G09 inventory is read-first and generates the event disposition map from
  `SessionLogger.write` source; unmapped source changes fail freshness.
- G10 is a serial logger migration with a concurrency stress test; log sequence
  remains distinct from step and telemetry revision.
- G11 pairs provenance/config auditors; secrets and unrelated environment are
  negative fixtures.
- G12 captures the planner-visible offer set at the authoritative enumeration
  boundary, not by prompt parsing.
- G13 derives the capability manifest from existing KAE registries/protocol and
  proof authorities; no hand-written sibling list is permitted.
- Exit artifacts: generated event map, sequence fixture, generation manifest,
  affordance-set event fixture, generated capability manifest, freshness tests.

### G14–G17 — Exact exporter and observer plugin

- G14 is cross-repository and serial: KAE exporter first, then retirement of the
  EvoGen provisional adapter. Each checkpoint records the counterpart commit.
- G15 registers the optional KAE plugin without making ordinary KAE imports
  depend on EvoGen.
- G16 proves checked-in observer and newly produced replay through one public
  runner path; no game launch or DLL installation.
- G17 maps current evaluator metrics without reducing them to success/action
  count; current and EvoGen results must agree explicitly.
- Independent roles: mapping auditor, plugin/conformance reviewer, metrics
  equivalence verifier.

### G18–G20 — Sealed historical corpus and benchmark

- Separate three authorities: case curator with sealed-answer access,
  diagnostician without it, and scorer/evaluator.
- G18 packages the trade-window lifecycle case from exact historical evidence.
- G19 adds at least six structurally different additions/removals/representation
  and evidence corrections.
- G20 runs the deterministic baseline and proves the inference mount cannot
  reach sealed answers, commit-message hints, or patch paths.
- Required artifacts: reconstruction manifest, parent/child commits, source and
  binary context, hidden diagnosis/spec/patch, integrity digest, leakage audit,
  multidimensional baseline score.

### G21–G23 — Model study, investigator, architect

- G21 requires navigator approval for provider/model/cost. Retain every request,
  response, timeout, malformed result, and score artifact. No implementation.
- G22 investigator output separates available engine mechanism, project-owned
  supported operation, unsafe guess, rejected mechanism, crash history, and
  remaining unknown.
- G23 specs additions, corrections, removals, observations, verification,
  recovery, and probes; implementers cannot broaden them.
- Independent roles: clean-context runner, evidence-citation auditor,
  alternative-diagnosis reviewer, frozen-spec reviewer.

### G24–G27 — Isolated level-4 candidate cycle

- G24 creates branch/worktree from exact parent; candidate author receives only
  issue/spec/evidence packet and has no sealed answers, evaluator, or install
  credentials.
- G25 reviewer/evaluator independently run KAE portable/replay/regression gates;
  unit tests alone cannot prove gameplay change.
- G26 defines suite/save/model/time/binary/rollback/approval authority but does
  not install or execute live candidates.
- G27 runs the historical level-4 cycle serially through artifact stages; the
  historical child is opened only after selection for comparison.
- Required separation: spec author -> candidate author -> reviewer -> evaluator
  -> release recommender -> root selection.

### G28–G29 — New live KAE evidence

- G28: navigator approves each supervised session budget. Multiple completed
  bundles may be analyzed in parallel afterward. Root/human reviews whether a
  repeated issue is capability, planning, or environment refusal. Stop before
  implementation; honest no-issue is completion.
- G29: wholly serial live chain—frozen spec, isolated implementation,
  portable/replay, approved install, restored revealing fixture, live variants,
  regression restoration, longer supervised run, rollback/final safe state.
- Retention requires exact source/model/prompt/scenario/save/DLL/run/evidence
  hashes and later world evidence across more than one lucky run.

Journey II exit gate: KAE conformance, seven sealed cases, one historical
level-4 cycle, and either one genuinely new supervised live closure or the
predeclared honest no-qualifying-issue result required by G49.

## 10. Journey III routing — OpenTTD

### G30–G32 — Reproducible subject foundation

- G30 navigator review point: choose submodule, reproducible source-checkout
  script, or patch series after license/upstream audit. Pin the exact upstream
  commit and separate every local patch.
- G31 builds a dedicated/headless target, binds no public port, and proves
  start/load/save/stop/crash capture with build/config/base-asset hashes.
- G32 creates immutable road-freight scenarios with fixed settings, economy,
  competitors, seeds, cargo/industry set, and starting company state.
- Existing Windows OpenTTD 15.3 and executable hash are host-availability
  evidence only until mapped to the pinned source and assets.

### G33–G34 — Least-invasive bridge and NoAI shell

- Parallel read-only spike: admin/console investigator and NoAI boundary
  investigator; threat reviewer tests session/correlation/timeout assumptions.
- Navigator review point before upstream patching. Patch only after existing
  interfaces are falsified with retained evidence.
- G34 executor owns company actions and supports only observe/wait/stop with
  heartbeat, bounded tick work, explicit errors, save/load identity, and no
  duplicate command execution.

### G35–G39 — Protocol, lifecycle, operations, runtime, plugin

- G35 freezes strict complete/truncated/missing/unknown telemetry before producer
  migration; valid and invalid fixtures precede implementation.
- G36 freezes request/bind/dispatch/receipt/later-observation/disposition and
  idempotency; spending or `true` is not completion.
- G37 derives the narrow road-freight offer surface from authoritative
  applicability and proves both acceptance and refusal.
- G38 keeps strategy separate from mechanics while mock and headless paths share
  decision/binding/execution.
- G39 registers OpenTTD through the existing EvoGen contract. Change EvoGen only
  when two-subject evidence proves a generic contract defect.

### G40–G42 — Baseline and route-planning diagnosis

- G40 repeats flat-map profitable-route trials; executor defects block progress.
- G41 uses structural obstacle scenarios without removing any atomic operation;
  repeated causal evidence must point to a reusable reasoning gap.
- Root/navigator confirms the deficit is not executor failure before G42.
- G42 uses a blind diagnostician and independent alternative-diagnosis reviewer;
  the desired capability name and answer are withheld. Freeze unseen-layout
  predictions, allowed APIs/costs, and forbidden coordinates/paths.

### G43–G45 — Candidate retention and observability follow-on

- G43 isolated author implements quotation only; mutation-purity verifier proves
  no game change during route planning; reviewer audits hard-coded maps,
  evaluator access, bounds, and cost assumptions.
- G44 may shard deterministic suites into isolated sandboxes, but the selector
  waits for every revealing/variant/regression/refusal/long-run result.
- G45 long-run observers and causal reviewer determine observability gap,
  planner problem, or no-change. A justified no-change result is success.

Journey III exit gate: reproducible headless subject, conformance, honest
baseline, and deterministic route-planning plus observability dispositions.

## 11. Journey IV routing — genericity and release

### G46 — Two-subject genericity audit

- Parallel read-only auditors inspect EvoGen core, microworld, KAE, and OpenTTD.
- One EvoGen writer performs accepted migrations.
- Reject abstractions used by only one subject merely to remove duplication.
- Prove core imports with neither subject installed.

### G47 — One CLI and artifact layout

- Per-repository command/layout auditors may inspect in parallel.
- Writes are serial by repository with cross-referenced checkpoints.
- Prove the same command sequence by changing only subject/suite configuration.
- Preserve KAE human live approval; do not inherit OpenTTD automation policy.

### G48 — Cross-subject study

- Navigator approves provider/model/cost.
- Sealed KAE and OpenTTD runs may execute in isolated parallel contexts.
- Independent synthesizer reports layer, resolution, grounding, unsupported
  claims, probe utility, candidate result, regressions, cost, and human semantic
  intervention. No scalar collapse.

### G49 — Serious completion state

- Wholly serial release audit after every source-plan criterion is evidenced.
- Independent reproducibility, lineage, evaluator-integrity, security, and
  documentation auditors return signed-off handbacks to the root.
- Fresh-machine portable/headless reproduction is mandatory.
- Live KAE bundle names exact remaining hardware/human boundary.
- Navigator authorizes publication/tagging only after the root reconciles every
  criterion to an artifact and no checkpoint overclaims completion.

## 12. Human and navigator gates

Mandatory check-ins:

- any change to numbered-goal order or repository ownership;
- any material broadening of a frozen goal packet;
- G21 and G48 provider/model/cost commitment;
- G28 supervised live-session budget;
- every G29 candidate installation and live trial;
- G30 upstream-carrying strategy;
- G33 decision to patch upstream;
- destructive repository or fixture replacement not already named by the goal;
- public release, remote creation, or publication when no established target
  already exists; and
- G49 final release.

Frequent updates should report evidence and directional decisions. They should
not become generic permission checkpoints for ordinary in-scope work.

## 13. Root closure checklist

Before committing any goal, the root verifies:

- [ ] exact parent commit and branch recorded;
- [ ] current source authority inspected;
- [ ] goal packet and falsifiers remained unchanged or revision was recorded;
- [ ] only named repositories/paths changed;
- [ ] superseded authority removed where the goal requires a clean break;
- [ ] generated projections refreshed from source;
- [ ] author did not certify its own work;
- [ ] independent review findings resolved or durably recorded;
- [ ] focused and full gates pass with preserved exit status;
- [ ] evidence lanes and withheld claims are explicit;
- [ ] failed experiments/rejected candidates remain artifacts;
- [ ] cross-repository counterpart commits are exact and committed;
- [ ] checkpoint names tests, evidence, uncertainty, and next unstarted goal;
- [ ] checkpoint dirty-state ratchet passes;
- [ ] final diff reviewed;
- [ ] one coherent commit created;
- [ ] checkpoint clean-state ratchet passes;
- [ ] tree clean;
- [ ] all subagents stopped;
- [ ] next goal remains unstarted.

## 14. Subagent handback schema

Every subagent returns this shape, even when its result is “no change”:

```yaml
handback:
  goal_id: G02
  role: authority_cartographer
  mode: read_only
  checkout:
    repository: evogen
    commit: <full-sha>
    dirty_at_start: false
  conclusion: ""
  evidence:
    source: []
    tests: []
    portable: []
    replay: []
    headless: []
    live: []
  findings:
    blocking: []
    nonblocking: []
  changed_files: []
  generated_artifacts: []
  commands:
    - argv: []
      exit_code: 0
  remaining_unknowns: []
  withheld_claims: []
  recommended_follow_ons: []
```

The root rejects handbacks that omit checkout identity, remaining unknowns, or
evidence classification.

## 15. Machine-readable goal registry

This appendix is routing metadata, not permission to start a goal.

```yaml
version: 1
ordering: strict_numeric
global_active_goal_limit: 1
goals:
  - {id: G01, repo: [evogen], depends: [], profile: foundation_release, state: complete, human_gate: []}
  - {id: G02, repo: [evogen], depends: [G01], profile: core_contract, state: complete, human_gate: []}
  - {id: G03, repo: [evogen], depends: [G02], profile: schema_migration, state: complete, human_gate: []}
  - {id: G04, repo: [evogen], depends: [G03], profile: orchestration_state, state: next, human_gate: []}
  - {id: G05, repo: [evogen], depends: [G04], profile: lifecycle_contract, state: unstarted, human_gate: []}
  - {id: G06, repo: [evogen], depends: [G05], profile: role_contract, state: unstarted, human_gate: []}
  - {id: G07, repo: [evogen], depends: [G06], profile: evaluator_security, state: unstarted, human_gate: []}
  - {id: G08, repo: [evogen], depends: [G07], profile: conformance, state: unstarted, human_gate: []}
  - {id: G09, repo: [kenshi-agent-env], depends: [G08], profile: source_inventory, state: unstarted, human_gate: []}
  - {id: G10, repo: [kenshi-agent-env], depends: [G09], profile: logger_migration, state: unstarted, human_gate: []}
  - {id: G11, repo: [kenshi-agent-env], depends: [G10], profile: generation_manifest, state: unstarted, human_gate: []}
  - {id: G12, repo: [kenshi-agent-env], depends: [G11], profile: event_contract, state: unstarted, human_gate: []}
  - {id: G13, repo: [kenshi-agent-env], depends: [G12], profile: generated_manifest, state: unstarted, human_gate: []}
  - {id: G14, repo: [kenshi-agent-env, evogen], depends: [G13], profile: cross_repo_adapter, state: unstarted, human_gate: []}
  - {id: G15, repo: [kenshi-agent-env], depends: [G14], profile: subject_plugin, state: unstarted, human_gate: []}
  - {id: G16, repo: [kenshi-agent-env], depends: [G15], profile: observer_replay, state: unstarted, human_gate: []}
  - {id: G17, repo: [kenshi-agent-env], depends: [G16], profile: metric_mapping, state: unstarted, human_gate: []}
  - {id: G18, repo: [kenshi-agent-env], depends: [G17], profile: sealed_case, state: unstarted, human_gate: []}
  - {id: G19, repo: [kenshi-agent-env], depends: [G18], profile: sealed_corpus, state: unstarted, human_gate: []}
  - {id: G20, repo: [kenshi-agent-env, evogen], depends: [G19], profile: blind_benchmark, state: unstarted, human_gate: []}
  - {id: G21, repo: [kenshi-agent-env], depends: [G20], profile: external_model_study, state: unstarted, human_gate: [provider_model_cost]}
  - {id: G22, repo: [kenshi-agent-env], depends: [G21], profile: investigator, state: unstarted, human_gate: []}
  - {id: G23, repo: [kenshi-agent-env], depends: [G22], profile: capability_architect, state: unstarted, human_gate: []}
  - {id: G24, repo: [evogen, kenshi-agent-env], depends: [G23], profile: isolated_candidate, state: unstarted, human_gate: []}
  - {id: G25, repo: [kenshi-agent-env], depends: [G24], profile: independent_evaluation, state: unstarted, human_gate: []}
  - {id: G26, repo: [kenshi-agent-env], depends: [G25], profile: live_suite_definition, state: unstarted, human_gate: []}
  - {id: G27, repo: [evogen, kenshi-agent-env], depends: [G26], profile: historical_level4, state: unstarted, human_gate: []}
  - {id: G28, repo: [kenshi-agent-env], depends: [G27], profile: supervised_observation, state: unstarted, human_gate: [live_session_budget]}
  - {id: G29, repo: [evogen, kenshi-agent-env], depends: [G28], profile: supervised_live_candidate, state: unstarted, human_gate: [install, live_revealing, live_variants, live_regressions, live_long_run]}
  - {id: G30, repo: [openttd-agent-env], depends: [G29], profile: subject_bootstrap, state: unstarted, human_gate: [upstream_carrying_strategy]}
  - {id: G31, repo: [openttd-agent-env], depends: [G30], profile: headless_build, state: unstarted, human_gate: []}
  - {id: G32, repo: [openttd-agent-env], depends: [G31], profile: scenario_pack, state: unstarted, human_gate: []}
  - {id: G33, repo: [openttd-agent-env], depends: [G32], profile: bridge_spike, state: unstarted, human_gate: [upstream_patch_route]}
  - {id: G34, repo: [openttd-agent-env], depends: [G33], profile: executor_shell, state: unstarted, human_gate: []}
  - {id: G35, repo: [openttd-agent-env], depends: [G34], profile: protocol_freeze, state: unstarted, human_gate: []}
  - {id: G36, repo: [openttd-agent-env], depends: [G35], profile: command_lifecycle, state: unstarted, human_gate: []}
  - {id: G37, repo: [openttd-agent-env], depends: [G36], profile: operation_surface, state: unstarted, human_gate: []}
  - {id: G38, repo: [openttd-agent-env], depends: [G37], profile: subject_runtime, state: unstarted, human_gate: []}
  - {id: G39, repo: [openttd-agent-env, evogen], depends: [G38], profile: subject_plugin, state: unstarted, human_gate: []}
  - {id: G40, repo: [openttd-agent-env], depends: [G39], profile: baseline_trials, state: unstarted, human_gate: []}
  - {id: G41, repo: [openttd-agent-env], depends: [G40], profile: deficit_observation, state: unstarted, human_gate: [deficit_classification_review]}
  - {id: G42, repo: [evogen, openttd-agent-env], depends: [G41], profile: blind_diagnosis_spec, state: unstarted, human_gate: []}
  - {id: G43, repo: [openttd-agent-env], depends: [G42], profile: isolated_candidate, state: unstarted, human_gate: []}
  - {id: G44, repo: [evogen, openttd-agent-env], depends: [G43], profile: deterministic_selection, state: unstarted, human_gate: []}
  - {id: G45, repo: [evogen, openttd-agent-env], depends: [G44], profile: observability_follow_on, state: unstarted, human_gate: []}
  - {id: G46, repo: [evogen], depends: [G45], profile: genericity_audit, state: unstarted, human_gate: []}
  - {id: G47, repo: [evogen, kenshi-agent-env, openttd-agent-env], depends: [G46], profile: cross_repo_cli, state: unstarted, human_gate: []}
  - {id: G48, repo: [evogen, kenshi-agent-env, openttd-agent-env], depends: [G47], profile: cross_subject_study, state: unstarted, human_gate: [provider_model_cost]}
  - {id: G49, repo: [evogen], depends: [G48], profile: release_audit, state: unstarted, human_gate: [final_publication]}
```

## 16. Immediate next execution packet

The next permitted packet is G04 only. It remains unstarted until the Goal 3
stop and navigator review are complete.

Before any G04 edit, the root must:

1. re-read EvoGen `AGENTS.md` and `docs/INTEGRATION_CHECKPOINT.md`;
2. confirm `main` starts at the reviewed, committed G03 result with a clean
   checkpoint ratchet;
3. inspect the orchestrator, CLI, ledger, artifact store, workspace layout,
   typed stage outputs, and every value the one-shot cycle keeps only in memory;
4. dispatch a stage-state cartographer and crash/resume proof designer read-only;
5. freeze the persisted stage manifest, immutable upstream references, subject
   generation and hash checks, invocation boundary, and one-shot compatibility;
6. assign one writer to make the nine stages individually invokable while the
   convenience `cycle` command executes the same stage path;
7. independently stop after diagnosis, resume in a new process, and prove the
   final lineage and artifacts match an uninterrupted cycle exactly;
8. refresh the checkpoint with the exact G04 parent and next G05; and
9. commit and stop without beginning G05.
