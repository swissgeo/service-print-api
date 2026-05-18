from unittest.mock import MagicMock

from httpx import ASGITransport, AsyncClient

import pytest

from app.dependencies import get_session
from app.main import app


@pytest.fixture
async def client():
    def _mock_session() -> MagicMock:
        return MagicMock()

    app.dependency_overrides[get_session] = _mock_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_session, None)
