# Integration checkpoint: KAE run-local event sequence

This document is the current repository authority for one bounded integration
goal. It is replaced in the same commit as every completed goal; Git history
retains older checkpoints.

## Repository and planning authority

```text
parent commit                    cf70589f91add9c9dbe6affd11866b20d2690642
integration branch               main
current goal                     Goal 10 - Add logger-owned event sequence
next unstarted goal              Goal 11 - Add generation manifest
KAE parent commit                b8544b88b8c610f2859298308b0adaca290c9ddc
KAE completion commit            7e25459c992572b0f102297420f7117fbc2146d7
KAE-recorded EvoGen counterpart  cf70589f91add9c9dbe6affd11866b20d2690642
KAE public remote                https://github.com/libardo667/kenshi-agent-env
KAE hosted run                   31538471899
alpha release commit             9c8d94c59a95222a719e20fac5a61d2ec712743d
source plan revision             2026-08-10T21:25:08.835Z
execution plan                   docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 10 began from clean, synchronized KAE `main` after the complete Goal 9
event-disposition inventory. This EvoGen commit changes only the durable
planning ratchet; implementation and evidence live in the exact KAE completion
commit above.

## Behavioral change and authority

Source-proven in KAE:

- every newly written session record has a logger-owned, one-based
  `event_sequence`;
- sequence allocation, JSON serialization, append, and immediate flush share
  one lock, so serialized file order is sequence order for the production
  shared logger;
- uncertain I/O retires its attempted identity instead of permitting a later
  duplicate;
- reopening an append log continues after legacy and sequenced rows for the
  same run, preserves complete final JSON without a newline, and removes only
  a provably invalid unterminated crash fragment;
- `SessionEvent.event_sequence` is optional and positive, preserving typed
  compatibility with legacy dictionary-payload rows;
- `step_index` remains nullable gameplay evidence and nested telemetry sequence
  remains a separate world-revision field; and
- no overlay, replay, evaluator, environment, native-controller, or gameplay
  semantics changed.

The committed sequence fixture contains records `1..4`: a run-level record and
three rows sharing step 7 and telemetry revision 42. The historical 45-row
reporting fixture remains byte-unchanged and has no sequence field.

G09 freshness remains active. The semantic denominator is still 89 event types
and 127 producer records. The crash-tail separator adds one explicitly reviewed
non-event write, so the generated inventory now has 17 open boundaries and
fingerprint
`232a934c595657d6189d9ab39dc347b4af711d86814fc071ec263e51da3ad60b`.

## Verification and independent review

The focused proof writes 1,024 events from eight threads, all at gameplay step
7 and telemetry revision 314159. It requires all `(writer, ordinal)` identities
to survive and file-order sequences to equal exactly `1..1024`. Additional
tests prove nullable-step independence, run-local reset, legacy continuation,
valid no-newline preservation, invalid crash-tail repair, ambiguous flush
identity retirement, and both committed fixture contracts.

Lamport, Hoare, and Dijkstra independently audited logger authority, consumer
compatibility, and concurrency falsifiers. Candidate review found two genuine
defects: duplicate reuse after an ambiguous flush failure and retention of an
invalid unterminated tail. Root repaired both and added regression tests;
Lamport reran the exact adversarial probes and passed the repaired candidate.

Root then passed KAE's complete portable gate:

```bash
UV_CACHE_DIR=/tmp/kae-g10-uv-cache \
RUFF_CACHE_DIR=/tmp/kae-g10-ruff-cache \
MYPY_CACHE_DIR=/tmp/kae-g10-mypy-cache \
./dev verify-portable
```

That gate covered locked dependency sync, Ruff, strict mypy over 150 source
files, research validation, event-map/schema/document generation and freshness,
the complete pytest suite, and whitespace checks.

The exact KAE completion commit passes hosted run
`https://github.com/libardo667/kenshi-agent-env/actions/runs/31538471899` on
Python 3.11, 3.12, 3.13, and 3.14. Candidate-author diagnostics were not used
as certification.

This EvoGen planning ratchet passes `uv run python scripts/verify.py`: source
and test compilation, Ruff, strict mypy over 47 source files, wheel build and
entry-point inspection, 264 tests, a fresh deterministic microworld cycle, and
`git diff --check`.

## Withheld claims and completion boundary

`event_sequence` records session-log order only. It does not certify dispatch,
acceptance, completion, a world effect, goal progress, or goal achievement. It
is not a cross-run, cross-process, telemetry, gameplay, or charged-turn clock.
G10 adds no EvoGen exporter or trajectory envelope, changes no live process or
game artifact, and makes no power-loss-durability claim.

Goal 10 is complete at KAE commit
`7e25459c992572b0f102297420f7117fbc2146d7`. This planning-ratchet candidate is
complete only after EvoGen verification, commit, clean checkpoint mode, public
push, and hosted Python 3.11-3.13 matrix are green.

Goal 11 is the sole next packet and remains unstarted here. It owns generation
provenance, effective configuration, secrets exclusion, and the generation
manifest. No Goal 12 affordance-event or Goal 14 exporter work is authorized in
that slice.
