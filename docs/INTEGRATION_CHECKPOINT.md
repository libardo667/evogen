# Integration checkpoint: G12 exact planner affordance evidence

This document is the current repository authority for one bounded integration
goal. It is replaced in the same commit as every completed goal; Git history
retains older checkpoints.

## Repository and planning authority

```text
parent commit                    643ca51b04d8c8e21d5a1478e6fa6542f3b9e36a
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

Goal 12 began from clean, synchronized KAE `main` after G11's exact generation
manifest. This EvoGen candidate changes only the durable planning ratchet;
implementation and primary evidence live in the exact KAE completion commit.

The subsequent cockpit repair changes no numbered-goal state. The first public
ratchet run `31703681557` correctly rejected the stale G11/G12 cockpit snapshot
after the plan advanced to G13. Commit
`643ca51b04d8c8e21d5a1478e6fa6542f3b9e36a` refreshed that generated UI and
its assertions from the already-published ratchet authority; hosted run
`31704114352` then passed Python 3.11–3.13. This final metadata refresh records
that proof without changing the plan queue.

## Behavioral change and authority

Source-proven in KAE:

- `enumerate_affordance_set` produces one immutable offer snapshot used by the
  hosted planner payload, the dedicated evidence event, and the read-only watch
  surface;
- hosted planners enumerate once before budgeting and reuse that snapshot;
- the complete planner `affordances` array must equal the projection from the
  same snapshot or planner preparation fails closed;
- `planner_context_prepared` remains delivery accounting, while
  `affordance_set` is written after it as the final durable record before
  `decide_prepared` receives the context;
- a failed event write prevents an unrecorded planner delivery, and a provider
  failure leaves the exact delivered menu in the log;
- direct-action and scripted planners record every source as `not_delivered`
  because they do not consume the hosted semantic menu; and
- the event disposition generator now inventories 90 event types and 128
  producer records, with `affordance_set` mapped exactly to EvoGen's event kind.

Each typed event records its context and authored world revision, optional
identity session, opaque offer identity, operation kind, source adapter,
semantic name, typed parameter constraints, required opaque selection target,
applicable engine-owned target identities, per-source completeness, and the
canonical union of withholding categories.

## Missing evidence and semantic/mechanical separation

Missing telemetry, stale telemetry, unknown sources, truncated sources,
unprobed targets, invalid semantic values, authoring refusal, binding refusal,
interface scope, and intentional non-delivery remain distinct. A fresh complete
source with zero offers is represented differently from every unavailable or
incomplete source. Contradictory statuses, unsorted or duplicate identities,
malformed parameter contracts, and incomplete source inventories fail closed.

The evidence event contains no presentation labels, descriptions, executor
arguments, keys, screen coordinates, inventory sections or slots, or inventories
of unoffered native commands. Inventory transfers now expose one opaque semantic
selection target plus role-tagged source/destination owner identities. Their
private section and slot address remains only in runtime binding arguments.

This separation does not weaken execution. Selection and later execution still
re-enumerate current adapter authority and bind against fresh world evidence;
the recorded event is provenance of what was delivered, never durable permission
to dispatch.

## Replay proof

The checked-in `affordance_set` schema and JSONL fixture are parsed through the
strict typed event model. `load_affordance_sets` requires the exact registered
adapter inventory and validates every adapter/operation pair. It refuses old
logs with no typed event rather than inferring a menu from prompts, descriptions,
or the retired summary fields in `planner_context_prepared`.

`reconstruct_choice` resolves semantic, target, and parameter constraints from
the event and can cross-check the retained opaque affordance ID, operation kind,
and source adapter. Tests mutate all of those authorities, malformed bounds and
choices, completeness coherence, and forged source/operation pairs.

## Independent review and verification

Cicero mapped enumeration, delivery, generated, and replay authority. Kuhn
designed adversarial falsifiers and found permissive parameter/completeness and
replay-identity contracts. Hypatia independently found the forged
adapter/operation boundary. Root repaired those findings; Kuhn and Hypatia then
retested the exact repairs read-only and returned PASS.

Cicero also identified that the generated reporting-surface report still shows
zero `affordance_set` events in its real pre-G12 live fixture. That gap is kept
visible. The new synthetic fixture proves typed replay mechanics but is not
inserted into historical live evidence or presented as a live run.

KAE's final candidate passed Ruff, strict mypy over 153 source files, generated
event/schema/document freshness, research evidence, architecture and whitespace
checks, the full pytest suite, and `./dev verify-portable`. The exact public KAE
completion commit passed hosted run
`https://github.com/libardo667/kenshi-agent-env/actions/runs/31703301693` on
Python 3.11, 3.12, 3.13, and 3.14.

This EvoGen ratchet is verified with the repository's current complete command:

```bash
UV_CACHE_DIR=/tmp/evogen-uv-cache \
  uv run --frozen --extra dev python scripts/verify.py
```

Hosted EvoGen CI remains the post-push completion authority.

## Withheld claims and completion boundary

An affordance event proves only what semantic choices were delivered. It does
not prove that the planner selected one, that dispatch was accepted, that an
operation completed, that the game advanced, or that Kenshi changed. Those
claims still require their independent later evidence.

Source completeness describes the adapter's declared observed denominator, not
every possible action in Kenshi. Old logs remain valid historical records but
cannot claim exact offer reconstruction. The runtime plane and EvoGen evolution
plane remain separate. No game process, save, DLL, native protocol, operation
definition, environment, or evaluator changed in G12.

Goal 12 is complete at KAE commit
`0560b9de6e049f0dc06fab9afbef76f76d198092`. This planning-ratchet candidate is
complete only after EvoGen verification, commit, clean checkpoint mode, public
push, and hosted Python matrix are green.

Goal 13 is the sole next packet and remains unstarted here. It owns a generated
KAE `CapabilityManifest` derived from existing registries, protocol/schema
versions, and proof authorities with no hand-maintained sibling list. G14 still
owns production trajectory export, and G15 still owns subject registration.
