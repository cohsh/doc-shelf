class DocShelfError(Exception):
    """Base exception for doc-shelf."""


class PDFExtractionError(DocShelfError):
    """Error during PDF text extraction."""


class StorageError(DocShelfError):
    """Error during storage and index operations."""
