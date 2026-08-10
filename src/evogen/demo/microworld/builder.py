from __future__ import annotations

from pathlib import Path

from evogen.core.ids import new_id, sha256_bytes, stable_digest
from evogen.core.models import (
    CandidateManifest,
    CapabilityIssue,
    CapabilitySpec,
    GenerationManifest,
)

_INSPECT_CONTAINER_PLUGIN = '''from __future__ import annotations

from evogen.core.enums import ProofClass
from evogen.core.models import CapabilityDefinition
from evogen.demo.microworld.models import ActionChoice, ActionOffer, ActionResult, WorldSnapshot


class InspectContainerCapability:
    name = "inspect_container"

    def definition(self, generation_id: str) -> CapabilityDefinition:
        return CapabilityDefinition(
            name=self.name,
            purpose=(
                "Inspect an exact opaque container so a later authoritative observation can "
                "reveal its contents."
            ),
            kind="action",
            semantic_effects=["reveal_contents"],
            owner_component="candidate capability plugin",
            input_schema={"container_id": "string"},
            output_schema={"container_id": "string", "inspected": "boolean"},
            applicability=(
                "A container is offered only when it is present, opaque, and not yet inspected."
            ),
            completion_evidence=[
                "A later snapshot marks the exact container inspected and exposes its contents."
            ],
            implementation_ref="plugin:inspect_container.py",
            proof_class=ProofClass.PORTABLE,
            introduced_generation=generation_id,
            limitations=["Only containers in the active room are eligible."],
        )

    def offers(self, snapshot: WorldSnapshot) -> list[ActionOffer]:
        return [
            ActionOffer(
                action=self.name,
                target_id=container.container_id,
                arguments={"expected_revision": snapshot.revision},
                description=f"Inspect opaque container {container.name}.",
            )
            for container in sorted(
                snapshot.visible_containers,
                key=lambda value: value.container_id,
            )
            if container.opaque and not container.inspected
        ]

    def execute(self, world, choice: ActionChoice) -> ActionResult:
        return world.inspect_container(choice.target_id)


def build_plugin() -> InspectContainerCapability:
    return InspectContainerCapability()
'''


class ReferenceMicroworldBuilder:
    """Deterministic stand-in for the implementer role in the offline proof.

    This class writes real candidate code in an isolated directory. It is
    intentionally narrow: unsupported specifications fail closed. Replace it
    with JsonStdioRoleBackend or a project-specific coding-agent adapter for
    open-ended implementation.
    """

    def build(
        self,
        *,
        parent: GenerationManifest,
        issue: CapabilityIssue,
        specification: CapabilitySpec,
        candidate_root: Path,
    ) -> CandidateManifest:
        if specification.capability_name != "inspect_container":
            raise ValueError(
                "Reference builder only knows the proof capability inspect_container; "
                f"received {specification.capability_name!r}"
            )
        candidate_id = new_id("candidate")
        workspace = candidate_root / candidate_id
        plugins = workspace / "plugins"
        plugins.mkdir(parents=True, exist_ok=False)
        plugin_path = plugins / "inspect_container.py"
        plugin_path.write_text(_INSPECT_CONTAINER_PLUGIN, encoding="utf-8")
        source = plugin_path.read_bytes()
        source_digest = sha256_bytes(source)
        spec_digest = stable_digest(specification.model_dump(mode="json"))
        issue_digest = stable_digest(issue.model_dump(mode="json"))
        return CandidateManifest(
            candidate_id=candidate_id,
            parent_generation=parent.generation_id,
            issue_id=issue.issue_id,
            spec_id=specification.spec_id,
            workspace_path=str(workspace),
            source_digest=source_digest,
            artifact_digests={
                "plugin": source_digest,
                "specification": spec_digest,
                "issue": issue_digest,
            },
            changed_files=["plugins/inspect_container.py"],
            claimed_capabilities=["inspect_container"],
            metadata={
                "builder": "ReferenceMicroworldBuilder",
                "implementation_mode": "deterministic_reference",
            },
        )
