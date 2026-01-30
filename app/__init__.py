from flask import Flask

from app import routes  # noqa: F401 - registers routes with app
from app.app import app


def create_app() -> Flask:
    """Application factory for Flask."""
    return app
