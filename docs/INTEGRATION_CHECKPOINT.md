# Integration checkpoint: Exact KAE generation manifest

This document is the current repository authority for one bounded integration
goal. It is replaced in the same commit as every completed goal; Git history
retains older checkpoints.

## Repository and planning authority

```text
parent commit                    303701c078ead81f1886933d10faa5d0891fac8d
integration branch               main
current goal                     Goal 11 - Export exact KAE generation manifest
next unstarted goal              Goal 12 - Log the exact affordance set
KAE parent commit                7e25459c992572b0f102297420f7117fbc2146d7
KAE completion commit            bfaa4d55ae10a34d33e7a06ee3959fc6659eceb4
KAE-recorded EvoGen counterpart  303701c078ead81f1886933d10faa5d0891fac8d
KAE public remote                https://github.com/libardo667/kenshi-agent-env
KAE hosted run                   31542719034
alpha release commit             9c8d94c59a95222a719e20fac5a61d2ec712743d
source plan revision             2026-08-10T21:25:08.835Z
execution plan                   docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 11 began from clean, synchronized KAE `main` after the complete Goal 10
logger migration. This EvoGen commit changes only the durable planning ratchet;
implementation and evidence live in the exact KAE completion commit above.

## Behavioral change and authority

Source-proven in KAE:

- `./dev generation-manifest --output ...` is read-only with respect to the
  repository and game and writes a strict, versioned JSON manifest atomically;
- the top-level document validates through EvoGen's current
  `GenerationManifest` model without importing EvoGen into ordinary KAE use;
- identity is canonical and covers Git source state, `uv.lock`, active model
  routes, raw prompt and strategy corpus, rendered planner policy, redacted
  effective configuration, protocols and schemas, generated and semantic
  operation definitions, proof ledger, memory schema, scenario and authored
  start, Kenshi target/observation, and independent native artifacts;
- a requested output inside the checkout is lexically excluded from its own Git
  fingerprint, so publication cannot recursively change the identity;
- scenario and authored-start lineage are independent channels and may coexist;
- built, staged, and installed DLL evidence preserves present, absent, and
  unreadable states independently, with parity only when both inputs exist;
- Kenshi target identity remains separate from optional observed executable
  bytes and does not identify a running process; and
- schema and CLI documentation are generated from source and freshness-tested.

KAE's G09 source-sink authority remains active. The manifest publication was
explicitly reviewed as a non-event file write, increasing the generated open
boundary inventory without pretending it is a session event.

The capability digest currently projects KAE's native
`GameplayCapabilities.json`. The manifest metadata labels this authority
provisional until G13. Serialized-envelope compatibility is therefore proven;
an EvoGen `CapabilityManifest` CAS and full subject-conformance/bootstrap are
not claimed.

## Redaction, stability, and mutation proof

KAE inspects configuration references before interpolation. Unknown and
credential-like environment references fail closed, including nested default
forms. Paths become role markers, arbitrary strings are hashed, and mutable
telemetry, memory, runtime-scenario, and attestation payloads remain in their
own authorities instead of contaminating effective configuration.

The command does not load `.env`, enumerate process environment, serialize API
keys, or let unrelated variables such as `HOME` affect generation identity.
Model identifiers use a narrow reviewed projection and reject path-like,
credential-like, malformed, and overlong values. Symlink outputs, symlinked
parents, and existing non-files are rejected before publication.

The focused suite proves:

- two materially identical invocations are byte-identical;
- planner model, advisor model, prompt, strategy corpus, generated operation
  definition, semantic operation registry, protocol schema, and installed DLL
  mutations each change identity;
- schema key reordering alone does not change identity;
- missing and unreadable artifacts do not collapse into empty content; and
- serialized output contains neither tested secrets nor host paths.

On the clean KAE completion commit, two real-host invocations produced the same
generation ID:

```text
generation ID       1cab62443f02231a32ef216638393808b51b1563e226d1be09db35e03d07815a
source ref          bfaa4d55ae10a34d33e7a06ee3959fc6659eceb4
Kenshi version      1.0.65
Steam build         13871665
Kenshi target       observed bytes matched repository target
built vs installed  matched
staged vs installed did not match and remained separately visible
```

These are file-identity results, not running-process or world-effect evidence.

## Independent review and verification

Shannon mapped source and generated provenance authorities. Dwork designed the
configuration and secret threat model. Merkle designed stable-identity and
mutation falsifiers. Hopper expanded the executable test suite. Saltzer's
security review found and then verified repairs for model-ID leakage,
symlink/path safety, external-target mutation, and absent-versus-unreadable
evidence. Knuth verified every source-plan field, all required mutation
triggers, generated-artifact freshness, local CLI behavior, and parsing through
EvoGen's exact current model.

Root then passed KAE's complete portable gate after repairing two integration
findings it exposed: classification of the new file write in the source-sink
inventory, and removal of a schema-export/import cycle through a neutral shared
schema authority. The final gate covered locked dependency sync, Ruff, strict
mypy over 152 source files, research validation, event-map/schema/document
generation and freshness, the full pytest suite, architecture checks, and
whitespace checks.

The exact KAE completion commit passes hosted run
`https://github.com/libardo667/kenshi-agent-env/actions/runs/31542719034` on
Python 3.11, 3.12, 3.13, and 3.14. Candidate-author diagnostics were not used
as certification.

This EvoGen planning ratchet must pass both repository acceptance commands:

```bash
UV_CACHE_DIR=/tmp/evogen-uv-cache uv run pytest
UV_CACHE_DIR=/tmp/evogen-uv-cache \
  uv run evogen demo --workspace .evogen-demo --clean
```

It also runs the repository's complete `scripts/verify.py` gate before commit.
Hosted EvoGen CI remains the post-push completion authority.

## Withheld claims and completion boundary

The generation manifest proves stable typed provenance of identified files and
configuration authorities. It does not certify that a DLL is loaded, a process
is the observed executable, a command was accepted or completed, a world effect
occurred, or a goal progressed. G11 changes no runtime plane, planner behavior,
evaluator, native controller, save, installed DLL, or live game state.

Goal 11 is complete at KAE commit
`bfaa4d55ae10a34d33e7a06ee3959fc6659eceb4`. This planning-ratchet candidate is
complete only after EvoGen verification, commit, clean checkpoint mode, public
push, and hosted Python matrix are green.

Goal 12 is the sole next packet and remains unstarted here. It owns a dedicated
`affordance_set` event at the authoritative enumeration path immediately before
planner delivery, with exact replay reconstruction and no prompt parsing. G13
still owns permanent capability-manifest authority; G14 still owns production
trajectory export.
