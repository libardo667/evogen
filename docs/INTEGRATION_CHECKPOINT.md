# Integration checkpoint: first-class evidence probes

This document is the current repository authority for one bounded integration
goal. It is replaced in the same commit as every completed goal; Git history
retains older checkpoints.

## Repository and planning authority

```text
parent commit          c001c885bd6f2f2ae498430d5f2533cb3b0c167c
integration branch     main
current goal           Goal 5 - Add first-class probes
next unstarted goal    Goal 6 - Add typed external reasoning roles
alpha source commit    88c169d46e3eaf5c0b0cc87f31e05c95ea9356b4
alpha release commit   9c8d94c59a95222a719e20fac5a61d2ec712743d
alpha tag              v0.1.0
public remote          https://github.com/libardo667/evogen
plan file              EVOGEN_KENSHI_OPENTTD_BOUNDED_GOALS.md
plan file id           1IcZkzsjmsdtPqxxj4NxSiKWIBzB8In3D
plan updated           2026-08-10T21:25:08.835Z
execution plan         docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 5 began from the reviewed Goal 4 commit named by `parent commit`. This
goal adds a disposable evidence-probe plane without changing microworld
scenarios, permanent candidate architecture, evaluator rules, retention
policy, or the retained baseline generation.

## Behavioral change and authority

Source-proven:

- probes have their own ordered `plan`, `build`, `review`, `evaluate`, and
  `dispose` stages, typed manifest, receipts, atomic pointers, content-addressed
  artifacts, ledger records, candidate kind, permissions, evidence target,
  evaluation, and terminal disposition;
- the permanent `EvolutionStageOrchestrator` raises a typed
  `ProbeRequiredError` before invoking the capability architect whenever an
  issue requests `BUILD_PROBE`;
- the optional subject-plugin probe factory exposes typed planner, builder,
  reviewer, and evaluator roles without a core import or built-in fallback to
  microworld code;
- probe builders return typed in-memory file payloads and receive no workspace
  path; the orchestrator alone validates and publishes the exact declared file
  set under the assigned probe root;
- builder, reviewer, and evaluator objects must be distinct authorities;
- the microworld planner requires one persisted `BUILD_PROBE` issue, one exact
  investigation-derived operation/effect, one revealing fixture, a named
  uncertainty, and explicit operation, effect, path, step, byte, and duration
  permissions;
- generated probe code binds one opaque container from the supplied observation
  and contains no scenario identifier, target identifier, container name, or
  expected answer;
- dispatch acceptance is insufficient: `RESOLVED` requires a complete accepted
  and changed receipt, the declared operation/effect within budget, an initially
  observed target, and a later complete observation of the same inspected target
  with exposed items;
- the subject evaluator executes against a fresh microworld and obtains the
  later snapshot separately from the dispatch receipt; deterministic evaluator
  replay rejects coordinated persisted-evidence substitution;
- permanent capability bytes are independently read and hash-checked before and
  after evaluation against the runner-produced capability manifest;
- probe CAS, workspace, receipt chain, and ledger transitions are separate from
  permanent candidates, experiments, decisions, generations, materialization,
  retention, and lineage; and
- replay fails closed with typed integrity errors for forged identities or
  links, missing or corrupt CAS objects, malformed pointers, cross-probe
  substitution, extra files, path escape, and existing or dangling symlinks.

Test-proven:

- a persisted single-case microworld chain produces occurrence count `1`, an
  insufficient-evidence `BUILD_PROBE` issue, and the exact
  `inspect_container -> reveal_contents` investigation without calling the
  permanent architect;
- that probe records and resolves its named uncertainty only after an accepted
  and changed engine receipt plus a complete later observation;
- permanent ledger rowsets, permanent stage-pointer bytes, all permanent CAS
  bytes, the baseline `GenerationManifest` reference and bytes, and the
  capability-manifest reference and bytes are identical before and after the
  probe; exactly one baseline generation and no child generation remain;
- missing, truncated, unknown, dispatch-only, unchanged, refused, over-budget,
  missing-later, contradictory-later, and missing-initial-container evidence all
  remain non-resolving;
- evaluator exceptions are retained as typed unknown evidence and terminate
  inconclusively with before/after capability proof;
- crash-after-ledger-insert recovery is idempotent at every probe stage, and
  fresh-process resume produces one immutable row per stage and byte-stable
  status/result replay;
- planner, candidate, review, evaluation, disposition, receipt, pointer, and
  evidence tampering attacks fail, including attacks with recomputed enclosing
  content hashes and deterministic IDs;
- manifest, stage-pointer, workspace, probe-root, candidate-root, candidate-file,
  and dangling-symlink attacks fail closed;
- source specimens using imports, filesystem/process access, attributes,
  dunder names, or unbounded control flow are rejected without marker-file side
  effects; and
- optional/malformed probe role factories and every malformed individual role
  fail through typed subject-plugin errors.

Generated authority:

- the schema registry and generated index now own sixteen probe schemas for
  build output, file payload, permissions, evidence target, plan, candidate,
  review, dispatch evidence, observation evidence, evaluation, disposition,
  manifest, receipt, pointer, required result, and final result; and
- the pre-existing permanent candidate and cycle-result schemas remain
  byte-identical to the Goal 4 parent.

Not proven:

- evaluator provenance, provider/model transcripts, or frozen evaluator and
  held-out-suite authority; these are explicit Goal 6 and Goal 7 work;
- containment of an intentionally malicious trusted Python plugin that uses
  ambient filesystem APIs; G05 removes workspace authority from the builder
  contract and sandboxes generated probe source, but plugin process isolation is
  not claimed;
- concurrent writers to the same probe workspace are serialized;
- probe results automatically launch a later permanent capability cycle; probe
  findings are evidence only and never retention authority; or
- OpenTTD or Kenshi is registered, controlled, installed from pinned source, or
  live-proven as an EvoGen subject.

## Verification and independent review

The local and CI authority remains:

```bash
uv run --frozen --extra dev python scripts/verify.py
```

Before checkpoint refresh, the root independently passed 110 focused
probe/plugin/schema tests and all 174 non-checkpoint tests, together with Ruff,
strict mypy over 45 source files, generated-schema freshness, preservation of
the Goal 4 permanent schemas, and whitespace checks. With this checkpoint
present, the authoritative dirty-candidate gate passed compile, Ruff, strict
mypy, a fresh isolated wheel build and exact subject entry-point metadata check,
all 175 tests, the retained microworld demo, and whitespace checks.

Two Luna agents mapped the pre-write insufficient-evidence path and the
probe/permanent threat boundary. A separate Luna writer implemented the bounded
candidate without checkpoint or commit authority. Two independent Luna review
lanes repeatedly rejected early candidates after reproducing real defects:
forged receipts and evaluations, weak causal snapshots, writable builder paths,
unlisted files, raw CAS exceptions, forged plans, symlinked pointers, and
dangling symlinks. Each accepted correction was tied to a retained regression.
The causal reviewer and final integrity reviewer independently returned
`ACCEPT`; candidate-author diagnostics were not used as certification.

## External subject availability

Kenshi Agent Environment remains a separate subject repository. Its exact
integration baseline must be resolved again when Goal 9 starts.

OpenTTD 15.3 remains installed at `C:\Program Files\OpenTTD`. The installed
`openttd.exe` SHA-256 is
`360f615cb74cafcedf0486398a396577e8f1470e0f8158f66b7e29557fdb711d`.
This is availability evidence only: it has not been correlated to pinned
upstream source or base assets, configured for headless execution, or accepted
as a subject.

## Completion boundary

This checkpoint is part of the coherent Goal 5 candidate. Goal 5 is complete
only after the authoritative gate passes with this dirty checkpoint, the final
diff is reviewed and committed, the clean-state checkpoint ratchet passes, and
the tree is clean and synchronized with the public remote.

Goal 6 is the sole next packet and remains unstarted. External reasoning-role
or frozen evaluator-authority work must not be smuggled into this probe commit.
