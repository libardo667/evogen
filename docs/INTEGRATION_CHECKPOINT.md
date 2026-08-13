# Integration checkpoint: G13 generated KAE capability authority

This document is the current repository authority for one bounded integration
goal. Git history retains the completed prerequisite-contract checkpoint.

## Repository and planning authority

```text
parent commit                    73a6ab25f5b726f23cba050f4ace1c3d70c83935
integration branch               main
current goal                     Goal 13 - Generate KAE capability manifest
next unstarted goal              Goal 14 - Replace the provisional normalizer with an exact KAE exporter
KAE parent commit                0560b9de6e049f0dc06fab9afbef76f76d198092
KAE completion commit            a8584554e30bb793f5b60ef57e3d1500de5aaa12
KAE-recorded EvoGen counterpart  4270e8332f8a03757b39a306b2e936ac8a618cc3
KAE public remote                https://github.com/libardo667/kenshi-agent-env
KAE hosted run                   31720597916
EvoGen prerequisite commit       4270e8332f8a03757b39a306b2e936ac8a618cc3
EvoGen prerequisite hosted run   31717965263
EvoGen plan ratchet commit       6265c42950fc5cf47eac70d64dc8e9d8ad86ba7a
EvoGen cockpit proof commit      73a6ab25f5b726f23cba050f4ace1c3d70c83935
EvoGen hosted run                31721525900
alpha release commit             9c8d94c59a95222a719e20fac5a61d2ec712743d
source plan revision             2026-08-10T21:25:08.835Z
execution plan                   docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 13 began from clean, synchronized KAE `main` after G12's exact
planner-affordance evidence. EvoGen first published the subject-neutral evidence
contract above. The KAE commit then generated the real subject capability
manifest from existing authorities and recorded that exact EvoGen prerequisite
in its commit message and checkpoint.

The follow-up cockpit refresh changed no numbered-goal state. Commit
`73a6ab25f5b726f23cba050f4ace1c3d70c83935` rendered the already-committed
G13/G14 queue boundary and KAE proof into the checked-in, offline project
interface. Hosted run `31721525900` passed Python 3.11, 3.12, and 3.13. This
final metadata refresh records that proof without advancing into G14.

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

## Withheld claims and completion boundary

The manifest proves a typed inventory and the evidence state KAE can currently
support. It does not prove that an offered operation was selected, dispatched,
accepted, completed, or changed Kenshi. Source and portable proof are not live
proof; even a live evidence reference applies only to its exact retained scope.

Goal 13 is complete at KAE commit
`a8584554e30bb793f5b60ef57e3d1500de5aaa12` once this central plan and cockpit
ratchet are committed, public, and hosted-green. Goal 14 is the sole next packet.
It owns the exact KAE trajectory exporter and serial retirement of EvoGen's
provisional normalizer. G15 subject registration and every later goal remain
unstarted.
