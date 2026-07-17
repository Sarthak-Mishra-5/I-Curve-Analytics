"""Entry point: `python -m backend.main` or `uvicorn backend.main:app`."""
from __future__ import annotations

from .api.app import app  # noqa: F401  (re-exported for uvicorn)


def run() -> None:
    import uvicorn
    uvicorn.run("backend.api.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
