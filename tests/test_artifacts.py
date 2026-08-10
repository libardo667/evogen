from __future__ import annotations

from evogen.storage.artifacts import ArtifactStore


def test_artifact_store_is_content_addressed(tmp_path):
    store = ArtifactStore(tmp_path / "objects")
    first = store.put_json({"b": 2, "a": 1})
    second = store.put_json({"a": 1, "b": 2})

    assert first == second
    assert store.verify(first)
    assert store.read_json(first) == {"a": 1, "b": 2}
