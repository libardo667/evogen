# Adapter contracts

The protocols under `evogen.adapters` are deliberately small. Domain-rich
objects should remain in subject-specific packages and be converted at the
boundary.

## SubjectRunner

```python
class SubjectRunner(Protocol):
    def run(
        self,
        *,
        generation: GenerationManifest,
        scenario_id: str,
        trace_directory: Path,
    ) -> tuple[RunRecord, list[TrajectoryEvent]]: ...

    def capability_manifest(
        self,
        generation: GenerationManifest,
    ) -> CapabilityManifest: ...
```

A runner must create a fresh or explicitly restored scenario. It must not mutate
the evaluator, scenario definition, or parent generation while testing a
candidate.

## EnvironmentInvestigator

```python
class EnvironmentInvestigator(Protocol):
    def investigate(self, issue: CapabilityIssue) -> InvestigationReport: ...
```

An investigator can inspect source, APIs, binaries, documentation, or run a
bounded probe. Its report separates candidate operations, rejected operations,
and remaining unknowns. It should not invent an operation because a feature would
be convenient.

## CandidateBuilder

```python
class CandidateBuilder(Protocol):
    def build(
        self,
        *,
        parent: GenerationManifest,
        issue: CapabilityIssue,
        specification: CapabilitySpec,
        candidate_root: Path,
    ) -> CandidateManifest: ...
```

The builder receives a frozen specification. Broadening that specification
requires a new artifact rather than an undocumented coding-agent decision.

## ExperimentEvaluator

```python
class ExperimentEvaluator(Protocol):
    def evaluate(
        self,
        *,
        baseline: GenerationManifest,
        candidate: CandidateManifest,
        trace_directory: Path,
        review_passed: bool,
    ) -> ExperimentResult: ...
```

The evaluator reruns the unchanged baseline and the candidate under the same
scenario definitions. It returns individual results plus a metric vector.

## External agent backend

`JsonStdioRoleBackend` launches a configured executable without a shell. The
process receives a `RoleRequest` JSON object on stdin and must emit one
`RoleResponse` JSON object on stdout.

This boundary intentionally does not prescribe OpenAI, Anthropic, Codex, Claude
Code, or another provider. A wrapper can manage authentication and provider
semantics while EvoGen retains the typed request, response, artifact references,
and timeout.

A backend process should never receive deployment credentials merely because it
is allowed to author code.
