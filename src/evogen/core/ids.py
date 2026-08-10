from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any


def new_id(prefix: str) -> str:
    """Return a sortable-enough, collision-resistant local identifier."""
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def stable_digest(value: Any) -> str:
    return sha256_bytes(stable_json_bytes(value))
