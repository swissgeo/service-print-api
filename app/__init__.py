from typing import TYPE_CHECKING

from app import routes  # noqa: F401 - registers routes with app
from app.app import app

if TYPE_CHECKING:
    from flask import Flask


def create_app() -> Flask:
    """Application factory for Flask."""
    return app
