"""Panelin API — Root entrypoint for Vercel FastAPI auto-detection."""

from api.index import app  # noqa: F401 — re-export for Vercel
