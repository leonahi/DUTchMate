"""Service entrypoint for DUTchMate."""

import uvicorn

from dutchmate_service.app import create_app


def main() -> None:
    """Start the Device Core Service."""
    uvicorn.run(create_app(), host="127.0.0.1", port=2040)
