from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from evogen.core.ids import sha256_bytes, stable_json_bytes


class ArtifactStore:
    """Small content-addressed store used for immutable EvoGen evidence."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.objects = root / "sha256"
        self.objects.mkdir(parents=True, exist_ok=True)

    def path_for(self, digest: str) -> Path:
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError(f"Invalid sha256 digest: {digest!r}")
        return self.objects / digest[:2] / digest[2:]

    def put_bytes(self, data: bytes) -> str:
        digest = sha256_bytes(data)
        destination = self.path_for(digest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != data:
                raise RuntimeError(f"Digest collision or corrupt artifact at {destination}")
            return digest

        temporary = destination.with_suffix(f".tmp-{os.getpid()}")
        temporary.write_bytes(data)
        temporary.replace(destination)
        return digest

    def put_text(self, text: str) -> str:
        return self.put_bytes(text.encode("utf-8"))

    def put_json(self, value: Any) -> str:
        return self.put_bytes(stable_json_bytes(value))

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
