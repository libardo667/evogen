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

## Subject plugins

Subjects are discovered from installed Python distribution metadata in the
`evogen.subjects` entry-point group. The public API version is
`evogen.adapters.subjects.SUBJECT_PLUGIN_API_VERSION` (`"1.0"`). An entry-point
name is the generic subject identity and must match the loaded plugin's
`name`; duplicate names, load failures, unsupported versions, and malformed
factories fail closed with typed `SubjectPluginError` subclasses.

The plugin supplies factories for seven behaviours: `SubjectRunner`,
`EnvironmentInvestigator`, `CandidateBuilder`, `CandidateReviewer`,
`ExperimentEvaluator`, `GenerationMaterializer`, and the minimal
`SubjectDoctor`. It also supplies the separate subject-neutral
`bootstrap_factory`, which returns the initial `GenerationManifest` and
`EvolutionPlan` required for a one-shot run. Every factory receives one
`SubjectFactoryContext` containing the shared workspace, artifact store, and
ledger. The runner is placed on that context before bootstrap, evaluator, and
materializer construction so subject adapters can reuse the exact runner
instance.

The bundled microworld is registered through the same entry-point path as an
external subject. Generated capability files remain a separate runtime plugin
boundary and are not loaded through subject entry points.

## Persisted evolution stages

The generic dispatcher exposes nine individually invokable stages in this exact
order: `ingest`, `distill`, `diagnose`, `investigate`, `specify`, `build`,
`review`, `evaluate`, `select`. Each stage stores a Pydantic-validated output in
the content-addressed artifact store and publishes an immutable receipt and
atomic stage pointer. Reinvoking a completed stage verifies and returns its
stored output. A cycle can resume in a new process only at a completed boundary;
orphan artifacts left by a crash are not completion proof, and arbitrary
instruction-level transactional recovery is intentionally not claimed.

When `clean=True`, recursive deletion is allowed only for a recognized EvoGen
workspace (ledger, artifact store, and workspace evidence) or the explicit
default `.evogen-demo` path. Filesystem roots, home/current directories, Git
repositories, and unmarked directories fail closed with `SubjectWorkspaceError`.
