"""Integration tests for the history route."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestHistoryRoute:
    """Integration tests for GET /v1/history."""

    async def test_history_returns_list(self, test_client) -> None:
        """History endpoint should return a list."""
        response = await test_client.get("/v1/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
