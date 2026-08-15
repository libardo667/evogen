# Integration checkpoint: G15 KAE subject plugin registered

This document is the current repository authority for one bounded integration
goal. Git history retains the completed prerequisite-contract checkpoint.

## Repository and planning authority

```text
parent commit                    ee89104fde397ab9de6f5b7dcfee09f372879827
integration branch               main
current goal                     Goal 15 - Register KAE as an EvoGen subject plugin
next unstarted goal              Goal 16 - Build observer and replay runners first
KAE parent commit                548658cbcef35037252e63be40248fa6a94b5ec1
KAE completion commit            2c2eb36e4f0b0438f1c42030d56f3a872007264d
KAE-recorded EvoGen counterpart  ee89104fde397ab9de6f5b7dcfee09f372879827
KAE public remote                https://github.com/libardo667/kenshi-agent-env
KAE hosted run                   31913192879
EvoGen prerequisite commit       ee89104fde397ab9de6f5b7dcfee09f372879827
EvoGen prerequisite hosted run   31908691766
EvoGen G14 completion commit     5e72ca364f0a1b2c5b23d41c9af5a2a15099b946
EvoGen G14 hosted run            31908510607
alpha release commit             9c8d94c59a95222a719e20fac5a61d2ec712743d
source plan revision             2026-08-10T21:25:08.835Z
execution plan                   docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 15 began from clean, synchronized KAE `main` at the completed G14 exporter
commit. KAE then published the optional subject plugin at the exact completion
commit above. The installed plugin preserves KAE's generated authorities while
keeping the game runtime and ordinary KAE imports independent of EvoGen.

The following context retains the G14 prerequisite boundary. Goal 14 began from
clean, synchronized KAE `main` after G13's generated
capability authority. KAE then published the exact reviewed trajectory exporter
at `548658cbcef35037252e63be40248fa6a94b5ec1`. EvoGen consumed its strict
current-envelope contract, removed the provisional broad alias/step-index
normalizer and CLI, and retained only an explicitly fixture-scoped historical
reader for the two pre-G14 diagnosis traces.

The completion commit adds an exact compact KAE bundle fixture containing raw events,
manifest, and trajectory bytes. Its focused tests verify source and trajectory
digests, five-record counts, strict current-envelope round-trip, exact receipt,
outcome, and observation-delta mappings, and explicit binding/dispatch
withholding. Public hosted run `31908510607` passed the full verifier on Python
3.11, 3.12, and 3.13 at that exact commit.

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
visible. At this checkpoint G15 is closed, public, and hosted-green at the
exact evidence fields above. G16 is the sole next packet and begins only in a
new bounded slice after this metadata ratchet is published.

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

The historical G13 KAE completion commit passed `./dev verify-portable` before
and after commit.
That gate covered locked dependency installation, Ruff, strict mypy over 156
source files, reverse-engineering evidence, generated event/schema/document
freshness, the full test suite, and whitespace checks. Public hosted run
`https://github.com/libardo667/kenshi-agent-env/actions/runs/31720597916`
passed Python 3.11, 3.12, 3.13, and 3.14 at the exact completion commit.

The historical G13 EvoGen prerequisite commit passed the complete repository
verifier locally and public hosted run
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

Goal 14 is complete at KAE commit
`548658cbcef35037252e63be40248fa6a94b5ec1` and EvoGen commit
`5e72ca364f0a1b2c5b23d41c9af5a2a15099b946`, with both hosted matrices green.

## Goal 15 evidence and completion boundary

KAE now publishes an optional `kenshi` entry point in `evogen.subjects`. The
wheel contains the KAE-owned API 1.1 factories and generated capability
authority; ordinary KAE installs and imports do not acquire EvoGen. A fresh
KAE-only wheel environment proved that separation before the exact public
EvoGen commit was added and metadata discovery loaded the installed plugin.

The synthetic conformance runner preserves dispatch, receipt, and later outcome
as separate typed events. Improvement requires the exact generated source bytes
to match both the declared source digest and plugin artifact digest; altered
source or artifact bytes remain blocked. Retained conformance materialization
adds only `kae_synthetic_observation`, with proven synthetic experiment evidence
and explicit no-live, no-replay, no-native, and no-world-effect limitations.

Noether authored the isolated candidate. Curie first blocked it for a mock
success path and event-inventory bypasses, then reproduced the repaired causal
falsifiers, installed-wheel discovery, fail-closed event inventory, and retained
synthetic evidence before returning PASS. Root byte-compared the accepted
candidate into the real KAE checkout and reran the complete gate before and
after commit. Public run `31913192879` passed Python 3.11-3.14 at exact commit
`2c2eb36e4f0b0438f1c42030d56f3a872007264d`.

G15 did not consume a KAE replay bundle, launch or control Kenshi, touch saves
or DLLs, prove metric equivalence, retain a real KAE capability, or prove a live
world effect. Goal 16 is the sole next packet and owns the first public KAE
observer/replay proof. G17 and all live/evolved-capability claims remain
unstarted or withheld.
