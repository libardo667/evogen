from __future__ import annotations

import json
from pathlib import Path

from evogen.schema import MODEL_REGISTRY, export_schemas


def test_committed_schemas_are_fresh(tmp_path):
    generated = tmp_path / "schemas"
    export_schemas(generated)
    committed = Path(__file__).parents[1] / "schemas"

    assert json.loads((generated / "index.json").read_text()) == json.loads(
        (committed / "index.json").read_text()
    )
    for name in MODEL_REGISTRY:
        filename = f"{name}.schema.json"
        assert json.loads((generated / filename).read_text()) == json.loads(
            (committed / filename).read_text()
        )
