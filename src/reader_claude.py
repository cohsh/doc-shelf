from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile

from src.exceptions import ClaudeReaderError
from src.pdf_extractor import ExtractedDocument

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "reading_prompt.txt")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "schema.json")

MAX_TEXT_LENGTH = 120000


def read(document: ExtractedDocument) -> dict:
    """Read a document using Claude Code CLI and return structured JSON."""
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
        mode="w", suffix=".txt", delete=False, prefix="doc_"
    ) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        cmd = [
            "claude",
            "-p",
            (
                f"Read the file at {prompt_file} and follow the instructions in it. "
                f"Respond ONLY with valid JSON matching this schema: {json.dumps(schema)}"
            ),
            "--output-format",
            "json",
            "--allowedTools",
            "Read",
        ]

        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            detail = detail[:1200]
            raise ClaudeReaderError(
                f"Claude CLI failed (exit code {result.returncode}): {detail}"
            )

        return _parse_response(result.stdout)
    except subprocess.TimeoutExpired:
        raise ClaudeReaderError("Claude CLI timed out after 600 seconds")
    except FileNotFoundError:
        raise ClaudeReaderError(
            "Claude CLI not found. Install it with: npm install -g @anthropic-ai/claude-code"
        )
    finally:
        try:
            os.unlink(prompt_file)
        except OSError:
            pass


def _parse_response(stdout: str) -> dict:
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise ClaudeReaderError(f"Failed to parse Claude output as JSON: {e}") from e

    if isinstance(response, dict):
        text = response.get("result", "")
        if text:
            parsed = _extract_json(text)
            if parsed:
                return parsed
        if "summary" in response:
            return response

    raise ClaudeReaderError("Could not extract structured reading JSON from Claude output")


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
