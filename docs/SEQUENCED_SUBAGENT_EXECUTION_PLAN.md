# EvoGen sequenced subagent execution plan

Status: checked-in proof-first execution authority for
`EVOGEN_KENSHI_OPENTTD_BOUNDED_GOALS.md`

Source plan:

- Drive file ID: `1IcZkzsjmsdtPqxxj4NxSiKWIBzB8In3D`
- Source revision observed: `2026-08-10T21:25:08.835Z`
- Source size observed: 37,532 bytes
- The Drive document remains the master specification for each numbered goal,
  its `Done when`, its `Do not`, and the final G49 completion standard.
- This checked-in companion owns execution order, local dependencies, subagent
  packets, proof-milestone UI, repository checkpoints, and the sole next goal.
- The navigator approved the proof-first order on 2026-08-14. It deliberately
  defers G19-G21 until after the first historical and supervised-live proofs;
  it does not delete, weaken, or mark those goals complete.

Drive lookup rule:

1. The root re-fetches the master document before freezing every numbered goal.
2. The root also re-fetches it at the start of each proof milestone, whenever
   the observed Drive revision changes, or whenever this companion does not
   contain enough detail to resolve a `Done when` or `Do not` boundary.
3. Subagents work from the root's frozen goal packet. They do not independently
   reinterpret the master plan while implementation is in flight.
4. If a goal contract conflicts with this file, the Drive goal contract wins.
   If only order or dependency differs, this proof-first file wins.

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
- Goal 9 state: completed at KAE commit
  `b8544b88b8c610f2859298308b0adaca290c9ddc`
- Goal 9 hosted proof: KAE run `31536027613` passed Python 3.11, 3.12,
  3.13, and 3.14 at the exact completion commit
- Goal 10 state: completed at KAE commit
  `7e25459c992572b0f102297420f7117fbc2146d7`
- Goal 11 state: completed at KAE commit
  `bfaa4d55ae10a34d33e7a06ee3959fc6659eceb4`
- Goal 11 hosted proof: KAE run `31542719034` passed the portable gate on
  Python 3.11, 3.12, 3.13, and 3.14 at the exact completion commit
- Goal 12 state: completed at KAE commit
  `0560b9de6e049f0dc06fab9afbef76f76d198092`
- Goal 12 hosted proof: KAE run `31703301693` passed the portable gate on
  Python 3.11, 3.12, 3.13, and 3.14 at the exact completion commit
- Goal 13 state: completed at KAE commit
  `a8584554e30bb793f5b60ef57e3d1500de5aaa12`
- Goal 13 hosted proof: KAE run `31720597916` passed the portable gate on
  Python 3.11, 3.12, 3.13, and 3.14 at the exact completion commit
- Goal 13 EvoGen prerequisite: commit
  `4270e8332f8a03757b39a306b2e936ac8a618cc3`, hosted run `31717965263`
- Goal 14 state: KAE exporter complete at commit
  `548658cbcef35037252e63be40248fa6a94b5ec1`; EvoGen retirement candidate is
  based on parent `6954f8bc1e0ad95a9ccd9486fe58999dce5cf885` and awaits the
  root's final review, commit, and hosted proof
- Goal 14 local focused proof: strict compact KAE export fixture round-trip,
  raw rejection, historical fixture diagnosis, and CLI removal pass in the
  candidate clone
- Next unstarted goal: Goal 15

## 1. What this plan controls

The source plan says to give one goal to a coding agent at a time. This document
keeps that rule, changes the order in which the remaining goals are selected,
and defines how a root agent may use subagents *inside* that one goal without
blurring authorship, authority, evidence, or completion.

The root agent is the only process allowed to:

1. declare a goal started or complete;
2. assign the repository write lock;
3. accept or reject subagent findings;
4. alter the integration checkpoint;
5. make the final goal commit;
6. select or retain an EvoGen candidate; and
7. unlock the next goal in the proof-first route.

Subagents increase scrutiny and bounded throughput. They never turn the roadmap
into 49 concurrent tasks. A proof milestone is a sequence of separately closed
numbered goals, not permission to merge their diffs or skip their stop gates.

## 2. Non-negotiable execution rules

1. **One numbered goal is active globally.** No work from the next routed goal
   is smuggled into the current diff.
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
    handoff, and cockpit refresh, no agent begins the next goal automatically.
13. **Every goal must improve proof visibility.** The checked-in cockpit must
    show what changed, the strongest evidence actually obtained, the nearest
    withheld claim, and which proof milestone the next goal advances.

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

- State: completed in the current bounded goal commit.
- Depends on: G03.
- Effectively serial writer: orchestration ownership changes are high fan-out.
- Pre-write fan-out: stage-state map; crash/resume/hash-mismatch proof design.
- Independent proof: stop after diagnosis, new process resume, identical final
  lineage and artifacts to one-shot execution.
- Special rule: no essential state survives only in Python memory or stdout.

### G05 — First-class probes

- State: completed in the current bounded goal commit.
- Depends on: G04 artifact/resume state.
- Pre-write fan-out: current insufficient-evidence path audit; probe/permanent
  capability separation threat model.
- Independent proof: probe resolves named uncertainty while retained capability
  manifest stays byte-identical.
- Special rule: `BUILD_PROBE` never reaches the permanent-capability architect.

### G06 — Typed external reasoning roles

- State: completed in the current bounded goal commit.
- Depends on: G04–G05.
- Pre-write fan-out: role inventory; ledger/transcript completeness audit;
  malformed-output/timeout test design.
- Independent proof: swap exactly one role backend; all other stages unchanged;
  request/response/provider/model/digest/failure retained.
- Special rule: prose never bypasses the typed result.

### G07 — Frozen evaluation authority

- State: completed in the current bounded goal commit.
- Depends on: G06 and persisted artifacts.
- Pre-write fan-out: evaluator threat model; suite-manifest contract design.
- Independent proof: candidate tampering with evaluator or held-out scenario is
  rejected even when reported metrics improve; pre/post hashes match otherwise.
- Special rule: candidate tests never become retention authority.

### G08 — Subject conformance and doctor

- State: completed in the current bounded goal commit.
- Depends on: G02–G07.
- Pre-write fan-out: public plugin contract matrix; doctor diagnostic UX.
- Independent proof: microworld passes the kit and each deliberately broken
  specimen names the exact violated boundary.
- Special rule: core doctor has no game-specific checks.

Journey I exit gate: G01–G08 clean, checkpointed, committed, conformance green,
and no real subject imports in core.

## 9. Journey II routing — Kenshi

### G09–G13 — Exact KAE export authorities

- G09 is complete at KAE commit
  `b8544b88b8c610f2859298308b0adaca290c9ddc`. Its read-first inventory
  generates the event disposition map from `SessionLogger.write` source;
  unmapped source changes fail freshness. The reviewed authority contains 89
  event types, 127 producer records, and 16 open boundaries.
- G10 is complete at KAE commit
  `7e25459c992572b0f102297420f7117fbc2146d7`. Its serial logger migration
  adds a run-local, append-safe event sequence under the physical write lock;
  a 1,024-write concurrency stress test proves ordered identities with no loss
  while step and telemetry revision remain distinct.
- G11 is complete at KAE commit
  `bfaa4d55ae10a34d33e7a06ee3959fc6659eceb4`. Its read-only manifest command
  records stable source, lock, model, prompt/corpus, redacted config, protocol,
  schema, operation, proof, memory, scenario/start, Kenshi, and independent
  native-binary evidence. Mutation falsifiers cover every source-plan trigger;
  secrets and unrelated environment are negative fixtures. The output parses
  as EvoGen's current `GenerationManifest`, while its native-capability digest
  remains explicitly provisional until G13 rather than claiming subject
  conformance early. Hosted run `31542719034` passed Python 3.11–3.14.
- G12 is complete at KAE commit
  `0560b9de6e049f0dc06fab9afbef76f76d198092`. One immutable enumeration now
  feeds hosted planner projection, typed `affordance_set` evidence, and the
  read-only watch surface. The event is the last durable record before planner
  delivery and retains opaque offer and selection identities, declared
  adapter/operation authority, semantic parameter contracts, applicable target
  identities, source completeness, typed withholding, and authored revision.
  Replay reconstructs selections from that typed evidence, refuses legacy logs
  rather than parsing prompts or labels, and rejects contradictory contracts,
  unknown adapter/operation pairs, or incomplete source inventories. Direct and
  scripted planners truthfully record `not_delivered`. Transfer slot/section
  mechanics remain private to runtime binding. The generated event authority is
  now 90 event types and 128 producer records. Hosted run `31703301693` passed
  Python 3.11–3.14.
- G13 is complete at KAE commit
  `a8584554e30bb793f5b60ef57e3d1500de5aaa12`. Its 69-row manifest is generated
  from operation, affordance, native, telemetry, protocol, continuity, outcome,
  recovery, and proof authorities rather than a sibling semantic registry. It
  preserves six exact kinds and distinct proven, absent, unproven, withheld,
  unknown, and unsupported states. Referenced proof bytes participate in
  content identity; semantic mutations change identity or output while
  ordering-only changes stay stable. The schema-2 native category metadata
  leaves the generated C++ header byte-identical to G12. Hosted run
  `31720597916` passed Python 3.11–3.14.
- Exit artifacts: generated event map, sequence fixture, generation manifest,
  affordance-set event fixture, generated capability manifest, freshness tests.

### Proof milestone A — Real KAE replay showcase (G14–G17)

This is the first human-readable proof target. G14, G15, G16, and G17 still
close one at a time, but together must leave one obvious command and one
reusable cockpit view that lets a navigator inspect real KAE evidence flowing
through EvoGen.

- G14 is cross-repository and serial: KAE exporter first, then retirement of the
  EvoGen provisional adapter. Each checkpoint records the counterpart commit.
  Strict mode on the current central-lifecycle real bundle must produce zero
  unknown event types, and every normalized event must round-trip through the
  current EvoGen schema.
- G15 registers the optional KAE plugin without making ordinary KAE imports
  depend on EvoGen.
- G16 proves a checked-in observer bundle and a newly produced replay through
  one public runner path, with the typed RunRecord, manifest, artifact digests,
  and evidence-class distinctions retained; no game launch or DLL installation.
- G17 maps current evaluator metrics without reducing them to success/action
  count; current and EvoGen results must agree explicitly.
- The showcase must display source identity, event ordering, observations,
  affordance sets, decisions, execution receipts, later outcomes, uncertainty,
  finalization, and metric equivalence. It must visually keep dispatch and
  native acknowledgement separate from later world-effect evidence.
- The showcase may claim replay and portable proof only. It may not claim that
  EvoGen generated or retained a KAE capability.
- Independent roles: mapping auditor, plugin/conformance reviewer, metrics
  equivalence verifier, and cockpit evidence auditor.

### Proof milestone B — One historical evolution (G18, G22–G27)

This is the first end-to-end KAE capability-engineering proof. It intentionally
uses one exact historical case before building the broader research corpus.

- G18 packages the trade-window lifecycle case from exact historical evidence.
  The case curator retains sealed-answer access; inference roles do not.
- G22 investigator output separates available engine mechanism, project-owned
  supported operation, unsafe guess, rejected mechanism, crash history, and
  remaining unknown. While G21 is deferred, G22 is deterministic or
  human-authored only and may not invoke an external model/provider.
- G23 specs additions, corrections, removals, observations, verification,
  recovery, and probes; implementers cannot broaden them.
- G24 creates a branch/worktree from the exact historical parent. Candidate
  authors receive only the issue/spec/evidence packet and have no sealed answer,
  evaluator, installation credential, or historical child access.
- G25 reviewers and evaluators independently run KAE portable, replay, variant,
  and regression gates. Unit tests alone cannot prove gameplay change.
- G26 freezes the suite, save, model, time, binary, rollback, and approval
  authority that the historical cycle and later live cycle consume. It does not
  install or execute a live candidate.
- G27 runs the historical level-4 cycle through persisted EvoGen stages. The
  historical child and human patch remain sealed until after root selection,
  then become comparison evidence rather than selection authority.
- The cockpit must show the artifact chain from failure evidence through
  diagnosis, investigation, frozen spec, candidate transcript/patch, independent
  review, baseline/candidate evaluation, decision, and post-decision comparison.
- The milestone may claim a historical portable/replay evolution. It may not
  claim a newly discovered or live-proven KAE improvement.
- Required separation: case curator -> diagnostician -> investigator -> spec
  author -> candidate author -> reviewer -> evaluator -> release recommender ->
  root selection.

### Proof milestone C — One supervised live evolution (G28–G29)

This is the first proof that begins with current live observation and may end in
a retained KAE capability. It does not begin until milestone B is closed.

- G28 requires navigator approval for each supervised session budget. Completed
  bundles may be analyzed in parallel afterward. Root and human review whether
  a repeated issue is capability, planning, environment refusal, or insufficient
  evidence. Stop before implementation; honest no-issue is completion.
- G29 is wholly serial: frozen spec, isolated implementation, portable/replay,
  approved installation, restored revealing fixture, live variants, regression
  restoration, longer supervised run, rollback, and final safe state.
- Retention requires exact source, model, prompt, scenario, save, DLL, run, and
  evidence hashes plus later world evidence across more than one lucky run.
- The cockpit must expose every approval, baseline/candidate identity, rollback
  point, revealing/variant/regression result, and the exact later observation
  that supports or withholds a world-effect claim.

### Deferred scientific depth — G19–G21

These goals move after the first supervised-live proof so the project becomes
observable sooner. They remain mandatory and must close before Journey III.

- G19 adds at least six cases, for at least seven total including G18: incomplete
  scans, the unsafe task-probability oracle, selected/queued versus accepted
  operators, collapsed player topology, obsolete pointer-calibration gating,
  and equipped-item withholding after the transfer-crash diagnosis. Together
  they cover additions, removals, representation corrections, and evidence
  corrections.
- G20 runs the deterministic hidden-answer baseline and proves the inference
  mount cannot reach sealed answers, commit-message hints, or patch paths.
- G21 requires navigator approval for provider, model, and cost, and compares
  model diagnoses with human diagnoses while retaining every request, response,
  timeout, malformed result, and score artifact. It performs no implementation.
- Separate case curator, diagnostician, scorer/evaluator, clean-context runner,
  evidence-citation auditor, and alternative-diagnosis reviewer authorities.
- Required artifacts: reconstruction manifests, parent/child commits, source and
  binary context, hidden diagnosis/spec/patch, integrity digest, leakage audit,
  multidimensional baseline, and model-versus-human scorecard.

Journey II exit gate: the replay showcase, one historical level-4 cycle, one
supervised-live closure or the predeclared honest no-qualifying-issue result,
seven sealed cases, and the hidden-answer/model study are all independently
closed. Proof-first order changes when these become visible, not what G49
ultimately requires.

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
version: 2
ordering: proof_first
global_active_goal_limit: 1
execution_route:
  - {id: replay_showcase, status: next, goals: [G14, G15, G16, G17]}
  - {id: historical_evolution, status: planned, goals: [G18, G22, G23, G24, G25, G26, G27]}
  - {id: supervised_live_evolution, status: planned, goals: [G28, G29]}
  - {id: deferred_scientific_depth, status: deferred, goals: [G19, G20, G21]}
  - {id: openttd_and_release, status: planned, goals: [G30, G31, G32, G33, G34, G35, G36, G37, G38, G39, G40, G41, G42, G43, G44, G45, G46, G47, G48, G49]}
goals:
  - {id: G01, repo: [evogen], depends: [], profile: foundation_release, state: complete, human_gate: []}
  - {id: G02, repo: [evogen], depends: [G01], profile: core_contract, state: complete, human_gate: []}
  - {id: G03, repo: [evogen], depends: [G02], profile: schema_migration, state: complete, human_gate: []}
  - {id: G04, repo: [evogen], depends: [G03], profile: orchestration_state, state: complete, human_gate: []}
  - {id: G05, repo: [evogen], depends: [G04], profile: lifecycle_contract, state: complete, human_gate: []}
  - {id: G06, repo: [evogen], depends: [G05], profile: role_contract, state: complete, human_gate: []}
  - {id: G07, repo: [evogen], depends: [G06], profile: evaluator_security, state: complete, human_gate: []}
  - {id: G08, repo: [evogen], depends: [G07], profile: conformance, state: complete, human_gate: []}
  - {id: G09, repo: [kenshi-agent-env], depends: [G08], profile: source_inventory, state: complete, human_gate: []}
  - {id: G10, repo: [kenshi-agent-env], depends: [G09], profile: logger_migration, state: complete, human_gate: []}
  - {id: G11, repo: [kenshi-agent-env], depends: [G10], profile: generation_manifest, state: complete, human_gate: []}
  - {id: G12, repo: [kenshi-agent-env], depends: [G11], profile: event_contract, state: complete, human_gate: []}
  - {id: G13, repo: [kenshi-agent-env], depends: [G12], profile: generated_manifest, state: complete, human_gate: []}
  - {id: G14, repo: [kenshi-agent-env, evogen], depends: [G13], profile: cross_repo_adapter, state: complete, human_gate: []}
  - {id: G15, repo: [kenshi-agent-env], depends: [G14], profile: subject_plugin, state: next, human_gate: []}
  - {id: G16, repo: [kenshi-agent-env], depends: [G15], profile: observer_replay, state: unstarted, human_gate: []}
  - {id: G17, repo: [kenshi-agent-env], depends: [G16], profile: metric_mapping, state: unstarted, human_gate: []}
  - {id: G18, repo: [kenshi-agent-env], depends: [G17], profile: sealed_case, state: unstarted, human_gate: []}
  - {id: G19, repo: [kenshi-agent-env], depends: [G18], profile: sealed_corpus, state: unstarted, human_gate: []}
  - {id: G20, repo: [kenshi-agent-env, evogen], depends: [G19], profile: blind_benchmark, state: unstarted, human_gate: []}
  - {id: G21, repo: [kenshi-agent-env], depends: [G20], profile: external_model_study, state: unstarted, human_gate: [provider_model_cost]}
  - {id: G22, repo: [kenshi-agent-env], depends: [G18], profile: deterministic_or_human_investigator, state: unstarted, human_gate: []}
  - {id: G23, repo: [kenshi-agent-env], depends: [G22], profile: capability_architect, state: unstarted, human_gate: []}
  - {id: G24, repo: [evogen, kenshi-agent-env], depends: [G23], profile: isolated_candidate, state: unstarted, human_gate: []}
  - {id: G25, repo: [kenshi-agent-env], depends: [G24], profile: independent_evaluation, state: unstarted, human_gate: []}
  - {id: G26, repo: [kenshi-agent-env], depends: [G25], profile: live_suite_definition, state: unstarted, human_gate: []}
  - {id: G27, repo: [evogen, kenshi-agent-env], depends: [G18, G26], profile: historical_level4, state: unstarted, human_gate: []}
  - {id: G28, repo: [kenshi-agent-env], depends: [G27], profile: supervised_observation, state: unstarted, human_gate: [live_session_budget]}
  - {id: G29, repo: [evogen, kenshi-agent-env], depends: [G28], profile: supervised_live_candidate, state: unstarted, human_gate: [install, live_revealing, live_variants, live_regressions, live_long_run]}
  - {id: G30, repo: [openttd-agent-env], depends: [G21, G29], profile: subject_bootstrap, state: unstarted, human_gate: [upstream_carrying_strategy]}
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

The next permitted packet is G15 only. G14 is complete at the KAE exporter
commit above plus the reviewed EvoGen retirement candidate; the root must still
commit and publish the EvoGen half before treating the cross-repository goal as
publicly ratcheted.

G14 was cross-repository and serial. KAE mapped the exact existing session-event
and generation/capability authorities into a production trajectory exporter at
commit `548658cbcef35037252e63be40248fa6a94b5ec1`. EvoGen then retired its
provisional KAE normalizer and `normalize-kae` CLI, retained only fixture-scoped
historical diagnosis support, and added an exact compact raw/manifest/trajectory
contract fixture. Each repository checkpoint names the exact counterpart commit.

The exporter must preserve missing, truncated, unknown, and withheld evidence;
retain event and generation identity; and keep dispatch separate from later
world-effect proof. G14 does not register the G15 subject plugin, run the G16
observer/replay path, change native behavior, install artifacts, launch Kenshi,
modify a save, or claim a live world effect.

G14 is the first separately closed step of Proof milestone A. Its cockpit
change exposes the exact raw-to-normalized event mapping, source identity,
ordering, receipt/outcome separation, and remaining uncertainty. It keeps the
overall KAE replay showcase withheld until G15 registration, G16 public replay,
and G17 metric equivalence have each closed.
