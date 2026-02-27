from __future__ import annotations

import os
import re
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from html import unescape

from doc_shelf.exceptions import EMLExtractionError
from doc_shelf.pdf_extractor import ExtractedDocument


def extract(eml_path: str) -> ExtractedDocument:
    """Extract text and metadata from an EML file."""
    if not os.path.exists(eml_path):
        raise EMLExtractionError(f"File not found: {eml_path}")

    if not eml_path.lower().endswith(".eml"):
        raise EMLExtractionError(f"Not an EML file: {eml_path}")

    try:
        with open(eml_path, "rb") as f:
            message = BytesParser(policy=policy.default).parse(f)
    except Exception as e:
        raise EMLExtractionError(f"Failed to parse EML: {e}") from e

    metadata = _extract_metadata(message)
    body = _extract_body_text(message).strip()
    header_block = _format_headers(message).strip()
    text = "\n\n".join(part for part in (header_block, body) if part).strip()

    if not text:
        raise EMLExtractionError("No readable text content found in EML.")

    return ExtractedDocument(
        text=text,
        metadata=metadata,
        page_count=1,
        source_path=os.path.abspath(eml_path),
        char_count=len(text),
    )


def _extract_metadata(message: EmailMessage) -> dict:
    return {
        "title": str(message.get("subject", "") or "").strip(),
        "author": str(message.get("from", "") or "").strip(),
        "subject": "Email",
        "keywords": "",
        "creator": str(message.get("x-mailer", "") or "").strip(),
        "creation_date": str(message.get("date", "") or "").strip(),
    }


def _format_headers(message: EmailMessage) -> str:
    lines: list[str] = []
    for key, label in (
        ("from", "From"),
        ("to", "To"),
        ("cc", "Cc"),
        ("date", "Date"),
        ("subject", "Subject"),
    ):
        value = str(message.get(key, "") or "").strip()
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def _extract_body_text(message: EmailMessage) -> str:
    plain_chunks: list[str] = []
    html_chunks: list[str] = []

    for part in message.walk():
        if part.is_multipart():
            continue

        disposition = (part.get_content_disposition() or "").lower()
        if disposition == "attachment":
            continue

        content_type = (part.get_content_type() or "").lower()
        text = _read_part_text(part).strip()
        if not text:
            continue

        if content_type == "text/plain":
            plain_chunks.append(text)
        elif content_type == "text/html":
            html_chunks.append(_html_to_text(text))
        elif content_type.startswith("text/"):
            plain_chunks.append(text)

    if plain_chunks:
        return "\n\n".join(plain_chunks)
    if html_chunks:
        return "\n\n".join(html_chunks)
    return ""


def _read_part_text(part: EmailMessage) -> str:
    try:
        content = part.get_content()
        if isinstance(content, str):
            return content
        if isinstance(content, bytes):
            charset = part.get_content_charset() or "utf-8"
            return content.decode(charset, errors="replace")
    except Exception:
        pass

    payload = part.get_payload(decode=True)
    if isinstance(payload, bytes):
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    if isinstance(payload, str):
        return payload
    return ""


def _html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
