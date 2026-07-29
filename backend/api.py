"""ASGI entrypoint used by Uvicorn."""
from app.bootstrap.api import create_app

app = create_app()

