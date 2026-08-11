from __future__ import annotations

import pytest

from evogen.core.enums import StageName
from evogen.core.models import StagePointer
from evogen.storage.artifacts import ArtifactStore


def test_artifact_store_is_content_addressed(tmp_path):
    store = ArtifactStore(tmp_path / "objects")
    first = store.put_json({"b": 2, "a": 1})
    second = store.put_json({"a": 1, "b": 2})

    assert first == second
    assert store.verify(first)
    assert store.read_json(first) == {"a": 1, "b": 2}


def test_read_only_artifact_store_rejects_all_writes_without_path_changes(tmp_path):
    writable = ArtifactStore(tmp_path / "objects")
    writable.put_text("existing")
    before = sorted(
        (path.relative_to(tmp_path), path.read_bytes())
        for path in tmp_path.rglob("*")
        if path.is_file()
    )
    readonly = ArtifactStore(tmp_path / "objects", read_only=True)
    with pytest.raises(RuntimeError):
        readonly.put_text("new")
    with pytest.raises(RuntimeError):
        readonly.write_pointer(
            tmp_path / "pointer.json",
            StagePointer(
                pointer_version="1.0",
                cycle_id="cycle-1",
                stage=StageName.INGEST,
                receipt_digest="0" * 64,
            ),
        )
    after = sorted(
        (path.relative_to(tmp_path), path.read_bytes())
        for path in tmp_path.rglob("*")
        if path.is_file()
    )
    assert after == before
