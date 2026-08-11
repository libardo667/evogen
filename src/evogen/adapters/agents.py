from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from evogen.core.enums import RoleOutcome
from evogen.core.ids import new_id, stable_digest
from evogen.core.models import (
    ArtifactRef,
    RoleInvocation,
    RoleRequest,
    RoleResponse,
    RoleTranscript,
)
from evogen.storage.artifacts import ArtifactStore
from evogen.storage.ledger import Ledger


@dataclass(frozen=True)
class RawRoleExecution:
    response: RoleResponse | None
    stdout: bytes | None
    stderr: bytes | None
    process_status: int | None
    outcome: RoleOutcome
    failure: str | None = None


class RoleBackend(Protocol):
    """Raw role execution boundary; no backend may return an unretained result."""

    timeout_seconds: float

    def execute(self, request: RoleRequest) -> RawRoleExecution: ...


class JsonStdioRoleBackend(RoleBackend):
    """Shell-free JSON-stdio backend with no ambient environment inheritance."""

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
        if not isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive and finite")
        self.environment = dict(environment or {})

    def execute(self, request: RoleRequest) -> RawRoleExecution:
        payload = request.model_dump_json().encode("utf-8")
        try:
            with TemporaryDirectory(prefix="evogen-role-") as empty:
                completed = subprocess.run(
                    self.command,
                    input=payload,
                    capture_output=True,
                    cwd=self.cwd if self.cwd is not None else empty,
                    env=self.environment,
                    timeout=self.timeout_seconds,
                    check=False,
                    shell=False,
                )
        except subprocess.TimeoutExpired as exc:
            stdout = _as_bytes(exc.stdout)
            stderr = _as_bytes(exc.stderr)
            return RawRoleExecution(
                response=None,
                stdout=stdout,
                stderr=stderr,
                process_status=None,
                outcome=RoleOutcome.TIMEOUT,
                failure=f"External role backend timed out after {self.timeout_seconds:g}s",
            )
        except OSError as exc:
            return RawRoleExecution(
                response=None,
                stdout=None,
                stderr=None,
                process_status=None,
                outcome=RoleOutcome.BACKEND_EXCEPTION,
                failure=f"External role backend could not start: {exc}",
            )

        stdout = bytes(completed.stdout)
        stderr = bytes(completed.stderr)
        parsed_response: RoleResponse | None = None
        parse_failure: str | None = None
        try:
            decoded: Any = json.loads(stdout.decode("utf-8"))
            parsed_response = RoleResponse.model_validate(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            parse_failure = f"External backend violated the RoleResponse envelope: {exc}"
        if completed.returncode != 0:
            return RawRoleExecution(
                response=parsed_response,
                stdout=stdout,
                stderr=stderr,
                process_status=completed.returncode,
                outcome=RoleOutcome.NONZERO_EXIT,
                failure=f"External role backend exited with status {completed.returncode}"
                if parsed_response is not None
                else parse_failure
                or f"External role backend exited with status {completed.returncode}",
            )
        if parsed_response is None:
            return RawRoleExecution(
                response=None,
                stdout=stdout,
                stderr=stderr,
                process_status=completed.returncode,
                outcome=RoleOutcome.MALFORMED_ENVELOPE,
                failure=parse_failure or "External backend emitted no RoleResponse envelope",
            )
        response = parsed_response
        if response.request_id != request.request_id:
            outcome = RoleOutcome.REQUEST_MISMATCH
            failure = "External backend returned a response for a different request"
        elif response.role != request.role:
            outcome = RoleOutcome.ROLE_MISMATCH
            failure = "External backend returned a response for a different role"
        elif not response.success:
            outcome = RoleOutcome.UNSUCCESSFUL_RESPONSE
            failure = "External backend returned success=false"
        else:
            outcome = RoleOutcome.SUCCESS
            failure = None
        return RawRoleExecution(
            response=response,
            stdout=stdout,
            stderr=stderr,
            process_status=completed.returncode,
            outcome=outcome,
            failure=failure,
        )

_OutputT = TypeVar("_OutputT", bound=BaseModel)


class RoleInvocationError(RuntimeError):
    """An external role failed after its immutable invocation was retained."""

    def __init__(self, invocation: RoleInvocation) -> None:
        self.invocation = invocation
        super().__init__(
            f"Role invocation {invocation.invocation_id} failed: {invocation.outcome.value}"
        )


@dataclass(frozen=True)
class RoleInvocationResult(Generic[_OutputT]):
    output: _OutputT
    invocation: RoleInvocation


class RoleInvoker(Generic[_OutputT]):
    """One generic retained executor shared by every role adapter."""

    def __init__(
        self,
        *,
        backend: RoleBackend,
        artifacts: ArtifactStore,
        ledger: Ledger,
        provider: str,
        model: str,
        authority_id: str,
    ) -> None:
        self.backend = backend
        self.artifacts = artifacts
        self.ledger = ledger
        self.provider = provider
        self.model = model
        for name, value in (
            ("provider", provider),
            ("model", model),
            ("authority_id", authority_id),
        ):
            if not value.strip():
                raise ValueError(f"{name} must be nonblank")
        if not isfinite(backend.timeout_seconds) or backend.timeout_seconds <= 0:
            raise ValueError("backend timeout_seconds must be positive and finite")
        self.authority_id = authority_id
        self.timeout_seconds = backend.timeout_seconds

    def invoke(
        self,
        request: RoleRequest,
        output_model: type[_OutputT],
        *,
        semantic_validator: Callable[[_OutputT], None] | None = None,
    ) -> _OutputT:
        result = self.invoke_with_record(
            request, output_model, semantic_validator=semantic_validator
        )
        return result.output

    def invoke_with_record(
        self,
        request: RoleRequest,
        output_model: type[_OutputT],
        *,
        semantic_validator: Callable[[_OutputT], None] | None = None,
    ) -> RoleInvocationResult[_OutputT]:
        if request.output_contract != output_model.model_json_schema():
            raise ValueError(
                "RoleRequest output_contract must exactly match the requested typed model"
            )
        invocation_id = new_id("role-invocation")
        request_ref = self.artifacts.put_model(request)
        input_digest = stable_digest(request.input_artifacts)
        contract_digest = stable_digest(request.output_contract)
        raw = self._execute(request)
        response_ref = self.artifacts.put_model(raw.response) if raw.response is not None else None
        stdout_ref = self._put_stream(raw.stdout, "RoleStdout")
        stderr_ref = self._put_stream(raw.stderr, "RoleStderr")
        output_ref: ArtifactRef | None = None
        output_digest: str | None = None
        outcome = raw.outcome
        failure = raw.failure
        if outcome == RoleOutcome.SUCCESS and raw.response is not None:
            try:
                typed = output_model.model_validate(raw.response.output)
                output_ref = self.artifacts.put_model(typed)
                output_digest = output_ref.digest
                if semantic_validator is not None:
                    try:
                        semantic_validator(typed)
                    except Exception as exc:
                        outcome = RoleOutcome.SEMANTIC_LINK_FAILURE
                        failure = f"Role output failed semantic link validation: {exc}"
            except ValidationError as exc:
                outcome = RoleOutcome.INVALID_TYPED_OUTPUT
                failure = f"Role output failed {output_model.__name__} validation: {exc}"
        transcript = RoleTranscript(
            invocation_id=invocation_id,
            request_id=request.request_id,
            role=request.role,
            response_id=raw.response.response_id if raw.response is not None else None,
            request_ref=request_ref,
            response_ref=response_ref,
            typed_output_ref=output_ref,
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
            input_digest=input_digest,
            output_contract_digest=contract_digest,
            output_digest=output_digest,
            provider=self.provider,
            model=self.model,
            backend=self.backend_identity,
            authority_id=self.authority_id,
            outcome=outcome,
            timeout_seconds=self.timeout_seconds,
            process_status=raw.process_status,
            failure=failure,
        )
        transcript_ref = self.artifacts.put_model(transcript)
        invocation = RoleInvocation(
            invocation_id=invocation_id,
            request_id=request.request_id,
            role=request.role,
            provider=self.provider,
            model=self.model,
            backend=self.backend_identity,
            authority_id=self.authority_id,
            outcome=outcome,
            response_id=raw.response.response_id if raw.response is not None else None,
            request_ref=request_ref,
            transcript_ref=transcript_ref,
            response_ref=response_ref,
            typed_output_ref=output_ref,
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
            input_digest=input_digest,
            output_contract_digest=contract_digest,
            output_digest=output_digest,
            timeout_seconds=self.timeout_seconds,
            process_status=raw.process_status,
            failure=failure,
        )
        self.ledger.add_role_invocation(invocation)
        if outcome != RoleOutcome.SUCCESS or output_ref is None:
            raise RoleInvocationError(invocation)
        return RoleInvocationResult(
            output=self.artifacts.read_model(output_ref, output_model),
            invocation=invocation,
        )

    def _execute(self, request: RoleRequest) -> RawRoleExecution:
        try:
            result = self.backend.execute(request)
        except Exception as exc:  # retain every backend exception
            return RawRoleExecution(
                response=None,
                stdout=None,
                stderr=None,
                process_status=None,
                outcome=RoleOutcome.BACKEND_EXCEPTION,
                failure=f"Role backend exception: {exc}",
            )
        if not isinstance(result, RawRoleExecution):
            return self._protocol_failure(
                None,
                f"Role backend returned {type(result).__name__}; expected RawRoleExecution",
            )
        try:
            return self._normalize_execution(request, result)
        except (TypeError, ValueError) as exc:
            return self._protocol_failure(result, str(exc))

    @staticmethod
    def _normalize_execution(
        request: RoleRequest, result: RawRoleExecution
    ) -> RawRoleExecution:
        if result.response is not None and not isinstance(result.response, RoleResponse):
            raise TypeError("RawRoleExecution.response must be RoleResponse or None")
        for name, stream in (("stdout", result.stdout), ("stderr", result.stderr)):
            if stream is not None and not isinstance(stream, bytes):
                raise TypeError(f"RawRoleExecution.{name} must be bytes or None")
        if result.process_status is not None and (
            isinstance(result.process_status, bool)
            or not isinstance(result.process_status, int)
        ):
            raise TypeError("RawRoleExecution.process_status must be an integer or None")
        if not isinstance(result.outcome, RoleOutcome):
            raise TypeError("RawRoleExecution.outcome must be RoleOutcome")
        if result.failure is not None and not isinstance(result.failure, str):
            raise TypeError("RawRoleExecution.failure must be a string or None")

        response = result.response
        if result.process_status not in {None, 0}:
            if result.outcome != RoleOutcome.NONZERO_EXIT:
                raise ValueError("nonzero process status must use nonzero_exit outcome")
            normalized_outcome = RoleOutcome.NONZERO_EXIT
        elif result.outcome == RoleOutcome.NONZERO_EXIT:
            raise ValueError("nonzero_exit outcome requires a nonzero process status")
        elif result.outcome in {
            RoleOutcome.SUCCESS,
            RoleOutcome.REQUEST_MISMATCH,
            RoleOutcome.ROLE_MISMATCH,
            RoleOutcome.UNSUCCESSFUL_RESPONSE,
        }:
            if response is None:
                raise ValueError(f"{result.outcome.value} outcome requires a response")
            if response.request_id != request.request_id:
                normalized_outcome = RoleOutcome.REQUEST_MISMATCH
            elif response.role != request.role:
                normalized_outcome = RoleOutcome.ROLE_MISMATCH
            elif not response.success:
                normalized_outcome = RoleOutcome.UNSUCCESSFUL_RESPONSE
            else:
                normalized_outcome = RoleOutcome.SUCCESS
            if (
                result.outcome != RoleOutcome.SUCCESS
                and result.outcome != normalized_outcome
            ):
                raise ValueError(
                    "backend outcome disagrees with response identity or success field"
                )
        elif result.outcome == RoleOutcome.MALFORMED_ENVELOPE:
            if response is not None:
                raise ValueError("malformed_envelope outcome cannot carry a response")
            normalized_outcome = result.outcome
        elif result.outcome in {RoleOutcome.TIMEOUT, RoleOutcome.BACKEND_EXCEPTION}:
            if response is not None or result.process_status is not None:
                raise ValueError(
                    f"{result.outcome.value} cannot carry a response or process status"
                )
            normalized_outcome = result.outcome
        else:
            raise ValueError(
                f"backend may not claim post-validation outcome {result.outcome.value}"
            )

        if normalized_outcome == RoleOutcome.SUCCESS:
            if result.failure is not None:
                raise ValueError("successful backend execution cannot carry failure detail")
            failure = None
        else:
            failure = result.failure
            if failure is None or not failure.strip():
                failure = f"Role backend reported {normalized_outcome.value}"
        return RawRoleExecution(
            response=response,
            stdout=result.stdout,
            stderr=result.stderr,
            process_status=result.process_status,
            outcome=normalized_outcome,
            failure=failure,
        )

    @staticmethod
    def _protocol_failure(
        result: RawRoleExecution | None, detail: str
    ) -> RawRoleExecution:
        stdout = result.stdout if result is not None and isinstance(result.stdout, bytes) else None
        stderr = result.stderr if result is not None and isinstance(result.stderr, bytes) else None
        return RawRoleExecution(
            response=None,
            stdout=stdout,
            stderr=stderr,
            process_status=None,
            outcome=RoleOutcome.BACKEND_EXCEPTION,
            failure=f"Role backend protocol violation: {detail}",
        )

    def _put_stream(self, value: bytes | None, model: str) -> ArtifactRef | None:
        if value is None:
            return None
        return ArtifactRef(digest=self.artifacts.put_bytes(value), model=model)

    @property
    def backend_identity(self) -> str:
        backend_type = type(self.backend)
        return f"{backend_type.__module__}.{backend_type.__qualname__}"


# Descriptive alias used by integration callers.
RetainedRoleExecutor = RoleInvoker


def _as_bytes(value: bytes | str | None) -> bytes | None:
    if value is None:
        return None
    return value if isinstance(value, bytes) else value.encode("utf-8", errors="replace")
