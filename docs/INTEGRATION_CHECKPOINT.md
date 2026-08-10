# Integration checkpoint: publish the deterministic alpha

This document is the current repository authority for one bounded integration
goal. It is replaced in the same commit as every completed goal; Git history
retains older checkpoints.

## Repository and planning authority

```text
parent commit          88c169d46e3eaf5c0b0cc87f31e05c95ea9356b4
integration branch     main
current goal           Goal 1 - Freeze and publish the alpha honestly
next unstarted goal    Goal 2 - Give subjects a real plugin boundary
plan file              EVOGEN_KENSHI_OPENTTD_BOUNDED_GOALS.md
plan file id           1IcZkzsjmsdtPqxxj4NxSiKWIBzB8In3D
plan updated           2026-08-10T21:25:08.835Z
```

The alpha source baseline is the parent commit above. It was restored from the
complete Git bundle at `C:\Hub\00_Inbox\evogen-main.bundle`; the bundle SHA-256
is `bb4d33ec2cf10fc4db4157f3d5055c259fb4be1c54ba434f48b3f29af1a833ca`.
The extracted workspace matched that commit after excluding its local virtual
environment and Windows download-metadata sidecars.

The independently supplied wheel
`C:\Hub\00_Inbox\evogen-0.1.0-py3-none-any.whl` has SHA-256
`1c7cfd952f1d52a7e9cc6b6527538b5ab6ccb670cc2e9355eaf360a356faa01c`.
Its archive is internally valid and its `evogen` payload matches the baseline
`src/evogen` package byte-for-byte. The wheel is provenance evidence, not a
substitute for fresh-clone verification.

## What the alpha proves

Source-proven:

- strict typed contracts cover generations, causal trajectory events,
  capabilities, issues, specifications, candidates, experiments, and lineage;
- artifacts are content-addressed and lineage is retained in SQLite;
- candidate construction, adversarial review, comparative evaluation, and
  deterministic selection remain separate responsibilities; and
- the demonstration environment is deterministic and generates real Python
  candidate code rather than a success report.

Test-proven by the verification command below:

- all committed schemas match the current public models;
- the complete test suite passes; and
- the microworld baseline fails before the candidate, while the candidate
  reaches 100% revealing, variant, regression, and long-horizon success and is
  retained.

Not proven:

- a general model can diagnose arbitrary real-world capability deficits;
- the current cycle can resume stage-by-stage across processes;
- either Kenshi or OpenTTD is registered as a subject plugin; or
- any generated candidate has changed either game or passed live evaluation.

## Verification

The one local and CI authority is:

```bash
uv run --frozen --extra dev python scripts/verify.py
```

It uses the checked-in lock, compiles the source and tests, runs the full pytest
suite including schema freshness and checkpoint freshness, enforces the narrow
Ruff policy and strict mypy over `src`, executes the complete microworld cycle
in a temporary workspace, and checks whitespace errors.

The supported alpha matrix is CPython 3.11, 3.12, and 3.13. Local verification
passed under CPython 3.11 and 3.12 on 2026-08-10. Hosted matrix completion
remains withheld until the committed workflow is observed after publication.

## External subject availability

Kenshi Agent Environment is a separate subject repository and remains outside
this goal. Its exact integration baseline must be resolved again when Goal 9
starts rather than copied from the planning snapshot.

OpenTTD 15.3 is installed at `C:\Program Files\OpenTTD`. The installed
`openttd.exe` SHA-256 is
`360f615cb74cafcedf0486398a396577e8f1470e0f8158f66b7e29557fdb711d`.
This is availability evidence only: it has not been correlated to the pinned
upstream source commit, configured for headless execution, or accepted as an
OpenTTD subject generation.

## Completion boundary

Goal 1 ends after the locked proof passes from this candidate and a fresh clone,
the checkpoint freshness ratchet passes before and after its commit, the tree is
clean, and the completed commit is tagged as the alpha baseline. Goal 2 remains
unstarted.

`EvolutionOrchestrator.run()` intentionally remains the alpha's synchronous
one-shot composition. Its stage outputs are typed, but individual stages are not
yet independently invokable or resumable and essential orchestration state is
not yet reconstructed from immutable upstream artifacts. Goal 4 owns that
behavioral migration and must preserve this alpha's final lineage result.
