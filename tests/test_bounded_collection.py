from __future__ import annotations

import pytest

from evogen.core.enums import Completeness
from evogen.core.models import BoundedCollection


def test_complete_collection_has_exact_total():
    collection = BoundedCollection[int](
        items=[1, 2],
        completeness=Completeness.COMPLETE,
        known_total=2,
    )
    assert collection.known_total == 2


def test_truncated_collection_cannot_masquerade_as_complete():
    with pytest.raises(ValueError):
        BoundedCollection[int](
            items=[1, 2],
            completeness=Completeness.TRUNCATED,
            known_total=2,
        )


def test_unknown_collection_carries_no_authoritative_items():
    with pytest.raises(ValueError):
        BoundedCollection[int](
            items=[1],
            completeness=Completeness.UNKNOWN,
        )
