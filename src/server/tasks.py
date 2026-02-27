from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class Task:
    task_id: str
    status: str = "pending"
    progress_message: str = "Queued"
    document_id: str | None = None
    error: str | None = None
    started_at: str = ""
    completed_at: str | None = None


class TaskManager:
    """In-memory task tracker."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def create_task(self) -> str:
        task_id = uuid.uuid4().hex[:12]
        self._tasks[task_id] = Task(
            task_id=task_id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        return task_id

    def update(self, task_id: str, **kwargs: object) -> None:
        task = self._tasks.get(task_id)
        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def all_tasks(self) -> list[Task]:
        return list(self._tasks.values())


def run_ingest_pipeline(
    task_id: str,
    task_manager: TaskManager,
    pdf_path: str,
    output_dir: str,
    source_name: str,
    shelves: list[str] | None = None,
) -> None:
    """Run extract -> save -> index pipeline in a background thread."""
    from src import library, pdf_extractor, storage

    try:
        task_manager.update(
            task_id,
            status="extracting",
            progress_message="Extracting text from PDF...",
        )
        document = pdf_extractor.extract(pdf_path)

        task_manager.update(task_id, status="saving", progress_message="Saving document...")
        document_id = storage.save(document, output_dir, source_name=source_name)
        library.update_index(document_id, output_dir, shelves=shelves)

        task_manager.update(
            task_id,
            status="completed",
            progress_message="Done!",
            document_id=document_id,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error("Ingest pipeline failed: %s", e, exc_info=True)
        task_manager.update(
            task_id,
            status="failed",
            progress_message=str(e),
            error=str(e),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
