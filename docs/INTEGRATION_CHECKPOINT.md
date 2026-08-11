# Integration checkpoint: versioned trajectory identity

This document is the current repository authority for one bounded integration
goal. It is replaced in the same commit as every completed goal; Git history
retains older checkpoints.

## Repository and planning authority

```text
parent commit          8f567cf84ce4de9998b4a652964bdbb98da0e49a
integration branch     main
current goal           Goal 3 - Fix trajectory identity before importing real logs
next unstarted goal    Goal 4 - Make the evolution cycle resumable
alpha source commit    88c169d46e3eaf5c0b0cc87f31e05c95ea9356b4
alpha release commit   9c8d94c59a95222a719e20fac5a61d2ec712743d
alpha tag              v0.1.0
public remote          https://github.com/libardo667/evogen
plan file              EVOGEN_KENSHI_OPENTTD_BOUNDED_GOALS.md
plan file id           1IcZkzsjmsdtPqxxj4NxSiKWIBzB8In3D
plan updated           2026-08-10T21:25:08.835Z
execution plan         docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 3 began from the reviewed Goal 2 commit named by `parent commit`. The alpha
release remains anchored above. This goal changes trajectory identity,
provenance, parsing, and persistence authority without changing the microworld
environment, evaluator, candidate implementation, selection rule, or retention
outcome.

## Behavioral change and authority

Source-proven:

- `TrajectoryEvent` is a strict normalized envelope at version `1.0`; all new
  records carry five required nullable source fields for event type, event ID,
  source sequence, source step index, and source world revision;
- EvoGen `sequence` is a strict nonnegative integer owned by the normalized run,
  while subject sequence and step remain provenance and never establish EvoGen
  identity or ordering;
- `TrajectoryRecorder` emits complete current envelopes and retains dispatch,
  execution receipt, later outcome observation, and ordinary observation as
  separate events;
- `KenshiJsonlAdapter` gives accepted raw records contiguous encounter-order
  EvoGen sequences and distinct generated event IDs, even when source IDs or
  source steps repeat, while preserving the exact raw object under
  `payload.raw`;
- normalized JSONL is homogeneous: alpha/current mixing, normalized/raw mixing,
  duplicate normalized event IDs, non-increasing sequence, and multiple source
  runs fail closed with location context;
- the explicit alpha compatibility reader upgrades only wholly unversioned
  records, leaves unavailable source provenance null, and rejects partial or
  unsupported envelopes;
- source sequence and step accept exact integers only; source IDs and revisions
  accept strings or integers excluding booleans; malformed present provenance
  is rejected rather than coerced, hidden as missing, or replaced by a
  lower-precedence alias; and
- ledger run/event writes validate run, generation, scenario, event identity,
  and monotonic order, then insert transactionally without replacement. Old
  alpha event JSON remains readable through the same compatibility boundary.

Test-proven:

- a four-event fixture at one subject step preserves dispatch, receipt, outcome,
  and later observation order as EvoGen sequences `0..3` while retaining
  out-of-order source sequences, exact source metadata, duplicate source IDs,
  and distinct normalized event IDs;
- physical alpha normalized fixtures upgrade without inventing source metadata;
- direct model and reader tests reject unsupported, partial, mixed, duplicate,
  multi-run, nonmonotonic, coercible, and negative normalized identities;
- malformed source booleans, floats, strings, and containers fail closed, and a
  malformed higher-precedence revision cannot fall through to payload data;
- payload omission remains consistent across the model, generated schema,
  current reader, and alpha reader, defaulting only the generic payload object;
- ledger collision and wrong-context tests preserve transaction atomicity and
  prove failed writes leave no partial evidence; and
- the historical missing-close fixture still normalizes, distills, and produces
  the same evidence-backed affordance-discovery diagnosis.

Generated authority:

- `schemas/trajectory-event.schema.json` is regenerated from the Pydantic model;
  its freshness test owns the projection; and
- the schema requires envelope version and all five nullable source fields while
  preserving the existing optional payload contract.

Not proven:

- the modest KAE alias vocabulary matches current Kenshi Agent Environment log
  authority or can import a current real run without a subject-owned adapter;
- skipped unknown non-strict KAE records provide a complete source trajectory;
- a receipt or normalized world revision proves any live game effect;
- evolution stages can resume across processes or hash mismatches, which remains
  Goal 4; or
- OpenTTD or Kenshi is registered, controlled, or live-proven as a subject.

## Verification and independent review

The one local and CI authority remains:

```bash
uv run --frozen --extra dev python scripts/verify.py
```

Before checkpoint refresh, 96 non-checkpoint tests passed together with Ruff,
strict mypy, schema freshness, and whitespace checks. The focused trajectory,
KAE, ledger, schema, and model surface passed 33 tests in the final independent
replay. With this checkpoint present, the authoritative dirty-candidate gate
passed compile, Ruff, strict mypy, a fresh wheel build and entry-point metadata
check, all 97 tests, the exact retained microworld cycle, and whitespace checks.
The checkpoint ratchet is rerun once more from the clean commit.

Pre-write authority mapping and adversarial fixture design were delegated to two
read-only Luna agents. A separate Luna writer produced the candidate without
checkpoint or commit authority. Independent adversarial review rejected the
first candidate for mixed-envelope acceptance, duplicate normalized IDs,
multi-run laundering, malformed provenance coercion, normalized-sequence
coercion, and a model/schema/parser requiredness mismatch. Each finding was
re-delegated with a durable falsifier. The independent reviewer replayed every
failure after correction and returned an explicit pass with no remaining G03
blocker. Candidate-author diagnostics were not used as certification.

## External subject availability

Kenshi Agent Environment remains a separate subject repository. Its exact
integration baseline must be resolved again when Goal 9 starts.

OpenTTD 15.3 remains installed at `C:\Program Files\OpenTTD`. The installed
`openttd.exe` SHA-256 is
`360f615cb74cafcedf0486398a396577e8f1470e0f8158f66b7e29557fdb711d`.
This is availability evidence only: it has not been correlated to the pinned
upstream source, configured for headless execution, or accepted as a subject.

## Completion boundary

This checkpoint is part of the coherent Goal 3 candidate. Goal 3 is complete
only after the authoritative gate passes with this dirty checkpoint, the final
diff is reviewed and committed, the clean-state checkpoint ratchet passes, and
the tree is clean and synchronized with the public remote.

Goal 4 is the sole next packet and remains unstarted. `TrajectoryRecorder`
rejects a reopened trace that appends a second sequence zero when it is read;
persisted cross-process writer/resume ownership belongs to Goal 4 and must not be
smuggled into this identity commit.
