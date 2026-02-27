from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from doc_shelf.exceptions import ReaderError

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
    source_path: str,
    output_dir: str,
    source_name: str,
    shelves: list[str] | None = None,
    reader_choice: str = "both",
) -> None:
    """Run extract -> optional read -> save -> index pipeline."""
    from doc_shelf import eml_extractor, library, pdf_extractor, storage
    from doc_shelf import reader_claude, reader_codex

    try:
        source_ext = Path(source_name or source_path).suffix.lower()
        source_label = "PDF" if source_ext == ".pdf" else "EML" if source_ext == ".eml" else "document"
        task_manager.update(
            task_id,
            status="extracting",
            progress_message=f"Extracting text from {source_label}...",
        )
        if source_ext == ".pdf":
            document = pdf_extractor.extract(source_path)
        elif source_ext == ".eml":
            document = eml_extractor.extract(source_path)
        else:
            raise ValueError("Unsupported file type. Only PDF and EML are accepted.")

        readings: dict[str, dict] = {}

        if reader_choice in ("claude", "both"):
            task_manager.update(
                task_id,
                status="reading_claude",
                progress_message="Claude is reading the document...",
            )
            try:
                readings["claude"] = reader_claude.read(document)
            except ReaderError as e:
                logger.error("Claude reader failed: %s", e)
                if reader_choice == "claude":
                    raise

        if reader_choice in ("codex", "both"):
            task_manager.update(
                task_id,
                status="reading_codex",
                progress_message="Codex is reading the document...",
            )
            try:
                readings["codex"] = reader_codex.read(document)
            except ReaderError as e:
                logger.error("Codex reader failed: %s", e)
                if reader_choice == "codex":
                    raise

        if reader_choice != "none" and not readings:
            raise ReaderError("No reader produced results")

        task_manager.update(
            task_id,
            status="saving",
            progress_message="Saving document...",
        )
        document_id = storage.save(
            document,
            output_dir,
            source_name=source_name,
            readings=readings,
        )
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
        if os.path.exists(source_path):
            os.unlink(source_path)
