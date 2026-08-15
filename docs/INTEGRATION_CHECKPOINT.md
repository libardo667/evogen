# Integration checkpoint: G14 exact KAE trajectory contract consumed

This document is the current repository authority for one bounded integration
goal. Git history retains the completed prerequisite-contract checkpoint.

## Repository and planning authority

```text
parent commit                    6954f8bc1e0ad95a9ccd9486fe58999dce5cf885
integration branch               main
current goal                     Goal 14 - Replace the provisional normalizer with an exact KAE exporter
next unstarted goal              Goal 15 - Register KAE as an EvoGen subject plugin
KAE parent commit                a8584554e30bb793f5b60ef57e3d1500de5aaa12
KAE completion commit            548658cbcef35037252e63be40248fa6a94b5ec1
KAE-recorded EvoGen counterpart  6954f8bc1e0ad95a9ccd9486fe58999dce5cf885
KAE public remote                https://github.com/libardo667/kenshi-agent-env
KAE hosted run                   31906703483
EvoGen prerequisite commit       6954f8bc1e0ad95a9ccd9486fe58999dce5cf885
EvoGen prerequisite hosted run   31903804873
EvoGen G14 implementation commit pending root review
EvoGen G14 implementation run    pending publication
EvoGen G14 ratchet commit        candidate working tree
EvoGen G14 ratchet run           pending publication
alpha release commit             9c8d94c59a95222a719e20fac5a61d2ec712743d
source plan revision             2026-08-10T21:25:08.835Z
execution plan                   docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 14 began from clean, synchronized KAE `main` after G13's generated
capability authority. KAE then published the exact reviewed trajectory exporter
at `548658cbcef35037252e63be40248fa6a94b5ec1`. EvoGen consumed its strict
current-envelope contract, removed the provisional broad alias/step-index
normalizer and CLI, and retained only an explicitly fixture-scoped historical
reader for the two pre-G14 diagnosis traces.

The candidate adds an exact compact KAE bundle fixture containing raw events,
manifest, and trajectory bytes. Its focused tests verify source and trajectory
digests, five-record counts, strict current-envelope round-trip, exact receipt,
outcome, and observation-delta mappings, and explicit binding/dispatch
withholding. Root review must replace the pending hosted fields above with the
final EvoGen commit and hosted proof before public ratcheting.

## Navigator-approved proof-first route

The navigator approved a proof-first execution order after G13. The checked-in
sequenced plan is now the scheduling authority: it tells the root which goal is
permitted next and when to re-fetch the Drive master plan for the detailed goal
contract. The Drive source remains authoritative for what each numbered goal
must prove; it is not used to silently reorder work between those lookups.

The route is G14-G17 for a real KAE replay showcase; G18 and G22-G27 for one
historical evolution; G28-G29 for one supervised live evolution; G19-G21 for
the deferred corpus, blind benchmark, and external-model study; then G30-G49
for OpenTTD and release. G26 precedes G27 so the historical cycle consumes a
frozen suite and provenance authority. While G21 is deferred, G22 is limited
to a deterministic or human-authored investigator. G30 depends on both G21 and
G29, so neither the scientific-depth branch nor the supervised-live branch can
be bypassed.

Every numbered goal still closes, is independently reviewed, updates the
checkpoint, and stops before the next goal begins. The reusable cockpit must
make each milestone's newly available proof and strongest withheld claim
visible. At this checkpoint G14 is closed in scope but still awaits its EvoGen
commit, public push, and hosted ratchet. G15 is the sole next packet and must
not begin before that publication boundary is complete.

## Generated subject authority

KAE now provides one canonical, content-addressed capability projection and a
read-only public command:

```bash
./dev capability-manifest --generation-id <sha256> --output <path>
```

The projection derives action rows from `OPERATION_DEFINITION_LIST`, checks the
exact affordance-adapter inventory, derives native sensing and representation
rows from schema-2 `GameplayCapabilities.json`, and imports small immutable
descriptors from the modules that own planner representation, Protocol 2,
continuity, outcome verification, and final recovery. The proof ledger supplies
evidence state and content-addressed references, not a second semantic registry.

The retained zero-generation fixture contains 69 unique, canonically sorted
rows across the six required kinds:

- 26 action;
- 27 sensing;
- 13 representation;
- one memory;
- one verification; and
- one recovery.

Evidence remains explicit: 23 rows are proven, 45 are unproven, and one is
unsupported. `action.respond_to_immediate_threat` remains unsupported because
its operation requires `nearby.visible_entities`, while the current native
authority provides `nearby.characters` and `nearby.roles`. G13 preserves that
boundary instead of changing telemetry or inventing conformance.

## Identity, evidence, and failure boundaries

Generation identity includes canonical digests for native declarations,
operations, affordances, telemetry, protocol, continuity, outcome, recovery,
and proof authority. The generation ID is computed from those inputs before the
generated capability bytes are linked into `GenerationManifest`, avoiding a
self-referential fixed point. All imported rows retain the explicit lineage
marker `kae-g13-import` rather than claiming that each later publication
introduced them.

The proof-ledger path and native-authority path are each threaded explicitly
through generation and capability construction. Referenced proof artifact bytes
participate in content identity. Ordering-only changes remain stable, while
semantic mutations to every contributing authority change the generation
identity or fixed-generation capability bytes.

Proven rows require typed evidence references and proof classes. Absent,
unproven, withheld, unknown, and unsupported states remain distinct and cannot
carry a proof class. Evidence paths are repository-relative, tracked regular
files and cannot escape through absolute paths, traversal, or symlinks. Output
publication rejects symlink traversal and uses atomic replacement plus file and
directory synchronization.

The native JSON change adds category metadata only. The generated C++ gameplay
capability header remains byte-identical to exact G12 parent
`0560b9de6e049f0dc06fab9afbef76f76d198092`. No native runtime behavior,
protocol, environment, evaluator, game process, save, installed DLL, or live
world state changed.

## Independent review and verification

Hopper authored the final KAE repairs. Faraday independently audited authority,
identity, proof preservation, native stability, and scope. Averroes independently
audited acceptance and adversarial falsifiers. Both initially rejected the
candidate for durable proof gaps: split proof paths, a post-commit header
self-comparison, schema/runtime drift, whitespace-only evidence references, and
incomplete descriptor mutation coverage. Hopper repaired those findings; both
reviewers retested the exact final tree read-only and returned PASS.

The KAE completion commit passed `./dev verify-portable` before and after commit.
That gate covered locked dependency installation, Ruff, strict mypy over 156
source files, reverse-engineering evidence, generated event/schema/document
freshness, the full test suite, and whitespace checks. Public hosted run
`https://github.com/libardo667/kenshi-agent-env/actions/runs/31720597916`
passed Python 3.11, 3.12, 3.13, and 3.14 at the exact completion commit.

The EvoGen prerequisite commit passed the complete repository verifier locally
and public hosted run
`https://github.com/libardo667/evogen/actions/runs/31717965263` on Python 3.11,
3.12, and 3.13. This central ratchet must pass the same complete command:

```bash
UV_CACHE_DIR=/tmp/evogen-uv-cache \
  uv run --frozen --extra dev python scripts/verify.py
```

## Goal 14 evidence and completion boundary

The exact KAE exporter retains raw source bytes and emits a strict current
trajectory envelope. The EvoGen compact fixture records five source records and
five normalized events with source sequences `1..5` and normalized sequences
`0..4`. `action_receipt` remains `execution_receipt`, `action_outcome` remains
`outcome_observation`, and `world_state_update` remains `observation_delta`.
Binding and dispatch are explicitly withheld. Receipt, acknowledgement, or
process exit is not a later world effect.

The stronger retained KAE soak has source SHA-256
`542eff1353e00b9cd4cad4c83969e4db9156776d7c55b5e51d01a0356ffb92ef`.
KAE's public command retained all 38,293 raw records and projected 22,995 strict
events: 11,308 observations, 11,308 observation deltas, 126 outcome
observations, 121 decisions, 119 execution receipts, 11 errors, one run start,
and one run finish. EvoGen's actual `read_jsonl_events` parsed all 22,995 with
normalized sequence `0..22994`, unique event IDs, and singular run/generation
identity. The soak predates G11 and lacks a contemporaneous generation manifest,
so this proves exporter compatibility with the exact supplied manifest bytes,
not the generation that originally produced the run.

The EvoGen candidate deletes `KenshiJsonlAdapter` and the `normalize-kae` CLI.
The generic `read_jsonl_events` path accepts current envelopes and rejects raw
KAE records. The two historical raw traces remain checked-in evidence; a
test-only literal reader under `tests/support` serves only those named fixtures
for diagnosis coverage. No KAE package is imported by production EvoGen code.

Hypatia authored the isolated EvoGen retirement candidate. Root repaired one
literal historical-fixture omission and then found that the real repository's
existing `build/` directory could leak deleted modules into a new wheel. The
repository verifier now cleans that generated directory and rejects any wheel
that contains the retired KAE package. Curie independently reviewed the strict
production boundary and historical quarantine and returned PASS. Averroes
independently blocked first on contradictory checkpoint prose and then on stale
generated cockpit artifacts. After both repairs, he reran the authority and
freshness checks and returned PASS.

Goal 14 is complete in scope at KAE commit
`548658cbcef35037252e63be40248fa6a94b5ec1` plus the EvoGen candidate described
above. Root review, a final EvoGen commit, the complete verifier, public push,
and hosted matrix remain required to replace the pending fields and publish the
cross-repository ratchet. Goal 15 is the sole next packet. It owns optional KAE
subject registration; G16, G17, live effects, and retained capabilities remain
unstarted or withheld.
