# Integration checkpoint: typed external reasoning roles

This document is the current repository authority for one bounded integration
goal. It is replaced in the same commit as every completed goal; Git history
retains older checkpoints.

## Repository and planning authority

```text
parent commit          dae87edbeb8ca67f20c08a2302171cdcc48c04ce
integration branch     main
current goal           Goal 6 - Add typed external reasoning roles
next unstarted goal    Goal 7 - Freeze evaluation authority outside candidates
alpha source commit    88c169d46e3eaf5c0b0cc87f31e05c95ea9356b4
alpha release commit   9c8d94c59a95222a719e20fac5a61d2ec712743d
alpha tag              v0.1.0
public remote          https://github.com/libardo667/evogen
plan file              EVOGEN_KENSHI_OPENTTD_BOUNDED_GOALS.md
plan file id           1IcZkzsjmsdtPqxxj4NxSiKWIBzB8In3D
plan updated           2026-08-10T21:25:08.835Z
execution plan         docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md
```

Goal 6 began from the reviewed Goal 5 commit named by `parent commit`. This
goal makes six reasoning stages externally replaceable through one retained
typed boundary without changing the deterministic microworld result, subject
ontology, evaluator inputs, or retention policy.

## Behavioral change and authority

Source-proven:

- one generic `RoleInvoker` owns request dispatch, strict typed result
  validation, content-addressed request/response/stream/output/transcript
  retention, and append-only ledger publication for every external role;
- the raw backend contract returns `RawRoleExecution`; the retained executor
  independently normalizes response identity, role, success, process status,
  timeout, and backend-protocol failures before any result can reach a stage;
- the JSON-stdio backend is shell-free, uses an explicit environment rather
  than ambient secrets, defaults to a fresh empty working directory, preserves
  exact stdout/stderr bytes, enforces a finite timeout, and rejects malformed,
  trailing, extra-field, nonzero, mismatched, and unsuccessful envelopes;
- `RoleRequest` and `RoleResponse` accept recursively validated JSON values;
  prose may be retained as notes or stream bytes but cannot substitute for the
  exact Pydantic output model named by the request contract;
- trace analysis, diagnosis, investigation, capability architecture,
  adversarial review, and release recommendation have subject-neutral adapters
  over the same executor; deterministic implementations remain the defaults;
- implementer candidate construction now uses the same retained executor and a
  self-contained JSON packet, with no legacy direct-backend or unretained
  fallback and no child-visible mutable workspace path;
- ledger schema version 2 stores immutable role invocation records and links
  provider, model, backend class, declared authority, timeout, process status,
  outcome, failure, request/response/stream/transcript/output references, and
  input, contract, output, and record digests;
- ledger replay re-reads every referenced CAS object, validates typed request,
  response, transcript, and output models, recomputes digests, checks SQL
  identity columns, and requires the transcript to mirror the invocation;
- DISTILL replay validates the retained result against persisted event and
  capability evidence without redispatching the external analyst;
- builder, reviewer, and evaluator must be distinct objects and may not share
  an exposed authority ID or external backend object;
- an external release recommendation must preserve the deterministic policy's
  exact ordered rule evidence, cannot name a generation, and cannot be more
  permissive than deterministic reject or revise; and
- the microworld review authority forbids every diagnostic, revealing,
  structural-variant, regression, and long-horizon scenario ID and every
  corresponding target ID from generated capability source.

Test-proven:

- all six new reasoning adapters use the retained executor and reopen as six
  verified ledger invocations with typed outputs;
- byte-identical completed-INGEST workspace clones produce the same deterministic
  and externally supplied DISTILL artifact while changing only the trace
  authority; the external clone records exactly one backend call and one role
  ledger row, and completed-stage replay makes no second call;
- malformed external trace output retains an `INVALID_TYPED_OUTPUT` invocation
  and publishes no DISTILL pointer;
- plain prose, trailing prose, missing/extra envelope fields, request and role
  mismatch, `success=false`, malformed typed output, nonzero exit, timeout with
  partial streams, startup failure, generic-backend exception, wrong raw return
  type, and inconsistent generic response claims all fail closed and remain
  ledger evidence;
- a real ambient sentinel does not cross the default JSON-stdio environment
  boundary;
- version-1 ledger migration preserves invocation JSON and backfills its record
  digest; byte-identical duplicate insertion is idempotent while divergent
  reuse of an invocation ID is rejected;
- SQL identity, record JSON/digest, request, response, transcript, and typed
  output substitution or content/model mismatch is detected during replay;
- malicious release recommendations cannot loosen reject/revise, reorder,
  duplicate, add, or remove policy rules, change candidate identity, or forge a
  retained generation; and
- authority tests reject shared objects, authority IDs, invokers, and backend
  objects across permanent build, review, and evaluation.

Generated authority:

- the schema registry and committed index now own role invocation, role
  transcript, and adversarial review report schemas in addition to the strict
  role request and response schemas; and
- generated schema freshness remains enforced from the Pydantic model registry.

Not proven:

- no hosted model or provider was called; external-role proof uses deterministic
  in-process specimens and isolated Python JSON-stdio subprocesses;
- only trace analysis has the full completed-microworld one-role swap proof;
  the other five adapters have typed injection and retained-ledger proof but not
  five additional end-to-end cycle clones;
- a fully coherent rewrite of both SQLite records and every replacement CAS
  object cannot be detected without an external signed anchor; partial or
  inconsistent tampering is detected;
- evaluator/scenario suite manifests, protected pre/post hashes, namespaced
  subject metrics, and held-out evaluation authority remain Goal 7 work; or
- OpenTTD or Kenshi is registered, controlled, installed from pinned source, or
  live-proven as an EvoGen subject.

## Verification and independent review

The local and CI authority remains:

```bash
uv run --frozen --extra dev python scripts/verify.py
```

Before checkpoint refresh, the root passed 32 focused role, policy, ledger,
builder, and schema tests, together with repository-wide Ruff, strict mypy over
46 source files, schema freshness, whitespace checks, and the full test suite
with only the expected checkpoint-freshness failure. With this checkpoint
present, the authoritative dirty-candidate gate passed compile, Ruff, strict
mypy, a fresh isolated wheel build, the entire test suite, the retained
microworld demo, and whitespace checks.

Two Luna agents mapped the pre-write role authority and failure-retention
boundaries. A separate Luna writer implemented the bounded candidate; the root
rejected its first handback after two independent audits found unretained
fallbacks, timeout and identity gaps, weak replay checks, and release-policy
bypass. The corrected handback was reconciled by the root. Kepler then added
the real one-role microworld swap proof and exposed duplicate external
redispatch during replay. Noether and Turing independently authored adversarial
ledger and policy proofs, which the root tightened against false-positive
exception paths. Curie and Faraday performed fresh final read-only audits;
Faraday found incomplete hidden-target protection, the root corrected it with
a regression, and both final reviewers returned `PASS`. Candidate-author
diagnostics were not used as certification.

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

This checkpoint is part of the coherent Goal 6 candidate. Goal 6 is complete
only after the authoritative gate passes with this dirty checkpoint, the final
diff is reviewed and committed, the clean-state checkpoint ratchet passes, and
the tree is clean and synchronized with the public remote.

Goal 7 is the sole next packet and remains unstarted. Frozen evaluation-authority
or suite-manifest implementation must not be smuggled into this role-boundary
commit.
