# Kenshi Agent Environment integration

Kenshi Agent Environment should begin as an EvoGen subject, not be refactored
wholesale into EvoGen.

## Keep in KAE

- native mod and reverse-engineering evidence;
- Kenshi telemetry ontology and protocol;
- operation definitions and affordance adapters;
- game installation, launch, save, and recovery machinery;
- authored starts and save fixtures;
- strategy knowledge; and
- live proof bundles.

## Export to EvoGen

- generation manifest: source commit, installed DLL hash, planner/advisor models,
  prompt/config digests, schema versions, and operation/proof manifest;
- normalized trajectories retaining observation, affordance, binding, command,
  monitor, result, later state, intervention, and finalization;
- scenario identifiers and attestation digests;
- candidate workspace/build/test commands; and
- domain metrics such as intervention-free horizon, repeated failures, recovery,
  command ambiguity, and final safe state.

## Current trajectory boundary

```text
kenshi-agent-env
  -> ./dev trajectory-export (exact reviewed KAE event projection)
  -> raw-events.jsonl + trajectory.jsonl + manifest.json
  -> EvoGen read_jsonl_events (strict current envelope)
  -> diagnosis/spec/candidate/evaluation
  -> human-approved KAE sandbox installation
  -> supervised live proof
```

KAE owns the production exporter at commit `548658cbcef35037252e63be40248fa6a94b5ec1`.
It validates the reviewed source-event disposition inventory, retains every raw
record byte-for-byte, and emits only the exact current EvoGen envelope. EvoGen
does not guess event types, reorder by `step_index`, or expose a KAE normalizer
CLI. The generic reader accepts current envelopes (and its existing alpha
compatibility format) but rejects raw KAE records.

The compact checked-in contract fixture retains the raw source, export manifest,
and normalized trajectory. It proves source and normalized digests, encounter
ordering, receipt versus later outcome, `world_state_update` as an observation
delta, and the explicit withholding of binding and dispatch. This is portable
contract evidence only, not evidence of a game-world effect.

Two older raw traces remain solely as historical diagnosis evidence. The
test-only `tests/support/historical_kenshi_fixture.py` reader names those files
explicitly and is not importable from the production package or CLI. New KAE
bundles must use KAE's exact exporter instead.

## Historical-case corpus

Recent KAE development already contains useful labeled cases:

- a trade interface opened without a supported close path;
- bounded scans presented as complete;
- a task-probability mechanism emitted false affordances and crashed;
- selected or queued workers confused with accepted operators;
- player topology fields collapsed despite different ownership;
- pointer calibration retained after coordinate-independent operations; and
- equipped items withheld due to an earlier misdiagnosed transfer crash.

Each case can become a hidden-answer package:

```text
case/
  parent-generation.json
  evidence/
  source-ref.txt
  hidden-human-diagnosis.json
  hidden-capability-spec.json
  resulting.patch
  verification/
```

The first evaluation should ask a diagnostician to classify and specify the fix
from pre-fix evidence without seeing the historical answer. Agreement with the
human diagnosis is useful, but behavioral evaluation remains the final test.

## First live milestone

EvoGen should not claim a KAE success until it:

1. observes a previously unknown live capability deficit;
2. creates an evidence-backed issue;
3. distinguishes capability absence from planning misuse and environment refusal;
4. researches the actual Kenshi/KenshiLib surface;
5. implements in an isolated branch/worktree;
6. passes portable, replay, regression, and long-run gates;
7. receives human approval for installation; and
8. closes the original deficit in a supervised live proof bundle.
