from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from doc_shelf.server.tasks import TaskManager


def create_app(output_dir: str = "library", dev_mode: bool = False) -> FastAPI:
    app = FastAPI(title="Doc Shelf", version="0.1.0")

    app.state.output_dir = output_dir
    app.state.task_manager = TaskManager()

    if dev_mode:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    from doc_shelf.server.routes_documents import router as documents_router
    from doc_shelf.server.routes_shelves import router as shelves_router
    from doc_shelf.server.routes_upload import router as upload_router

    app.include_router(documents_router, prefix="/api")
    app.include_router(shelves_router, prefix="/api")
    app.include_router(upload_router, prefix="/api")

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir) and os.listdir(static_dir):
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        index_html = os.path.join(static_dir, "index.html")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            file_path = os.path.join(static_dir, full_path)
            if full_path and os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(index_html)

    return app
