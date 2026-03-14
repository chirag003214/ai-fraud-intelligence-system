"""Integration tests for the explain route."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestExplainRoute:
    """Integration tests for GET /v1/explain/{txn_id}."""

    async def test_unknown_txn_returns_404(self, test_client) -> None:
        """Request for a non-existent transaction should return 404."""
        response = await test_client.get("/v1/explain/non-existent-id")
        assert response.status_code == 404
