class DocShelfError(Exception):
    """Base exception for doc-shelf."""


class PDFExtractionError(DocShelfError):
    """Error during PDF text extraction."""


class ReaderError(DocShelfError):
    """Error during LLM reading."""


class ClaudeReaderError(ReaderError):
    """Error specific to Claude reader."""


class CodexReaderError(ReaderError):
    """Error specific to Codex reader."""


class StorageError(DocShelfError):
    """Error during storage and index operations."""
