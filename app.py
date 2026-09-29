"""Shim so the app can also be started with ``uvicorn app:app``.

The real implementation lives in :mod:`mahva.webapp`.
"""
from __future__ import annotations

from mahva.webapp import app, create_app, main  # noqa: F401

__all__ = ["app", "create_app", "main"]

if __name__ == "__main__":  # pragma: no cover
    main()
