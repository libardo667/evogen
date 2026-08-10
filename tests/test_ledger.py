from __future__ import annotations

from evogen.core.models import GenerationManifest
from evogen.storage.ledger import Ledger


def test_ledger_round_trips_generation(tmp_path):
    ledger = Ledger(tmp_path / "evogen.sqlite3")
    generation = GenerationManifest(
        generation_id="gen-1",
        subject="test",
        source_ref="source",
        capability_manifest_digest="0" * 64,
    )
    ledger.add_generation(generation)

    assert ledger.get_generation("gen-1") == generation
    assert ledger.list_generations() == [generation]
