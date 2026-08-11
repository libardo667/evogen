# Integration checkpoint: subject conformance and doctor

This document is the current repository authority for one bounded integration
goal. It is replaced in the same commit as every completed goal; Git history
retains older checkpoints.

## Repository and planning authority

```text
parent commit          32b7a3ed114f4dfc837fc819fc2885954a79fc8d
integration branch     main
current goal           Goal 8 - Add subject conformance kit and doctor command
next unstarted goal    Goal 9 - Inventory exact KAE export authorities
alpha source commit    88c169d46e3eaf5c0b0cc87f31e05c95ea9356b4
alpha release commit   9c8d94c59a95222a719e20fac5a61d2ec712743d
alpha tag              v0.1.0
public remote          https://github.com/libardo667/evogen
plan file              EVOGEN_KENSHI_OPENTTD_BOUNDED_GOALS.md
plan file id           1IcZkzsjmsdtPqxxj4NxSiKWIBzB8In3D
plan updated           2026-08-10T21:25:08.835Z
execution plan         docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 8 began from the reviewed, public Goal 7 closure commit shown as the exact
`parent commit`. Goal 9 remains unstarted and no Kenshi repository was edited.

## Behavioral change and authority

Source-proven:

- subject plugin API 1.1 requires one data-only `SubjectConformanceFixture`
  factory and a typed `SubjectDoctor.check()` returning
  `BoundedCollection[SubjectDiagnostic]`; API 1.0 fails closed without a
  compatibility fallback;
- `evogen subject list` reads installed entry-point metadata without loading or
  composing plugins;
- `evogen subject doctor NAME` loads exactly the requested plugin in disposable
  storage by default and never falls back to microworld composition;
- an explicit doctor workspace must be a brand-new path; existing paths,
  repositories, filesystem roots, home/current directories, direct symlinks,
  and ancestor symlinks fail before any write;
- one subject-neutral host runner checks generation manifest authority,
  generation-bound capability manifests, canonical trajectory ordering,
  A/B/A scenario isolation, candidate workspace isolation, symmetric frozen
  evaluation, and retained-generation materialization without stage dispatch;
- typed reports serialize `status`, `passed`, nonempty structured evidence,
  exact failure boundary/code, blocked dependencies, and complete diagnostics;
  missing, unknown, truncated, or nonempty subject diagnostics cannot certify a
  report;
- normal discovery, API, load, factory, bootstrap, composition, workspace, and
  endpoint exceptions use the same typed report shape and nonzero CLI exit;
- runner evidence is independently bound to requested generation/scenario/seed,
  regular in-workspace trace bytes, canonical event identity/order, digest,
  timestamps, and ledger read-back;
- builder, reviewer, evaluator, and materializer are distinct authorities at
  both plugin composition and lower-level orchestration boundaries;
- candidate file inventory and digests are host-recomputed before review and
  rechecked after reviewer, evaluator, and materializer execution;
- evaluation binds the canonical suite expansion, baseline/candidate/review
  identities, ledger records and events, trace bytes, per-run and total timing,
  suite metric namespace, generic metrics, and independently captured pre/post
  suite authority;
- materialization uses the real experiment object and retention policy, verifies
  protected/CAS authority again afterward, validates a typed generation-bound
  child capability manifest, and rejects cycle, stage, decision, generation,
  lineage, or report publication; and
- generic conformance code imports no Kenshi, OpenTTD, microworld, or demo
  ontology and contains no game-specific checks or scenario literals.

Test-proven:

- the bundled microworld passes all seven public conformance boundaries with
  complete-empty diagnostics and structured evidence;
- deliberately broken public plugin specimens fail at each exact boundary:
  coherent wrong-generation capability CAS, post-bootstrap capability
  instability, ignored requested scenario, returned/on-disk isolation
  divergence, candidate mutation, evaluator identity/timing/namespace forgery,
  and protected-authority materializer mutation;
- dependency failures suppress downstream role invocation and report blocked
  boundaries rather than unrelated failures;
- outside/symlink traces, forged ledger generations, candidate siblings,
  post-build mutations, inverted windows, zero elapsed time, total-ceiling
  violations, and symmetric fake subject namespaces fail closed;
- existing evolution workspaces and direct/ancestor symlink paths remain
  byte-identical after doctor refusal;
- unexpected endpoint failures retain typed JSON and human output;
- four-way object, authority-ID, and backend alias tests cover direct lower-level
  orchestrator use; and
- a fresh doctor creates no cycle/stage/lineage pointer or generation/lineage
  ledger authority, while the complete persisted microworld cycle still retains
  the expected candidate.

Generated authority:

- the schema registry and committed schema index include subject conformance
  fixture, check, diagnostic, and report schemas;
- generated schemas require nonempty structured check evidence, typed bounded
  diagnostics, and serialized report status; and
- schema freshness covers every new public model.

Not proven:

- the conformance kit is not an operating-system sandbox; subject code executes
  in the EvoGen process and can inspect ambient process/filesystem state;
- pre/post hashing cannot detect a hostile component that mutates and restores
  authority entirely between snapshots;
- timing violations fail after a role returns; the doctor does not hard-kill a
  hung runner or evaluator subprocess;
- a subject-supplied fixture identifies opaque scenarios and typed builder
  inputs; passing still depends on host-observed behavior and does not prove the
  fixture is representative of every subject behavior;
- no Kenshi or OpenTTD subject is installed, registered, controlled, or
  live-proven by this goal; and
- OpenTTD installation availability remains only the prior host observation,
  not pinned-source or subject-conformance evidence.

## Verification and independent review

The local and CI authority remains:

```bash
uv run --frozen --extra dev python scripts/verify.py
```

Before checkpoint refresh, root verification passed the focused conformance,
subject-plugin, CLI, schema, probe, and four-way policy suites; repository-wide
Ruff; strict mypy over 47 source files; schema freshness; doctor JSON/human
smokes; the retained microworld demo; and whitespace checks. The complete suite
had only the expected checkpoint-freshness failure.

Faraday audited plugin API migration, error taxonomy, scratch safety, public
specimens, authority separation, docs, and genericity. Nightingale attacked
trace identity, A/B/A isolation, evaluator/ledger binding, timing, namespaces,
authority snapshots, materialization, CLI output, and workspace symlinks. Both
initially rejected the candidate with reproducible passing forgeries; Franklin
repaired them on the Luna model. After root added full pre/post suite identity
and authority-window validation, Faraday and Nightingale independently returned
final PASS verdicts. Candidate-author diagnostics were not used as
certification.

The first sandboxed authoritative-gate attempt reached the isolated wheel build
and failed DNS resolution for pinned `setuptools==80.9.0`. The authorized rerun
resolved that dependency and passed compile, Ruff, strict mypy, fresh wheel
build and entry-point inspection, the entire checkpoint-fresh suite, the
retained microworld demo, and whitespace checks.

## Completion boundary

This checkpoint is part of the Goal 8 closure candidate. Goal 8 is complete only
after the authoritative dirty-candidate gate passes with this checkpoint, the
final diff is committed, the clean-state checkpoint ratchet passes, the tree is
clean and synchronized with the public remote, and the hosted Python 3.11, 3.12,
and 3.13 matrix is green.

Goal 9 is the sole next packet and remains unstarted. No KAE inventory or source
change may be smuggled into this conformance commit.
