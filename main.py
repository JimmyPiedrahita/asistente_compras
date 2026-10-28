"""Punto de entrada ASGI.

Uso local:
    uvicorn main:app --reload
"""

from __future__ import annotations

import os

from views.api.app import create_app

app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("UVICORN_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
