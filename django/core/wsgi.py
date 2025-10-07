"""WSGI helpers for the Django stub."""
from __future__ import annotations


def get_wsgi_application():  # pragma: no cover - integration hook
    def application(environ, start_response):
        start_response("500 ERROR", [("Content-Type", "text/plain")])
        return [b"WSGI not implemented in stub"]

    return application
