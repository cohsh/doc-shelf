import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getShelves, getTask, uploadDocument } from "../api/client";
import type { Shelf, TaskStatusValue } from "../types/document";
import IngestProgress from "../components/IngestProgress";
import UploadDropzone from "../components/UploadDropzone";

interface UploadItem {
  file: File;
  taskId: string | null;
  status: TaskStatusValue;
  message: string;
  documentId: string | null;
}

export default function UploadPage() {
  const navigate = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [items, setItems] = useState<UploadItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const pollingRef = useRef<number | null>(null);

  const [allShelves, setAllShelves] = useState<Shelf[]>([]);
  const [selectedShelves, setSelectedShelves] = useState<string[]>([]);

  useEffect(() => {
    getShelves()
      .then((shelves) => setAllShelves(shelves.filter((shelf) => !shelf.is_virtual)))
      .catch(console.error);
  }, []);

  const hasActiveItems = useMemo(
    () =>
      items.some(
        (item) =>
          item.taskId !== null && item.status !== "completed" && item.status !== "failed",
      ),
    [items],
  );

  const handleFilesSelected = useCallback(
    (newFiles: File[]) => {
      if (hasActiveItems || uploading) return;
      setFiles((prev) => [...prev, ...newFiles]);
    },
    [hasActiveItems, uploading],
  );

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleUpload = useCallback(async () => {
    if (files.length === 0) return;
    setUploading(true);

    const initial: UploadItem[] = files.map((file) => ({
      file,
      taskId: null,
      status: "pending",
      message: "Queued...",
      documentId: null,
    }));

    setItems(initial);
    setFiles([]);

    const withTaskIds = [...initial];
    await Promise.all(
      withTaskIds.map(async (item, i) => {
        try {
          const res = await uploadDocument(item.file, selectedShelves);
          withTaskIds[i] = { ...withTaskIds[i], taskId: res.task_id };
        } catch (e) {
          withTaskIds[i] = {
            ...withTaskIds[i],
            status: "failed",
            message: `Upload failed: ${e}`,
          };
        }
      }),
    );

    setItems(withTaskIds);
    setUploading(false);
  }, [files, selectedShelves]);

  const toggleShelf = (shelfId: string) => {
    setSelectedShelves((prev) =>
      prev.includes(shelfId)
        ? prev.filter((id) => id !== shelfId)
        : [...prev, shelfId],
    );
  };

  useEffect(() => {
    const activeItems = items.filter(
      (item) => item.taskId && item.status !== "completed" && item.status !== "failed",
    );

    if (activeItems.length === 0) return;

    const poll = async () => {
      const updates = await Promise.all(
        items.map(async (item) => {
          if (!item.taskId || item.status === "completed" || item.status === "failed") {
            return item;
          }

          try {
            const task = await getTask(item.taskId);
            return {
              ...item,
              status: task.status,
              message: task.progress_message,
              documentId: task.document_id || item.documentId,
            };
          } catch {
            return item;
          }
        }),
      );

      setItems(updates);
    };

    pollingRef.current = window.setInterval(poll, 2000);
    poll();

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [items]);

  const allDone =
    items.length > 0 &&
    items.every((item) => item.status === "completed" || item.status === "failed");

  const handleReset = () => {
    setItems([]);
    setFiles([]);
  };

  return (
    <div style={{ maxWidth: 720, margin: "0 auto" }}>
      <h2 style={{ marginBottom: 24 }}>Upload PDFs</h2>

      <UploadDropzone
        onFilesSelected={handleFilesSelected}
        disabled={hasActiveItems || uploading}
      />

      {files.length > 0 && items.length === 0 && (
        <div style={{ marginTop: 16 }}>
          <p style={{ marginBottom: 8, fontWeight: 500 }}>{files.length} file(s) selected:</p>
          <ul style={{ listStyle: "none", padding: 0, margin: "0 0 12px 0" }}>
            {files.map((file, i) => (
              <li
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "4px 0",
                  fontSize: 14,
                }}
              >
                <span style={{ flex: 1 }}>
                  {file.name}{" "}
                  <span style={{ color: "var(--color-text-secondary)" }}>
                    ({(file.size / 1024 / 1024).toFixed(1)} MB)
                  </span>
                </span>
                <button
                  className="btn btn-sm"
                  onClick={() => removeFile(i)}
                  style={{ padding: "2px 8px" }}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>

          {allShelves.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <span style={{ fontWeight: 500, fontSize: 14 }}>Shelves (optional):</span>
              <div className="shelf-checkbox-list" style={{ marginTop: 6 }}>
                {allShelves.map((shelf) => (
                  <label key={shelf.shelf_id} className="shelf-checkbox-item">
                    <input
                      type="checkbox"
                      checked={selectedShelves.includes(shelf.shelf_id)}
                      onChange={() => toggleShelf(shelf.shelf_id)}
                    />
                    {shelf.name}
                  </label>
                ))}
              </div>
            </div>
          )}

          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={uploading}
            style={{ marginTop: 12 }}
          >
            {uploading
              ? "Uploading..."
              : `Start Import (${files.length} file${files.length > 1 ? "s" : ""})`}
          </button>
        </div>
      )}

      {items.length > 0 && (
        <div style={{ marginTop: 24 }}>
          {items.map((item, i) => (
            <div
              key={i}
              style={{
                marginBottom: 20,
                padding: 16,
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius)",
              }}
            >
              <p style={{ marginBottom: 8, fontWeight: 500, fontSize: 14 }}>{item.file.name}</p>
              <IngestProgress status={item.status} message={item.message} />

              {item.status === "completed" && item.documentId && (
                <div style={{ marginTop: 12 }}>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => navigate(`/documents/${item.documentId}`)}
                  >
                    Open Document
                  </button>
                </div>
              )}
            </div>
          ))}

          {allDone && (
            <button className="btn" onClick={handleReset} style={{ marginTop: 8 }}>
              Upload More PDFs
            </button>
          )}
        </div>
      )}
    </div>
  );
}
