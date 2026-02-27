from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from doc_shelf.exceptions import StorageError
from doc_shelf.storage import generate_document_id

UNSORTED_SHELF_ID = "__unsorted__"
UNSORTED_SHELF_NAME = "Unsorted"
UNSORTED_SHELF_NAME_JA = "未分類"


def _save_index(index: dict, output_dir: str) -> None:
    index["updated_at"] = datetime.now(timezone.utc).isoformat()
    index_path = os.path.join(output_dir, "index.json")
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except OSError as e:
        raise StorageError(f"Failed to write index: {e}") from e


def _find_document(documents: list[dict], document_id: str) -> dict | None:
    for doc in documents:
        if doc["document_id"] == document_id:
            return doc
    return None


def load_index(output_dir: str) -> dict:
    index_path = os.path.join(output_dir, "index.json")
    if os.path.exists(index_path):
        try:
            with open(index_path, encoding="utf-8") as f:
                index = json.load(f)
            if isinstance(index, dict):
                index.setdefault("version", 1)
                index.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
                index.setdefault("shelves", [])
                index.setdefault("documents", [])
                for entry in index["documents"]:
                    entry.setdefault("shelves", [])
                return index
        except json.JSONDecodeError:
            pass

    return {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "shelves": [],
        "documents": [],
    }


def update_index(
    document_id: str,
    output_dir: str,
    shelves: list[str] | None = None,
) -> None:
    index = load_index(output_dir)
    doc_data = get_document(document_id, output_dir)

    entry = {
        "document_id": document_id,
        "title": doc_data.get("title", ""),
        "source_type": doc_data.get("source_type", ""),
        "author": doc_data.get("author", ""),
        "subject": doc_data.get("subject", ""),
        "uploaded_date": doc_data.get("uploaded_date", ""),
        "page_count": doc_data.get("page_count", 0),
        "char_count": doc_data.get("char_count", 0),
        "tags": doc_data.get("tags", []),
        "readers_used": doc_data.get("readers_used", []),
        "shelves": shelves if shelves is not None else [],
    }

    documents = index["documents"]
    existing_idx = next(
        (i for i, d in enumerate(documents) if d["document_id"] == document_id),
        None,
    )
    if existing_idx is not None:
        if shelves is None:
            entry["shelves"] = documents[existing_idx].get("shelves", [])
        documents[existing_idx] = entry
    else:
        documents.append(entry)

    _save_index(index, output_dir)


def get_document(document_id: str, output_dir: str) -> dict:
    json_path = os.path.join(output_dir, "json", f"{document_id}.json")
    if not os.path.exists(json_path):
        raise StorageError(f"Document not found: {document_id}")
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def save_document(document_id: str, data: dict, output_dir: str) -> None:
    json_path = os.path.join(output_dir, "json", f"{document_id}.json")
    if not os.path.exists(json_path):
        raise StorageError(f"Document not found: {document_id}")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_document_text(document_id: str, output_dir: str) -> str:
    text_path = os.path.join(output_dir, "texts", f"{document_id}.txt")
    if os.path.exists(text_path):
        with open(text_path, encoding="utf-8") as f:
            return f.read()

    raise StorageError(f"Text not found for document: {document_id}")


def search(
    query: str,
    field: str = "all",
    output_dir: str = "library",
    shelf: str | None = None,
) -> list[dict]:
    index = load_index(output_dir)
    query_lower = query.lower()
    results = []

    for entry in index["documents"]:
        if shelf is not None:
            doc_shelves = entry.get("shelves", [])
            if shelf == UNSORTED_SHELF_ID:
                if doc_shelves:
                    continue
            elif shelf not in doc_shelves:
                continue

        if _matches(entry, query_lower, field, output_dir):
            results.append(entry)

    return results


def list_documents_by_shelf(shelf_id: str | None, output_dir: str) -> list[dict]:
    index = load_index(output_dir)

    if shelf_id is None:
        return index["documents"]

    documents: list[dict] = []
    for doc in index["documents"]:
        doc_shelves = doc.get("shelves", [])
        if shelf_id == UNSORTED_SHELF_ID:
            if not doc_shelves:
                documents.append(doc)
        elif shelf_id in doc_shelves:
            documents.append(doc)

    return documents


def create_shelf(name: str, output_dir: str, name_ja: str = "") -> dict:
    index = load_index(output_dir)
    shelf_id = generate_document_id(name)

    if any(s["shelf_id"] == shelf_id for s in index["shelves"]):
        raise StorageError(f"Shelf already exists: {shelf_id}")

    shelf = {
        "shelf_id": shelf_id,
        "name": name,
        "name_ja": name_ja,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    index["shelves"].append(shelf)
    _save_index(index, output_dir)
    return shelf


def list_shelves(output_dir: str) -> list[dict]:
    index = load_index(output_dir)

    shelf_counts: dict[str, int] = {}
    unsorted_count = 0
    for doc in index["documents"]:
        doc_shelves = doc.get("shelves", [])
        if not doc_shelves:
            unsorted_count += 1
        for sid in doc_shelves:
            shelf_counts[sid] = shelf_counts.get(sid, 0) + 1

    shelves: list[dict] = [
        {
            "shelf_id": UNSORTED_SHELF_ID,
            "name": UNSORTED_SHELF_NAME,
            "name_ja": UNSORTED_SHELF_NAME_JA,
            "document_count": unsorted_count,
            "is_virtual": True,
        }
    ]

    for shelf in index["shelves"]:
        shelves.append(
            {
                **shelf,
                "document_count": shelf_counts.get(shelf["shelf_id"], 0),
                "is_virtual": False,
            }
        )

    return shelves


def get_shelf(shelf_id: str, output_dir: str) -> dict:
    if shelf_id == UNSORTED_SHELF_ID:
        return {
            "shelf_id": UNSORTED_SHELF_ID,
            "name": UNSORTED_SHELF_NAME,
            "name_ja": UNSORTED_SHELF_NAME_JA,
            "is_virtual": True,
        }

    index = load_index(output_dir)
    for shelf in index["shelves"]:
        if shelf["shelf_id"] == shelf_id:
            return shelf

    raise StorageError(f"Shelf not found: {shelf_id}")


def rename_shelf(
    shelf_id: str,
    name: str,
    output_dir: str,
    name_ja: str | None = None,
) -> dict:
    if shelf_id == UNSORTED_SHELF_ID:
        raise StorageError("Cannot rename the Unsorted shelf")

    index = load_index(output_dir)
    new_shelf_id = generate_document_id(name)

    for shelf in index["shelves"]:
        if shelf["shelf_id"] == shelf_id:
            old_id = shelf["shelf_id"]
            shelf["shelf_id"] = new_shelf_id
            shelf["name"] = name
            if name_ja is not None:
                shelf["name_ja"] = name_ja

            if old_id != new_shelf_id:
                for doc in index["documents"]:
                    doc_shelves = doc.get("shelves", [])
                    if old_id in doc_shelves:
                        doc_shelves[doc_shelves.index(old_id)] = new_shelf_id

            _save_index(index, output_dir)
            return shelf

    raise StorageError(f"Shelf not found: {shelf_id}")


def delete_shelf(shelf_id: str, output_dir: str) -> None:
    if shelf_id == UNSORTED_SHELF_ID:
        raise StorageError("Cannot delete the Unsorted shelf")

    index = load_index(output_dir)
    original_count = len(index["shelves"])
    index["shelves"] = [s for s in index["shelves"] if s["shelf_id"] != shelf_id]

    if len(index["shelves"]) == original_count:
        raise StorageError(f"Shelf not found: {shelf_id}")

    for doc in index["documents"]:
        doc_shelves = doc.get("shelves", [])
        if shelf_id in doc_shelves:
            doc_shelves.remove(shelf_id)

    _save_index(index, output_dir)


def assign_document_to_shelves(
    document_id: str,
    shelf_ids: list[str],
    output_dir: str,
) -> None:
    index = load_index(output_dir)

    valid_ids = {s["shelf_id"] for s in index["shelves"]}
    for sid in shelf_ids:
        if sid != UNSORTED_SHELF_ID and sid not in valid_ids:
            raise StorageError(f"Shelf not found: {sid}")

    clean_ids = [sid for sid in shelf_ids if sid != UNSORTED_SHELF_ID]

    doc = _find_document(index["documents"], document_id)
    if doc is None:
        raise StorageError(f"Document not found: {document_id}")

    doc["shelves"] = clean_ids
    _save_index(index, output_dir)


def add_document_to_shelf(document_id: str, shelf_id: str, output_dir: str) -> None:
    index = load_index(output_dir)

    if shelf_id != UNSORTED_SHELF_ID:
        if not any(s["shelf_id"] == shelf_id for s in index["shelves"]):
            raise StorageError(f"Shelf not found: {shelf_id}")

    doc = _find_document(index["documents"], document_id)
    if doc is None:
        raise StorageError(f"Document not found: {document_id}")

    shelves = doc.get("shelves", [])
    if shelf_id not in shelves:
        shelves.append(shelf_id)
        doc["shelves"] = shelves

    _save_index(index, output_dir)


def remove_document_from_shelf(document_id: str, shelf_id: str, output_dir: str) -> None:
    index = load_index(output_dir)

    doc = _find_document(index["documents"], document_id)
    if doc is None:
        raise StorageError(f"Document not found: {document_id}")

    shelves = doc.get("shelves", [])
    if shelf_id in shelves:
        shelves.remove(shelf_id)
    doc["shelves"] = shelves

    _save_index(index, output_dir)


def _matches(entry: dict, query: str, field: str, output_dir: str) -> bool:
    title = entry.get("title", "").lower()
    author = entry.get("author", "").lower()
    subject = entry.get("subject", "").lower()
    tags = [t.lower() for t in entry.get("tags", [])]
    readers = [r.lower() for r in entry.get("readers_used", [])]

    def _matches_readings(document_id: str) -> bool:
        try:
            data = get_document(document_id, output_dir)
        except StorageError:
            return False

        readings = data.get("readings", {})
        for reader_data in readings.values():
            if not isinstance(reader_data, dict):
                continue
            for value in reader_data.values():
                if isinstance(value, str) and query in value.lower():
                    return True
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str) and query in item.lower():
                            return True
        return False

    if field == "title":
        return query in title
    if field == "author":
        return query in author
    if field == "subject":
        return query in subject
    if field == "tags":
        return any(query in t for t in tags)
    if field == "readers":
        return any(query in r for r in readers)
    if field == "readings":
        return _matches_readings(entry["document_id"])
    if field == "text":
        try:
            text = get_document_text(entry["document_id"], output_dir)
            return query in text.lower()
        except StorageError:
            return False

    if query in title or query in author or query in subject:
        return True
    if any(query in t for t in tags):
        return True
    if any(query in r for r in readers):
        return True
    if _matches_readings(entry["document_id"]):
        return True

    try:
        text = get_document_text(entry["document_id"], output_dir)
        return query in text.lower()
    except StorageError:
        return False
