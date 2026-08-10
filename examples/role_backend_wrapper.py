"""Minimal JSON-stdio role backend example.

A real wrapper would call a coding model, validate its structured output, and
return artifact references. This example deliberately declines work so the
contract is easy to inspect without API credentials.
"""

from __future__ import annotations

import sys

from evogen.core.ids import new_id
from evogen.core.models import RoleRequest, RoleResponse


def main() -> None:
    request = RoleRequest.model_validate_json(sys.stdin.read())
    response = RoleResponse(
        response_id=new_id("role-response"),
        request_id=request.request_id,
        role=request.role,
        success=False,
        output={},
        notes=[
            "Example wrapper received the role packet but has no model provider configured."
        ],
    )
    sys.stdout.write(response.model_dump_json())


if __name__ == "__main__":
    main()
