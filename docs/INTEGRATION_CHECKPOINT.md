# Integration checkpoint: versioned subject plugin boundary

This document is the current repository authority for one bounded integration
goal. It is replaced in the same commit as every completed goal; Git history
retains older checkpoints.

## Repository and planning authority

```text
parent commit          f924dcee37b0a5e67bf667385e132796ce5bf505
integration branch     main
current goal           Goal 2 - Give subjects a real plugin boundary
next unstarted goal    Goal 3 - Fix trajectory identity before importing real logs
alpha source commit    88c169d46e3eaf5c0b0cc87f31e05c95ea9356b4
alpha release commit   9c8d94c59a95222a719e20fac5a61d2ec712743d
alpha tag              v0.1.0
public remote          https://github.com/libardo667/evogen
plan file              EVOGEN_KENSHI_OPENTTD_BOUNDED_GOALS.md
plan file id           1IcZkzsjmsdtPqxxj4NxSiKWIBzB8In3D
plan updated           2026-08-10T21:25:08.835Z
execution plan         docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 2 began from the published planning commit named by `parent commit`. The
alpha remains anchored at the release commit and tag above; this goal changes
subject composition and packaging authority without changing the deterministic
microworld environment, evaluator, candidate, or retention outcome.

## Behavioral change and authority

Source-proven:

- `evogen.adapters.subjects` owns the versioned `SubjectPlugin` 1.0 contract
  and discovers installed subjects only from the `evogen.subjects` Python
  entry-point group;
- the contract preserves the existing runner, investigator, builder, reviewer,
  evaluator, and materializer protocols, adds a minimal doctor protocol, and
  requires a subject-neutral baseline/plan bootstrap factory;
- all factories receive one shared workspace/artifact/ledger context, and the
  evaluator and materializer use the exact runner supplied to the orchestrator;
- missing, duplicate, malformed, failing, mismatched, and incompatible plugins
  fail closed through typed errors, with no built-in registry or import fallback;
- the bundled microworld is registered in installed distribution metadata and
  `evogen demo` reaches it through the same public loader available to a
  separately installed subject;
- generic source contains no microworld imports, while generated capability
  files remain a separate subject-owned runtime boundary; and
- recursive `--clean` refuses roots, home/current directories, repositories,
  files, and unrecognized directories instead of deleting an arbitrary path.

Test-proven:

- all eight factories are exercised for missing/non-callable attributes,
  exceptions, wrong result shapes, shared context, runner identity, malformed
  bootstrap data, and subject mismatch;
- real temporary `.dist-info` metadata proves discovery without monkeypatching
  the metadata API, while no-metadata and duplicate-metadata cases fail closed;
- the generic import-isolation ratchet passes; and
- the microworld still produces exact baseline rates of 0% revealing, 0%
  variant, 100% regression, and 0% long-horizon with five blocked runs, followed
  by 100% candidate success in all four suites, zero blocked runs, and `retain`.

Built and portable evidence:

- setuptools `80.9.0` is exact in both build authority and the locked dev
  environment;
- a fresh CPython 3.12 environment and empty uv cache resolved the frozen lock,
  built the wheel, and verified the exact `evogen.subjects` metadata before the
  expected dirty-checkpoint stop; and
- an independent verifier installed the candidate wheel outside the checkout,
  discovered `microworld`, and reproduced the exact retention result.

Not proven:

- Kenshi or OpenTTD is registered as a subject plugin;
- the minimal doctor factory performs the conformance checks owned by Goal 8;
- the evolution cycle can resume stage-by-stage across processes; or
- any generated candidate has changed either game or passed live evaluation.

## Verification and independent review

The one local and CI authority remains:

```bash
uv run --frozen --extra dev python scripts/verify.py
```

It compiles source and tests, runs Ruff and strict mypy, builds a wheel and
checks its exact entry-point metadata, runs the complete pytest suite including
schema/checkpoint/goal-queue freshness, executes the full microworld cycle in a
temporary workspace, and checks whitespace errors.

Before the checkpoint update, 67 non-checkpoint tests passed. The focused
subject-plugin module contributed 47 tests. Independent verification also
passed the installed-wheel demo outside the checkout. After this checkpoint
advanced the queue to Goal 3, the complete dirty-candidate gate passed with 68
tests, the pinned wheel build and metadata check, exact microworld retention,
and no Ruff, mypy, freshness, or whitespace failure.

Pre-write authority and falsifier design were delegated read-only. A separate
Luna writer produced the candidate without checkpoint or commit authority.
Independent adversarial review rejected its first form for an optional hidden
bootstrap dependency, unsafe generic cleanup, speculative public aliases,
incomplete durable falsifiers, and a warm-cache-only wheel gate. Those findings
were re-delegated, corrected, and independently rechecked. The final adversarial
handback reported no blocking findings. Candidate-author diagnostics were not
used as certification.

## External subject availability

Kenshi Agent Environment remains a separate subject repository. Its exact
integration baseline must be resolved again when Goal 9 starts.

OpenTTD 15.3 remains installed at `C:\Program Files\OpenTTD`. The installed
`openttd.exe` SHA-256 is
`360f615cb74cafcedf0486398a396577e8f1470e0f8158f66b7e29557fdb711d`.
This is availability evidence only: it has not been correlated to the pinned
upstream source, configured for headless execution, or accepted as a subject.

## Completion boundary

This checkpoint is part of the coherent Goal 2 candidate. Goal 2 is complete
only after the authoritative gate passes with this dirty checkpoint, the final
diff is reviewed and committed, the clean-state checkpoint ratchet passes, and
the tree is clean. No Goal 3 implementation has begun.

`EvolutionOrchestrator.run()` intentionally remains the alpha's synchronous
one-shot composition. Goal 2 changes how subject behavior reaches it; Goal 4
still owns persisted, independently invokable, resumable stages.
