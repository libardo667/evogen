# Integration checkpoint: resumable evolution stages

This document is the current repository authority for one bounded integration
goal. It is replaced in the same commit as every completed goal; Git history
retains older checkpoints.

## Repository and planning authority

```text
parent commit          d56b45021011edfd787e0ec45da75c2be8e34275
integration branch     main
current goal           Goal 4 - Make the evolution cycle resumable
next unstarted goal    Goal 5 - Add first-class probes
alpha source commit    88c169d46e3eaf5c0b0cc87f31e05c95ea9356b4
alpha release commit   9c8d94c59a95222a719e20fac5a61d2ec712743d
alpha tag              v0.1.0
public remote          https://github.com/libardo667/evogen
plan file              EVOGEN_KENSHI_OPENTTD_BOUNDED_GOALS.md
plan file id           1IcZkzsjmsdtPqxxj4NxSiKWIBzB8In3D
plan updated           2026-08-10T21:25:08.835Z
execution plan         docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 4 began from the reviewed Goal 3 commit named by `parent commit`. The alpha
release remains anchored above. This goal changes generic orchestration,
artifact, workspace, CLI, and typed stage authority without changing microworld
mechanics, scenarios, evaluator rules, selection policy, or retained outcome.

## Behavioral change and authority

Source-proven:

- the public evolution sequence is the exact ordered set `ingest`, `distill`,
  `diagnose`, `investigate`, `specify`, `build`, `review`, `evaluate`, and
  `select`;
- `cycle`, `demo`, and individual `stage` invocations use the same generic
  persisted dispatcher rather than parallel one-shot authority;
- an immutable `CycleManifest` pins the subject name, plugin API and source
  identity, baseline generation fingerprint, canonical baseline and plan
  artifacts, plan digest, and exact stage order;
- every completed stage has a typed content-addressed output, a typed receipt
  naming its exact input references, and an atomic pointer into a receipt hash
  chain;
- reopening a workspace reloads the persisted baseline and plan as canonical
  inputs; newly bootstrapped equivalents are used only to detect subject,
  generation, plugin, or plan drift;
- replay validates artifact bytes and schemas, every pointer and receipt
  identity, the complete prior chain, stage-specific semantic links, candidate
  file bytes, run/event generation and scenario ownership, and the canonical
  capability-manifest digest;
- diagnostic distillation is recomputed from immutable CAS event and capability
  artifacts during replay; mutable JSONL traces remain retained evidence but are
  not essential resume state;
- candidate ledger status remains truthful at the `reviewed`, `evaluated`, and
  final retained/rejected boundaries;
- `status` and `show-result` use validated read-only artifact and SQLite paths,
  do not execute missing stages, and do not infer completion from pointer-file
  existence; and
- safe resume is claimed only at a published completed-stage boundary. Orphaned
  CAS bytes are not completion proof, and arbitrary instruction-level crash
  recovery is not claimed.

Test-proven:

- all nine stages run individually in order, each from a separate CLI process,
  and a later `cycle` replay leaves every authoritative workspace byte
  unchanged;
- one process stops after diagnosis with no later pointer, and a fresh process
  resumes through selection with the same normalized issue, investigation,
  specification, candidate, review, experiment, decision, retained generation,
  and lineage semantics as uninterrupted execution;
- the retained lineage joins the exact baseline parent, retained child,
  candidate, decision, generation rows, and final result;
- completed replay remains valid after diagnostic JSONL mutation because the
  persisted CAS events are the replay authority;
- missing or corrupt CAS output, bad manifest digest, valid rehashed bootstrap
  mismatch, prior-pointer identity drift, forged receipt context, forged
  distilled output, forged run/event generation, forged capability manifest,
  and changed candidate files all fail closed;
- a completed stage replay creates no new stage, artifact, candidate, trace,
  report, result, lineage, or SQLite bytes; and
- successful read-only status/result operations and rejected read-only artifact
  writes leave the complete workspace unchanged.

Generated authority:

- public JSON Schemas now include `ArtifactRef`, `CycleManifest`, `IngestResult`,
  `StageReceipt`, and `StagePointer`, with required version discriminators on the
  versioned stage records; and
- candidate and cycle-result schemas include the generated changed-file digest
  map used to detect post-build mutation.

Not proven:

- a crash inside a stage can be resumed transactionally; only completed
  boundaries are safe;
- concurrent writers to the same cycle are serialized or conflict-free;
- a subject plugin's entry-module source identity captures the transitive source
  closure of every dependency;
- probes are a lifecycle distinct from permanent capabilities, which remains
  Goal 5;
- external model roles diagnose or implement capabilities; or
- OpenTTD or Kenshi is registered, controlled, or live-proven as a subject.

## Verification and independent review

The one local and CI authority remains:

```bash
uv run --frozen --extra dev python scripts/verify.py
```

Before checkpoint refresh, 120 non-checkpoint tests passed together with Ruff,
strict mypy, generated-schema freshness, and whitespace checks. The focused
persisted-cycle and artifact suite passed 17 tests in the final root replay.
With this checkpoint present, the authoritative dirty-candidate gate passed
compile, Ruff, strict mypy, a fresh wheel build and exact subject entry-point
metadata check, all 121 tests, the retained microworld demo, and whitespace checks.
The checkpoint ratchet is rerun once more from the clean commit.

Pre-write authority mapping and crash/resume proof design were delegated to two
read-only Luna agents. A separate Luna writer produced the candidate without
checkpoint or commit authority. Independent adversarial review rejected early
rounds for unvalidated public read paths, optional version discriminators,
fresh in-memory bootstrap use, missing lifecycle state, incomplete lineage and
idempotence proofs, forged pointer/receipt context, forged cross-stage outputs,
and forged run/capability provenance. Every finding was re-delegated with a
durable falsifier. The reviewer replayed the final attacks and returned an
explicit acceptance; candidate-author diagnostics were not used as
certification.

## External subject availability

Kenshi Agent Environment remains a separate subject repository. Its exact
integration baseline must be resolved again when Goal 9 starts.

OpenTTD 15.3 remains installed at `C:\Program Files\OpenTTD`. The installed
`openttd.exe` SHA-256 is
`360f615cb74cafcedf0486398a396577e8f1470e0f8158f66b7e29557fdb711d`.
This is availability evidence only: it has not been correlated to the pinned
upstream source, configured for headless execution, or accepted as a subject.

## Completion boundary

This checkpoint is part of the coherent Goal 4 candidate. Goal 4 is complete
only after the authoritative gate passes with this dirty checkpoint, the final
diff is reviewed and committed, the clean-state checkpoint ratchet passes, and
the tree is clean and synchronized with the public remote.

Goal 5 is the sole next packet and remains unstarted. Probe lifecycle work must
not be smuggled into this resumability commit.
