# AGENTS.md

## Purpose

EvoGen turns agent trajectories into evidence-backed capability changes. Preserve
that causal chain. A convenient patch that cannot say what evidence motivated it,
what behavior it predicts, and how it will be falsified is not an EvoGen change.

## Current completion state

The repository contains a complete deterministic microworld cycle:

- an impoverished baseline agent;
- repeated failure traces;
- generic distillation and conservative diagnosis;
- environment investigation;
- capability specification;
- real generated plugin code;
- static adversarial review;
- baseline/candidate comparison across revealing, variant, regression, and
  long-horizon suites; and
- retained lineage in SQLite plus content-addressed artifacts.

Do not replace this with a mock that merely reports success.

## Invariants

1. Dispatch is not proof of a world effect. Completion requires later independent
   evidence.
2. Missing, truncated, and unknown observations must not be collapsed into empty.
3. The runtime plane and evolution plane remain separate.
4. Candidate authors do not certify their own work.
5. Retention never depends only on the revealing case.
6. The environment and evaluator must not be changed to make a candidate pass.
7. Rejected candidates and failed experiments remain evidence.
8. Generic core code must not import Kenshi or microworld domain objects.
9. New model-backed roles must preserve a deterministic typed output contract.
10. Scenario identifiers, target names, and expected answers are forbidden from
    generated capability implementations.

## Verification

```bash
uv run --frozen --extra dev python scripts/verify.py
```

## Near-term priorities

1. Add a real subject-adapter package for Kenshi Agent Environment without moving
   KAE-specific ontology into EvoGen core.
2. Turn historical KAE fixes into hidden-answer diagnostic cases.
3. Add external role transcripts and artifact references to the ledger.
4. Add probe candidates as a first-class lifecycle distinct from permanent
   capabilities.
5. Compare human diagnoses with model-generated diagnoses before permitting
   sandbox implementation.
