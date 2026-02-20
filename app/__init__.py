from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask


def create_app() -> Flask:
    """Application factory for Flask."""
    from app import routes  # noqa: F401, PLC0415 - lazy import: must run after gevent monkey-patch
    from app.app import app  # noqa: PLC0415

    return app
