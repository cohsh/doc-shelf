from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from src import library
from src.exceptions import StorageError

router = APIRouter()


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
    pdf_path = os.path.join(output_dir, "pdfs", f"{document_id}.pdf")
    if not os.path.exists(pdf_path):
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
    text_path = os.path.join(output_dir, "texts", f"{document_id}.txt")

    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    for path in (json_path, md_path, pdf_path, text_path):
        if os.path.exists(path):
            os.unlink(path)

    index = library.load_index(output_dir)
    index["documents"] = [d for d in index["documents"] if d["document_id"] != document_id]
    library._save_index(index, output_dir)

    return {"ok": True}
