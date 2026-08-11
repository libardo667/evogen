# Architecture

## Governing question

EvoGen is built around one transformation:

```text
trajectory evidence -> failure-layer diagnosis -> capability change
```

Implementation agents are downstream machinery. The system is not successful
merely because an agent can edit code. It must identify the right layer, state a
falsifiable prediction, preserve counterevidence, and demonstrate generalized
behavioral improvement.

## Runtime plane

The runtime plane belongs to the subject agent. EvoGen expects events that retain
these distinctions:

1. an observation was produced;
2. a semantic action was offered;
3. an executor selected it;
4. the exact target and preconditions were rebound against fresh state;
5. a command was dispatched;
6. the environment or controller accepted or rejected execution; and
7. later world evidence did or did not establish the intended effect.

A subject can produce more events, but it should not collapse these into one
"action succeeded" assertion.

## Evolution plane

The evolution plane owns immutable generations and candidate descendants.

```text
observed runs
  -> trace distillation
  -> issue diagnosis
  -> investigation or probe
  -> capability specification
  -> isolated candidate
  -> adversarial review
  -> comparative experiment
  -> deterministic gate
  -> lineage
```

The current reference cycle is synchronous and local. Every stage emits a typed
artifact, so stages can later be queued, distributed, or performed by different
models without changing the evidence model.

## Data ownership

### GenerationManifest

Names the complete subject state relevant to behavior. Source commit alone is
insufficient; models, prompts, configuration, capability manifests, and build
artifacts may all alter behavior.

### TrajectoryEvent

An append-only normalized event with envelope version `1.0`. The event owns run,
generation, scenario, and an EvoGen-owned `sequence`: the unique, strictly
monotonic normalized order within a run. Source systems may provide independent
provenance (`source_event_type`, `source_event_id`, `source_sequence`,
`source_step_index`, and `source_world_revision`), but those fields never define
normalized order. `world_revision` remains the normalized correlation field;
source provenance is nullable when unavailable. The alpha JSONL reader upgrades
unversioned records only when all six new envelope/provenance fields are absent;
partially migrated records are rejected.

### CapabilityManifest

Declares the agent's current semantic body. A capability records purpose,
semantic effects, applicability, implementation route, completion evidence,
limits, and proof class.

### CapabilityIssue

An evidence-backed claim about a deficiency or unsafe abstraction. It retains
alternative diagnoses and known unknowns. A low score alone is not an issue.

### CapabilitySpec

The contract passed to implementers. It fixes semantics, binding, execution,
completion evidence, non-goals, acceptance cases, and implementation constraints
before code is written.

### CandidateManifest

An isolated descendant proposal. It records parent, originating issue/spec,
workspace, source digest, changed files, claimed capability, and artifacts.

### ExperimentResult

A baseline/candidate comparison represented as a metric vector rather than a
single reward. It includes every scenario result and whether the stated
prediction matched.

### GateDecision

A deterministic retain, revise, or reject result. A retained generation is valid
only for a retain verdict.

## Storage

`ArtifactStore` writes immutable bytes under their SHA-256. `Ledger` indexes JSON
records in SQLite. The ledger is not the sole copy of large evidence; it points to
content-addressed objects and trace files.

The alpha runs locally and trusts the workspace filesystem. A production version
would add signed manifests, explicit artifact media types, transactional candidate
promotion, and remote object-store support.

## Agent-role separation

The intended roles are:

- trace analyst;
- diagnostician;
- investigator;
- capability architect;
- implementer;
- adversarial reviewer;
- evaluator; and
- release steward.

Roles communicate through artifacts, not an unbounded shared chat. The same model
may perform several roles in separate contexts, but the implementer must not
supply the final evaluation or retention verdict.

## Observer mode and hosted mode

Observer mode leaves the subject runtime intact. EvoGen normalizes its traces and
controls only the outer loop. This is the correct first integration for KAE.

Hosted mode would use EvoGen's runtime contracts directly for observations,
affordances, binding, execution, receipts, and continuity. Hosted mode is not
required for the outer loop and should not be allowed to force premature shared
runtime abstractions.
