from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from flask import Flask
    from flask.testing import FlaskClient

from app import create_app  # Adjust import to match your app structure


@pytest.fixture
def app() -> Flask:
    """Create application for testing."""
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
        }
    )
    return app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create a test client for the app."""
    return app.test_client()
