from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile

from src.exceptions import CodexReaderError
from src.pdf_extractor import ExtractedDocument

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "reading_prompt.txt")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "schema.json")

MAX_TEXT_LENGTH = 80000


def is_available() -> bool:
    return shutil.which("codex") is not None


def read(document: ExtractedDocument) -> dict:
    """Read a document using Codex CLI and return structured JSON."""
    if not is_available():
        raise CodexReaderError(
            "Codex CLI not found. Install it with: npm install -g @openai/codex"
        )

    prompt_template = _load_prompt()
    schema = _load_schema()

    text = document.text
    if len(text) > MAX_TEXT_LENGTH:
        logger.warning(
            "Document text (%s chars) exceeds limit; truncating to %s chars.",
            len(text),
            MAX_TEXT_LENGTH,
        )
        text = text[:MAX_TEXT_LENGTH] + "\n\n[... text truncated due to length ...]"

    prompt = (
        prompt_template
        .replace("{document_title}", document.metadata.get("title", "") or "")
        .replace("{document_author}", document.metadata.get("author", "") or "")
        .replace("{document_subject}", document.metadata.get("subject", "") or "")
        .replace("{document_text}", text)
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="doc_codex_"
    ) as f:
        f.write(prompt)
        prompt_file = f.name

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="schema_codex_"
    ) as f:
        json.dump(schema, f)
        schema_file = f.name

    output_file = tempfile.mktemp(suffix=".json", prefix="codex_output_")

    try:
        cmd = [
            "codex",
            "exec",
            (
                f"Read the file at {prompt_file} and follow the instructions in it. "
                "Respond ONLY with valid JSON matching the schema."
            ),
            "--full-auto",
            "--output-schema",
            schema_file,
            "-o",
            output_file,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            detail = detail[:1200]
            raise CodexReaderError(
                f"Codex CLI failed (exit code {result.returncode}): {detail}"
            )

        return _parse_output(output_file, result.stdout)
    except subprocess.TimeoutExpired:
        raise CodexReaderError("Codex CLI timed out after 600 seconds")
    except FileNotFoundError:
        raise CodexReaderError(
            "Codex CLI not found. Install it with: npm install -g @openai/codex"
        )
    finally:
        for path in (prompt_file, schema_file, output_file):
            try:
                os.unlink(path)
            except OSError:
                pass


def _parse_output(output_file: str, stdout: str) -> dict:
    if os.path.exists(output_file):
        with open(output_file, encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            parsed = _extract_json(content)
            if parsed:
                return parsed

    if stdout.strip():
        parsed = _extract_json(stdout.strip())
        if parsed:
            return parsed

    raise CodexReaderError("No structured output received from Codex CLI")


def _extract_json(text: str) -> dict | None:
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "summary" in data:
            return data
    except json.JSONDecodeError:
        pass

    if "```json" in text:
        start = text.index("```json") + 7
        end = text.find("```", start)
        if end != -1:
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass

    if "```" in text:
        start = text.index("```") + 3
        end = text.find("```", start)
        if end != -1:
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass

    brace_start = text.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(text[brace_start : i + 1])
                        if isinstance(data, dict) and "summary" in data:
                            return data
                    except json.JSONDecodeError:
                        pass
                    break

    return None


def _load_prompt() -> str:
    path = os.path.normpath(PROMPT_PATH)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _load_schema() -> dict:
    path = os.path.normpath(SCHEMA_PATH)
    with open(path, encoding="utf-8") as f:
        return json.load(f)
