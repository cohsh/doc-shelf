from __future__ import annotations

import json
import logging
import os
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from src.exceptions import StorageError
from src.pdf_extractor import ExtractedDocument

logger = logging.getLogger(__name__)


def save(
    document: ExtractedDocument,
    output_dir: str,
    source_name: str = "",
    readings: dict[str, dict] | None = None,
) -> str:
    """Save extracted document data and source file. Returns document_id."""
    title = _get_title(document.metadata, source_name)
    document_id = generate_document_id(title)
    source_type = _detect_source_type(source_name, document.source_path)

    json_dir = os.path.join(output_dir, "json")
    md_dir = os.path.join(output_dir, "markdown")
    text_dir = os.path.join(output_dir, "texts")
    pdf_dir = os.path.join(output_dir, "pdfs")
    eml_dir = os.path.join(output_dir, "emls")

    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(md_dir, exist_ok=True)
    os.makedirs(text_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(eml_dir, exist_ok=True)

    document_id = _resolve_conflict(document_id, json_dir)

    record = _build_json_record(document, document_id, source_name, readings or {})

    json_path = os.path.join(json_dir, f"{document_id}.json")
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    except OSError as e:
        raise StorageError(f"Failed to write JSON file: {e}") from e

    markdown_path = os.path.join(md_dir, f"{document_id}.md")
    markdown = _render_markdown(record, document.text)
    try:
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown)
    except OSError as e:
        raise StorageError(f"Failed to write Markdown file: {e}") from e

    text_path = os.path.join(text_dir, f"{document_id}.txt")
    try:
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(document.text)
    except OSError as e:
        logger.warning("Failed to save extracted text: %s", e)

    if document.source_path and os.path.exists(document.source_path):
        if source_type == "eml":
            source_dest = os.path.join(eml_dir, f"{document_id}.eml")
        else:
            source_dest = os.path.join(pdf_dir, f"{document_id}.pdf")
        try:
            shutil.copy2(document.source_path, source_dest)
            record["source_file"] = source_dest
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.warning("Failed to copy source file: %s", e)

    return document_id


def generate_document_id(value: str) -> str:
    """Create a URL-safe slug from title or filename."""
    if not value:
        return "untitled"

    normalized = unicodedata.normalize("NFKD", value)
    cleaned = re.sub(r"[^\w\s-]", "", normalized).strip().lower()
    slug = re.sub(r"[\s_]+", "-", cleaned)
    slug = slug[:80].rstrip("-")
    return slug or "untitled"


def _resolve_conflict(document_id: str, json_dir: str) -> str:
    if not os.path.exists(os.path.join(json_dir, f"{document_id}.json")):
        return document_id

    i = 2
    while os.path.exists(os.path.join(json_dir, f"{document_id}-{i}.json")):
        i += 1
    return f"{document_id}-{i}"


def _get_title(metadata: dict, source_name: str) -> str:
    title = (metadata.get("title") or "").strip()
    if title:
        return title

    if source_name:
        return Path(source_name).stem

    return "Untitled Document"


def _detect_source_type(source_name: str, source_path: str = "") -> str:
    ext = Path(source_name).suffix.lower() or Path(source_path).suffix.lower()
    if ext == ".eml":
        return "eml"
    return "pdf"


def _tags_from_metadata(metadata: dict) -> list[str]:
    raw = metadata.get("keywords", "") or metadata.get("subject", "") or ""
    if not raw:
        return []

    chunks = re.split(r"[,;]", raw)
    tags: list[str] = []
    for chunk in chunks:
        tag = chunk.strip()
        if tag and tag.lower() not in {t.lower() for t in tags}:
            tags.append(tag)
        if len(tags) >= 8:
            break
    return tags


def _tags_from_readings(readings: dict[str, dict]) -> list[str]:
    tags: list[str] = []
    for data in readings.values():
        for tag in data.get("tags", []) or []:
            if isinstance(tag, str):
                clean = tag.strip()
                if clean and clean.lower() not in {t.lower() for t in tags}:
                    tags.append(clean)
            if len(tags) >= 12:
                return tags
    return tags


def _merge_tags(meta_tags: list[str], reading_tags: list[str]) -> list[str]:
    merged: list[str] = []
    for tag in meta_tags + reading_tags:
        if tag and tag.lower() not in {t.lower() for t in merged}:
            merged.append(tag)
        if len(merged) >= 12:
            break
    return merged


def _build_json_record(
    document: ExtractedDocument,
    document_id: str,
    source_name: str,
    readings: dict[str, dict],
) -> dict:
    metadata = document.metadata
    meta_tags = _tags_from_metadata(metadata)
    reading_tags = _tags_from_readings(readings)

    return {
        "document_id": document_id,
        "title": _get_title(metadata, source_name),
        "source_type": _detect_source_type(source_name, document.source_path),
        "author": metadata.get("author", ""),
        "subject": metadata.get("subject", ""),
        "creator": metadata.get("creator", ""),
        "creation_date": metadata.get("creation_date", ""),
        "uploaded_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source_name": source_name,
        "source_file": document.source_path,
        "page_count": document.page_count,
        "char_count": document.char_count,
        "tags": _merge_tags(meta_tags, reading_tags),
        "readers_used": list(readings.keys()),
        "readings": readings,
    }


def _render_markdown(record: dict, text: str) -> str:
    lines: list[str] = []
    lines.append(f"# {record['title']}")
    lines.append("")
    lines.append(f"**Document ID:** {record['document_id']}  ")
    lines.append(f"**Author:** {record['author'] or 'Unknown'}  ")
    lines.append(f"**Subject:** {record['subject'] or 'N/A'}  ")
    lines.append(f"**Pages:** {record['page_count']}  ")
    lines.append(f"**Characters:** {record['char_count']}  ")
    lines.append(f"**Uploaded:** {record['uploaded_date']}  ")
    if record.get("source_type"):
        lines.append(f"**Source Type:** {str(record['source_type']).upper()}  ")
    if record.get("readers_used"):
        lines.append(f"**Readers:** {', '.join(record['readers_used'])}  ")
    lines.append("")

    readings = record.get("readings", {})
    if readings:
        lines.append("## LLM Readings")
        lines.append("")
        for reader_name in ("claude", "codex"):
            data = readings.get(reader_name)
            if not data:
                continue

            lines.append(f"### {reader_name.capitalize()}")
            lines.append("")

            if data.get("summary"):
                lines.append("#### Summary")
                lines.append(data["summary"])
                lines.append("")

            if data.get("summary_ja"):
                lines.append("#### 要約")
                lines.append(data["summary_ja"])
                lines.append("")

            if data.get("key_points"):
                lines.append("#### Key Points")
                for item in data["key_points"]:
                    lines.append(f"- {item}")
                lines.append("")

            if data.get("key_points_ja"):
                lines.append("#### 重要ポイント")
                for item in data["key_points_ja"]:
                    lines.append(f"- {item}")
                lines.append("")

            keyword_explanations = (
                data.get("keyword_explanations") or data.get("action_items") or []
            )
            if keyword_explanations:
                lines.append("#### Keyword Explanations")
                for item in keyword_explanations:
                    lines.append(f"- {item}")
                lines.append("")

            keyword_explanations_ja = (
                data.get("keyword_explanations_ja") or data.get("action_items_ja") or []
            )
            if keyword_explanations_ja:
                lines.append("#### キーワード解説")
                for item in keyword_explanations_ja:
                    lines.append(f"- {item}")
                lines.append("")

            if data.get("confidence_notes"):
                lines.append("#### Confidence Notes")
                lines.append(data["confidence_notes"])
                lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Extracted Text (Preview)")
    lines.append("")

    preview = text[:8000]
    if len(text) > 8000:
        preview += "\n\n... (truncated in markdown preview, full text is saved in library/texts/)"

    lines.append("```")
    lines.append(preview)
    lines.append("```")

    return "\n".join(lines) + "\n"
