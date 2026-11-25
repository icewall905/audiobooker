#!/usr/bin/env python3
"""Backwards compatible entry point: ``python web_interface.py`` == ``audiobook-web``.

The UI and job runner live in :mod:`audiobooker.web`.
"""

from __future__ import annotations

from audiobooker import VERSION
from audiobooker.web import build_interface, generate_audiobook, main

__all__ = ["VERSION", "build_interface", "generate_audiobook", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
