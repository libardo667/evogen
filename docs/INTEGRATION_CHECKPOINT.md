# Integration checkpoint: serial G13 prerequisite contract candidate

This document is the current repository authority for one bounded integration
slice. Git history retains the completed G12 checkpoint. This candidate freezes
the EvoGen contract that KAE's next generated manifest must satisfy; it does not
advance the numbered-goal queue by itself.

## Repository and planning authority

```text
parent commit                    eb07feb10dbdaba30151d6338eca837a5c47d4ba
integration branch               main
current goal                     Goal 12 - Log the exact affordance set
next unstarted goal              Goal 13 - Generate KAE capability manifest
KAE parent commit                bfaa4d55ae10a34d33e7a06ee3959fc6659eceb4
KAE completion commit            0560b9de6e049f0dc06fab9afbef76f76d198092
KAE-recorded EvoGen counterpart  c37147b3120c38c9a979ca8671fcc11c5ab62c6c
KAE public remote                https://github.com/libardo667/kenshi-agent-env
KAE hosted run                   31703301693
EvoGen plan ratchet commit       ef27a9bc440b789a89bf5e1582868d21c244d2f7
EvoGen cockpit proof commit      643ca51b04d8c8e21d5a1478e6fa6542f3b9e36a
EvoGen hosted run                31704114352
alpha release commit             9c8d94c59a95222a719e20fac5a61d2ec712743d
source plan revision             2026-08-10T21:25:08.835Z
execution plan                   docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 12 remains the latest closed numbered goal at the exact KAE commit above.
The current EvoGen changes are a serial prerequisite discovered while mapping
G13: the old generic capability model could not represent absent, unknown, or
unsupported evidence without assigning a proof class. KAE must not invent
subject conformance merely to fit that weaker shape.

## Generic capability contract

The prerequisite makes these rules explicit in EvoGen's authoritative Pydantic
models and generated JSON Schemas:

- `CapabilityKind` has exactly six values: sensing, representation, memory,
  action, verification, and recovery;
- `EvidenceState` distinguishes proven, absent, unproven, withheld, unknown,
  and unsupported;
- a proven capability requires a proof class and at least one typed,
  content-addressed evidence reference;
- non-proven capabilities cannot carry a proof class, and absent capabilities
  cannot carry evidence references;
- identity and semantic strings cannot be blank;
- `semantic_effects` contains at least one nonblank effect so diagnosis can
  distinguish an existing capability from a missing effect;
- manifest capability names are unique and canonically sorted; and
- `introduced_generation` records lineage independently of the generation that
  currently publishes the manifest.

The contract remains subject-neutral. EvoGen core imports no KAE object, and
the detailed Kenshi proof artifacts stay in KAE. A subject manifest may refer to
those artifacts by stable authority reference and digest without copying an
incident narrative into reusable semantics.

This is an intentional alpha contract cutover. Older capability payloads that
omit explicit evidence state or rely on the former default portable proof class
are refused rather than silently upgraded into claims the retained artifact did
not make.

## Existing subject behavior

The microworld's built-in and generated capabilities now state `unproven`
instead of treating their own source bytes as behavioral proof. This preserves
the deterministic runnable cycle while honoring two existing invariants:
dispatch is not proof of a world effect, and candidate authors do not certify
their own work. Built-in capabilities retain their `genesis` lineage when a
later generation is materialized; only a newly retained capability names its
actual introduction generation.

This prerequisite changes no environment, evaluator, scenario, operation, or
selection rule. It launches no game, sends no input, contacts no model provider,
and claims no external world effect.

## Generated authority and verification

`evogen.schema.MODEL_REGISTRY` owns the generated capability-definition,
capability-evidence-ref, and capability-manifest schemas. The project cockpit is
regenerated from this checkpoint and the still-G13-next execution plan.

The complete repository gate is:

```bash
UV_CACHE_DIR=/tmp/evogen-uv-cache \
  uv run --frozen --extra dev python scripts/verify.py
```

It covers compileall, Ruff, mypy, wheel construction and entry-point metadata,
all tests, the deterministic end-to-end microworld evolution demo, generated
schema and cockpit freshness, and `git diff --check`. The uncommitted candidate
passes that full gate locally. Hosted EvoGen CI remains required after its exact
public commit.

## Completion boundary

This commit will establish only the generic prerequisite and its exact public
identity. G13 remains incomplete until KAE generates its manifest from existing
operation, affordance, native, protocol, continuity, outcome, recovery, and
proof authorities; independent reviewers accept the final projection; the full
KAE portable gate passes; both repositories record exact counterpart commits;
the public hosted matrices pass; and the central plan and cockpit are ratcheted.

G14 trajectory export and G15 subject registration remain unstarted. No agent
may begin either one as part of this slice.
