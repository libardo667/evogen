# Integration checkpoint: frozen evaluation authority

This document is the current repository authority for one bounded integration
goal. It is replaced in the same commit as every completed goal; Git history
retains older checkpoints.

## Repository and planning authority

```text
parent commit          0a89273fc86ec5f2e494cb7c91da08d2cf7e4682
integration branch     main
current goal           Goal 7 - Freeze evaluation authority outside candidates
next unstarted goal    Goal 8 - Add subject conformance kit and doctor command
alpha source commit    88c169d46e3eaf5c0b0cc87f31e05c95ea9356b4
alpha release commit   9c8d94c59a95222a719e20fac5a61d2ec712743d
alpha tag              v0.1.0
public remote          https://github.com/libardo667/evogen
plan file              EVOGEN_KENSHI_OPENTTD_BOUNDED_GOALS.md
plan file id           1IcZkzsjmsdtPqxxj4NxSiKWIBzB8In3D
plan updated           2026-08-10T21:25:08.835Z
execution plan         docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 7 source work began from reviewed Goal 6 commit
`8869cb056ac4c182978b963dfc6be0937521b6d8`. The first public G07 candidate is
the immediate `parent commit`; hosted Python 3.13 then exposed a read-only WAL
visibility defect, so this final closure commit retains that red candidate and
corrects the portability boundary rather than rewriting history.

## Behavioral change and authority

Source-proven:

- `EvaluationSuiteManifest` is the typed authority for revealing cases,
  structural variants, regressions, long-horizon suites, seeds, repeat counts,
  per-run and total wall-clock ceilings, evaluator version and artifact,
  environment artifacts, protected-path hashes, and one subject metric
  namespace;
- suite case categories and identifiers are unique and plan-aligned, seeds are
  nonempty and unique, limits are finite and positive, the evaluator digest is
  bound to its named protected path, and candidate tests are structurally fixed
  as nonauthoritative;
- subject bootstrap supplies the suite through the generic plugin boundary;
  `CycleManifest` version 1.1 binds its content-addressed reference and rejects
  a changed suite on resume;
- subject evaluators return only `EvaluationOutcome`; the root constructs the
  final `ExperimentResult` with the canonical suite reference and required pre-
  and post-execution authority snapshots;
- both authority snapshots verify every frozen CAS object and independently
  hash each protected evaluator, scenario, environment, and subject source;
  missing, corrupt, unreadable, symlinked, non-regular, or changed authority
  fails closed even when evaluation itself raises;
- the root requires the exact manifest-expanded coordinate order for baseline
  and candidate runs, unique run IDs, the correct generation, scenario,
  category, seed, outcome, counts, termination, trace digest, and canonical
  trace bytes from the ledger;
- run and experiment timestamps must be monotonic, every run must lie inside
  both the experiment and authority windows, total and per-run ceilings are
  independently checked, and reported elapsed time must agree with persisted
  run duration within a documented 50 ms clock-read tolerance;
- generic retention metrics are recomputed from canonical scenario results;
  namespaced subject metrics remain additional evidence and cannot override
  deterministic retention rules;
- the complete candidate workspace inventory is required, root-recomputed,
  content-hashed, statically reviewed, and checked again after evaluation, so
  undeclared or runtime-created files cannot escape review; and
- validation occurs before experiment publication, candidate lifecycle
  advancement, stage pointers, decisions, lineage, or cycle-result publication;
  and
- ledger context managers now explicitly close after commit or rollback, so a
  writer finalizes WAL state before immutable status and replay inspection;
  read-only commands still create or change no workspace bytes.

Test-proven:

- an unchanged evaluation retains matching canonical pre/post hashes, the
  frozen suite reference, namespaced metrics, and seven baseline plus seven
  candidate results;
- real generated candidate plugins that edit either the held-out evaluator or
  held-out scenarios still complete seven successful candidate runs, but are
  rejected before experiment, pointer, decision, lineage, or cycle-result
  publication and remain only reviewed candidates;
- missing, wrong-seed, reordered, reused-run, inflated-metric,
  inflated-elapsed, stale-time, and inner-time result forgeries fail closed;
- a runtime-created candidate file and runtime evaluator-CAS corruption are
  rejected before experiment publication;
- completed evaluation replay rejects protected-source drift and missing or
  corrupt suite CAS objects;
- mismatched evaluator-to-path binding, invalid case categories, duplicate
  cases, empty seeds, invalid ceilings, and authoritative candidate-test claims
  are rejected by typed construction; and
- a candidate subject metric claiming its own tests passed cannot override a
  generic regression failure, which remains a deterministic rejection; and
- a deterministic WAL fixture proves the ledger context closes its connection,
  finalizes the committed record, and makes it visible to immutable read-only
  replay without creating sidecar files.

Generated authority:

- the registry and committed schema index now include evaluation case, suite,
  outcome, authority snapshot, protected-path hash, scenario result, and
  subject metric schemas;
- final experiment schemas require suite identity, both authority snapshots,
  both subject metric vectors, and complete scenario coordinates; and
- candidate and cycle schemas require the complete workspace digest inventory
  and evaluation suite reference respectively, with schema freshness enforced.

Not proven:

- generated candidate Python still executes in the EvoGen process; the suite is
  not passed to the builder or capability API, but this goal does not establish
  an operating-system sandbox against ambient module or filesystem inspection;
- a hostile component that changes and restores protected source or CAS bytes
  entirely between the two snapshots is outside this goal; process isolation or
  an external monitor is required to close that interval;
- wall-clock overruns are rejected after a run returns; this goal does not add a
  hard-kill subprocess deadline for a hung subject runner;
- a fully coherent rewrite of SQLite, every replacement CAS object, and local
  anchors still requires an external signed anchor to detect; or
- OpenTTD or Kenshi is registered, controlled, installed from pinned source, or
  live-proven as an EvoGen subject.

## Verification and independent review

The local and CI authority remains:

```bash
uv run --frozen --extra dev python scripts/verify.py
```

Before checkpoint refresh, the root passed the 20 focused G07 adversarial tests,
broader subject-plugin, persistence, selection, external-role, policy, and
schema suites, repository-wide Ruff, strict mypy over 46 source files, schema
freshness, and whitespace checks. The complete 223-test suite had only the
expected checkpoint-freshness failure. With this checkpoint present, the
authoritative dirty-candidate gate passed compile, Ruff, strict
mypy, a fresh isolated wheel build, the entire test suite, the retained
microworld demo, and whitespace checks.

After the ledger lifecycle correction, the same authoritative gate passed
uncontended under Python 3.13 with all 224 tests, the retained microworld demo,
and the source, typing, build, and whitespace checks.

Hosted run `31518315356` passed Python 3.11 and 3.12 but failed Python 3.13
because immutable read-only SQLite replay ignored one committed evaluation run
still present in the WAL. The failed run and public parent commit remain
evidence. This closure candidate explicitly closes ledger context connections
so writers finalize committed WAL state, while preserving side-effect-free
immutable reads; its replacement hosted run must be green before Goal 7 is
complete.

Gauss and Hopper mapped evaluator authority and attack surfaces before writing.
Tesla implemented the bounded candidate on the Luna model. The root rejected
the first handback after Lovelace and Shannon found incomplete workspace
coverage, weak result authority, unbound run evidence, path-identity gaps, and
missing positive proofs. After repair, Shannon found elapsed and timestamp
forgeries, Lovelace found runtime CAS and optional-workspace-contract gaps, and
Curie found two stale compatibility aliases. The root corrected each finding
with negative proofs. Lovelace, Shannon, and Curie then returned independent
final `PASS` verdicts. Candidate-author diagnostics were not used as
certification.

## External subject availability

Kenshi Agent Environment remains a separate subject repository. Its exact
integration baseline must be resolved again when Goal 9 starts.

OpenTTD 15.3 remains installed at `C:\Program Files\OpenTTD`. The installed
`openttd.exe` SHA-256 is
`360f615cb74cafcedf0486398a396577e8f1470e0f8158f66b7e29557fdb711d`.
This is availability evidence only: it has not been correlated to pinned
upstream source or base assets, configured for headless execution, or accepted
as a subject.

## Completion boundary

This checkpoint is part of the final Goal 7 closure candidate. Goal 7 is complete
only after the authoritative gate passes with this dirty checkpoint, the final
diff is reviewed and committed, the clean-state checkpoint ratchet passes, and
the tree is clean and synchronized with the public remote.

Goal 8 is the sole next packet and remains unstarted. Subject-conformance-kit or
doctor-command implementation must not be smuggled into this evaluation-
authority commit.
