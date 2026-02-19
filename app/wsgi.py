"""
The gevent monkey import and patch suppress a warning, and a potential problem.
Gunicorn would call it anyway, but if it tries to call it after the ssl module
has been initialized in another module (like, in our code, by the botocore library),
then it could lead to inconsistencies in how the ssl module is used. Thus we patch
the ssl module through gevent.monkey.patch_all before any other import, especially
the app import, which would cause the boto module to be loaded, which would in turn
load the ssl module.
"""

# ruff: noqa: E402
from typing import Any

import gevent.monkey

gevent.monkey.patch_all()

# Initialize OTEL before the app is imported.
# The order has an impact on how the libraries are instrumented. If called after app import,
# e.g. the flask instrumentation has no effect. See:
# https://github.com/open-telemetry/opentelemetry.io/blob/main/content/en/docs/zero-code/python/troubleshooting.md#use-programmatic-auto-instrumentation

from app.helpers.otel import initialize, initialize_flask, setup_trace_provider

initialize()

import os

from gunicorn.app.base import BaseApplication

from app import create_app
from app.helpers.utils import get_logging_cfg

app = create_app()
initialize_flask(app)


def post_fork(server: object, worker: object) -> None:
    server.log.info("Worker spawned (pid: %s)", worker.pid)  # type: ignore[attr-defined]
    setup_trace_provider()


class StandaloneApplication(BaseApplication):
    def __init__(self, application: Any, options: dict[str, Any] | None = None) -> None:
        self.options = options or {}
        self.application = application
        super().__init__()

    def load_config(self) -> None:
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self) -> Any:
        return self.application


if __name__ == "__main__":
    port = os.getenv("HTTP_PORT", "8080")
    options: dict[str, Any] = {
        "bind": f"0.0.0.0:{port}",
        "workers": 2,
        "timeout": 60,
        "logconfig_dict": get_logging_cfg(),
        "post_fork": post_fork,
        # Disable gunicorn's asyncio-based control socket — it conflicts with gevent monkey-patching
        "control_socket_disable": True,
    }
    StandaloneApplication(app, options).run()
