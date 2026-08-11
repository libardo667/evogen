from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from evogen.core.ids import sha256_bytes, stable_json_bytes
from evogen.core.models import ArtifactRef

_ArtifactModelT = TypeVar("_ArtifactModelT", bound=BaseModel)


class ArtifactStore:
    """Small content-addressed store used for immutable EvoGen evidence."""

    def __init__(self, root: Path, *, read_only: bool = False) -> None:
        self.root = root
        self.objects = root / "sha256"
        self.read_only = read_only
        if read_only:
            if not self.objects.is_dir():
                raise FileNotFoundError(f"Artifact store not found: {self.objects}")
        else:
            self.objects.mkdir(parents=True, exist_ok=True)

    def path_for(self, digest: str) -> Path:
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError(f"Invalid sha256 digest: {digest!r}")
        return self.objects / digest[:2] / digest[2:]

    def put_bytes(self, data: bytes) -> str:
        digest = sha256_bytes(data)
        destination = self.path_for(digest)
        if destination.exists():
            if destination.read_bytes() != data:
                raise RuntimeError(f"Digest collision or corrupt artifact at {destination}")
            return digest

        if self.read_only:
            raise RuntimeError(f"Read-only artifact store cannot create {digest}")

        destination.parent.mkdir(parents=True, exist_ok=True)

        temporary = destination.with_suffix(f".tmp-{os.getpid()}")
        temporary.write_bytes(data)
        temporary.replace(destination)
        return digest

    def put_text(self, text: str) -> str:
        return self.put_bytes(text.encode("utf-8"))

    def put_json(self, value: Any) -> str:
        return self.put_bytes(stable_json_bytes(value))

    def put_model(self, model: BaseModel) -> ArtifactRef:
        """Persist a Pydantic value and retain its expected model name."""
        return ArtifactRef(
            digest=self.put_json(model.model_dump(mode="json")),
            model=model.__class__.__name__,
        )

    def read_model(self, reference: ArtifactRef, model: type[_ArtifactModelT]) -> _ArtifactModelT:
        if reference.model != model.__name__:
            raise TypeError(
                f"Artifact {reference.digest} declares {reference.model}, "
                f"expected {model.__name__}"
            )
        return model.model_validate(self.read_json(reference.digest))

    def write_pointer(self, path: Path, value: BaseModel) -> None:
        """Atomically publish a small pointer after validating its bytes."""
        if self.read_only:
            raise RuntimeError(f"Read-only artifact store cannot write pointer {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        data = value.model_dump_json().encode("utf-8")
        temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        temporary.write_bytes(data)
        temporary.replace(path)

    def read_pointer(self, path: Path, model: type[_ArtifactModelT]) -> _ArtifactModelT:
        if not path.exists():
            raise FileNotFoundError(f"Pointer not found: {path}")
        return model.model_validate_json(path.read_bytes())

    def read_bytes(self, digest: str) -> bytes:
        path = self.path_for(digest)
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {digest}")
        data = path.read_bytes()
        if sha256_bytes(data) != digest:
            raise RuntimeError(f"Artifact failed digest verification: {digest}")
        return data

    def read_text(self, digest: str) -> str:
        return self.read_bytes(digest).decode("utf-8")

    def read_json(self, digest: str) -> Any:
        return json.loads(self.read_text(digest))

    def verify(self, digest: str) -> bool:
        try:
            self.read_bytes(digest)
        except (FileNotFoundError, RuntimeError):
            return False
        return True
