from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from doc_shelf import library
from doc_shelf.exceptions import StorageError

router = APIRouter()


def _resolve_source_type(document: dict) -> str:
    source_type = str(document.get("source_type", "") or "").lower()
    if source_type in ("pdf", "eml"):
        return source_type

    for candidate in (document.get("source_name", ""), document.get("source_file", "")):
        text = str(candidate or "").lower()
        if text.endswith(".pdf"):
            return "pdf"
        if text.endswith(".eml"):
            return "eml"
    return ""


def _resolve_existing_path(path: str, output_dir: str) -> str | None:
    if not path:
        return None
    candidates = [path]
    if not os.path.isabs(path):
        candidates.append(os.path.abspath(path))
        candidates.append(os.path.abspath(os.path.join(output_dir, path)))
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


@router.get("/documents")
def list_documents(
    request: Request,
    sort_by: str = "date",
    search: str | None = None,
    field: str = "all",
    shelf: str | None = None,
) -> dict:
    output_dir = request.app.state.output_dir

    if search:
        docs = library.search(search, field=field, output_dir=output_dir, shelf=shelf)
    else:
        docs = library.list_documents_by_shelf(shelf, output_dir)

    if sort_by == "title":
        docs.sort(key=lambda d: d.get("title", "").lower())
    elif sort_by == "date":
        docs.sort(key=lambda d: d.get("uploaded_date", ""), reverse=True)
    elif sort_by == "pages":
        docs.sort(key=lambda d: d.get("page_count", 0), reverse=True)

    return {"documents": docs, "total": len(docs)}


@router.get("/documents/{document_id}")
def get_document(document_id: str, request: Request) -> dict:
    output_dir = request.app.state.output_dir
    try:
        document = library.get_document(document_id, output_dir)
    except StorageError:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    index = library.load_index(output_dir)
    for entry in index["documents"]:
        if entry["document_id"] == document_id:
            document["shelves"] = entry.get("shelves", [])
            break
    else:
        document["shelves"] = []

    return document


@router.get("/documents/{document_id}/text")
def get_document_text(document_id: str, request: Request) -> dict:
    output_dir = request.app.state.output_dir
    try:
        text = library.get_document_text(document_id, output_dir)
        return {"text": text}
    except StorageError:
        raise HTTPException(status_code=404, detail=f"Text not found: {document_id}")


@router.get("/documents/{document_id}/pdf")
def get_document_pdf(document_id: str, request: Request) -> FileResponse:
    output_dir = request.app.state.output_dir
    try:
        document = library.get_document(document_id, output_dir)
    except StorageError:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    source_type = _resolve_source_type(document)
    if source_type and source_type != "pdf":
        raise HTTPException(status_code=400, detail=f"Document is not a PDF: {document_id}")

    source_file = str(document.get("source_file", "") or "")
    pdf_path = None
    if source_file.lower().endswith(".pdf"):
        pdf_path = _resolve_existing_path(source_file, output_dir)

    if not pdf_path:
        legacy_pdf_path = os.path.join(output_dir, "pdfs", f"{document_id}.pdf")
        if os.path.exists(legacy_pdf_path):
            pdf_path = legacy_pdf_path

    if not pdf_path:
        raise HTTPException(status_code=404, detail=f"PDF not found: {document_id}")

    # Avoid non-ASCII header encoding issues by returning the file directly
    # without building Content-Disposition from user-visible IDs.
    return FileResponse(pdf_path, media_type="application/pdf")


@router.delete("/documents/{document_id}")
def delete_document(document_id: str, request: Request) -> dict:
    output_dir = request.app.state.output_dir

    json_path = os.path.join(output_dir, "json", f"{document_id}.json")
    md_path = os.path.join(output_dir, "markdown", f"{document_id}.md")
    pdf_path = os.path.join(output_dir, "pdfs", f"{document_id}.pdf")
    eml_path = os.path.join(output_dir, "emls", f"{document_id}.eml")
    text_path = os.path.join(output_dir, "texts", f"{document_id}.txt")

    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    source_file = ""
    try:
        source_file = str(library.get_document(document_id, output_dir).get("source_file", "") or "")
    except StorageError:
        pass

    source_path = _resolve_existing_path(source_file, output_dir)
    paths = {json_path, md_path, pdf_path, eml_path, text_path}
    if source_path:
        paths.add(source_path)

    for path in paths:
        if os.path.exists(path):
            os.unlink(path)

    index = library.load_index(output_dir)
    index["documents"] = [d for d in index["documents"] if d["document_id"] != document_id]
    library._save_index(index, output_dir)

    return {"ok": True}
