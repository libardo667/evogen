from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from evogen.core.ids import new_id
from evogen.core.models import RoleRequest, RoleResponse


class RoleBackend(Protocol):
    """A role-isolated agent accepts one JSON packet and returns one typed result."""

    def run(self, request: RoleRequest) -> RoleResponse: ...


class JsonStdioRoleBackend:
    """Invoke an external coding-agent wrapper through JSON over stdin/stdout.

    The command is passed without a shell. The wrapper receives a serialized
    RoleRequest on stdin and must emit exactly one RoleResponse-compatible JSON
    object on stdout. EvoGen records stderr in the failure rather than treating
    prose as a successful result.
    """

    def __init__(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout_seconds: float = 600.0,
        environment: dict[str, str] | None = None,
    ) -> None:
        if not command:
            raise ValueError("Agent command cannot be empty")
        self.command = tuple(command)
        self.cwd = cwd
        self.timeout_seconds = timeout_seconds
        self.environment = environment or {}

    def run(self, request: RoleRequest) -> RoleResponse:
        env = os.environ.copy()
        env.update(self.environment)
        completed = subprocess.run(
            self.command,
            input=request.model_dump_json(),
            text=True,
            capture_output=True,
            cwd=self.cwd,
            env=env,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            return RoleResponse(
                response_id=new_id("role-response"),
                request_id=request.request_id,
                role=request.role,
                success=False,
                output={
                    "returncode": completed.returncode,
                    "stderr": completed.stderr[-8000:],
                },
                notes=["External role backend returned a non-zero exit code."],
            )
        try:
            raw = json.loads(completed.stdout)
            response = RoleResponse.model_validate(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            return RoleResponse(
                response_id=new_id("role-response"),
                request_id=request.request_id,
                role=request.role,
                success=False,
                output={
                    "stdout": completed.stdout[-8000:],
                    "stderr": completed.stderr[-8000:],
                },
                notes=[f"External backend violated the output contract: {exc}"],
            )
        if response.request_id != request.request_id or response.role != request.role:
            return RoleResponse(
                response_id=new_id("role-response"),
                request_id=request.request_id,
                role=request.role,
                success=False,
                output=response.model_dump(mode="json"),
                notes=["External backend returned a response for a different request or role."],
            )
        return response
