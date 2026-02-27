import type {
  DocumentDetail,
  DocumentListResponse,
  Shelf,
  TaskStatus,
} from "../types/document";

const BASE = "/api";

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export async function getDocuments(params?: {
  sort_by?: string;
  search?: string;
  field?: string;
  shelf?: string;
}): Promise<DocumentListResponse> {
  const query = new URLSearchParams();
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.search) query.set("search", params.search);
  if (params?.field) query.set("field", params.field);
  if (params?.shelf) query.set("shelf", params.shelf);
  const qs = query.toString();
  return fetchJSON(`${BASE}/documents${qs ? `?${qs}` : ""}`);
}

export async function getDocument(documentId: string): Promise<DocumentDetail> {
  return fetchJSON(`${BASE}/documents/${documentId}`);
}

export async function getDocumentText(
  documentId: string,
): Promise<{ text: string }> {
  return fetchJSON(`${BASE}/documents/${documentId}/text`);
}

export async function deleteDocument(documentId: string): Promise<void> {
  await fetchJSON(`${BASE}/documents/${documentId}`, { method: "DELETE" });
}

export async function uploadDocument(
  file: File,
  reader: "none" | "claude" | "codex" | "both" = "both",
  shelves: string[] = [],
): Promise<{ task_id: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("reader", reader);
  if (shelves.length > 0) {
    form.append("shelves", shelves.join(","));
  }
  return fetchJSON(`${BASE}/upload`, { method: "POST", body: form });
}

export async function getTask(taskId: string): Promise<TaskStatus> {
  return fetchJSON(`${BASE}/tasks/${taskId}`);
}

export async function getShelves(): Promise<Shelf[]> {
  return fetchJSON(`${BASE}/shelves`);
}

export async function createShelf(
  name: string,
  nameJa: string = "",
): Promise<Shelf> {
  return fetchJSON(`${BASE}/shelves`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, name_ja: nameJa }),
  });
}

export async function renameShelf(
  shelfId: string,
  name: string,
  nameJa: string = "",
): Promise<{ shelf_id: string; name: string; name_ja?: string }> {
  return fetchJSON(`${BASE}/shelves/${shelfId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, name_ja: nameJa }),
  });
}

export async function deleteShelf(shelfId: string): Promise<void> {
  await fetchJSON(`${BASE}/shelves/${shelfId}`, { method: "DELETE" });
}

export async function setDocumentShelves(
  documentId: string,
  shelfIds: string[],
): Promise<void> {
  await fetchJSON(`${BASE}/documents/${documentId}/shelves`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ shelf_ids: shelfIds }),
  });
}
