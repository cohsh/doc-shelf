import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  deleteDocument,
  getDocument,
  getDocumentText,
  getShelves,
  setDocumentShelves,
} from "../api/client";
import type { DocumentDetail, Shelf } from "../types/document";
import TagBadge from "../components/TagBadge";

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [allShelves, setAllShelves] = useState<Shelf[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showPdf, setShowPdf] = useState(true);
  const [showText, setShowText] = useState(false);
  const [textLoading, setTextLoading] = useState(false);
  const [textError, setTextError] = useState<string | null>(null);
  const [extractedText, setExtractedText] = useState<string>("");

  const [editingShelves, setEditingShelves] = useState(false);
  const [selectedShelfIds, setSelectedShelfIds] = useState<string[]>([]);

  useEffect(() => {
    if (!id) return;

    setLoading(true);
    Promise.all([getDocument(id), getShelves()])
      .then(([doc, shelves]) => {
        setDocument(doc);
        setAllShelves(shelves);
        setSelectedShelfIds(doc.shelves || []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const handleDelete = async () => {
    if (!id || !confirm("Are you sure you want to delete this document?")) return;

    try {
      await deleteDocument(id);
      navigate("/library");
    } catch (e) {
      alert(`Failed to delete: ${e}`);
    }
  };

  const handleSaveShelves = async () => {
    if (!id) return;
    try {
      await setDocumentShelves(id, selectedShelfIds);
      setDocument((prev) => (prev ? { ...prev, shelves: selectedShelfIds } : prev));
      setEditingShelves(false);
    } catch (e) {
      alert(`Failed to update shelves: ${e}`);
    }
  };

  const toggleShelf = (shelfId: string) => {
    setSelectedShelfIds((prev) =>
      prev.includes(shelfId) ? prev.filter((id) => id !== shelfId) : [...prev, shelfId],
    );
  };

  const loadTextIfNeeded = async () => {
    if (!id || extractedText || textLoading) return;
    try {
      setTextLoading(true);
      setTextError(null);
      const res = await getDocumentText(id);
      setExtractedText(res.text);
    } catch (e) {
      setTextError(String(e));
    } finally {
      setTextLoading(false);
    }
  };

  useEffect(() => {
    if (showText) {
      loadTextIfNeeded();
    }
  }, [showText]);

  const userShelves = useMemo(
    () => allShelves.filter((shelf) => !shelf.is_virtual),
    [allShelves],
  );

  if (loading) return <p>Loading...</p>;

  if (error || !document) {
    return (
      <div className="empty-state">
        <h3>Document not found</h3>
        <p>{error}</p>
        <Link to="/library">Back to Library</Link>
      </div>
    );
  }

  const pdfUrl = `/api/documents/${document.document_id}/pdf`;
  const currentShelves = document.shelves || [];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Link to="/library">&larr; Back to Library</Link>
      </div>

      <div className="paper-header">
        <h1>{document.title}</h1>
        <div className="paper-meta">
          <span>{document.author || "Unknown"}</span>
          <span>{document.subject || "No subject"}</span>
          <span>{document.page_count} pages</span>
          <span>{document.char_count.toLocaleString()} chars</span>
          <span>Uploaded: {document.uploaded_date}</span>
          {document.source_name && <span>File: {document.source_name}</span>}
        </div>

        <div className="paper-tags">
          {document.tags.map((tag) => (
            <TagBadge key={tag} tag={tag} />
          ))}
        </div>

        <div className="paper-shelves">
          <span className="paper-shelves-label">Shelves:</span>
          {currentShelves.length === 0 ? (
            <span className="shelf-badge">Unsorted</span>
          ) : (
            currentShelves.map((sid) => {
              const shelf = allShelves.find((s) => s.shelf_id === sid);
              return (
                <span key={sid} className="shelf-badge">
                  {shelf ? shelf.name : sid}
                </span>
              );
            })
          )}

          <button
            className="btn btn-sm"
            onClick={() => {
              setSelectedShelfIds(currentShelves);
              setEditingShelves((prev) => !prev);
            }}
            style={{ marginLeft: 8 }}
          >
            {editingShelves ? "Cancel" : "Edit"}
          </button>
        </div>

        {editingShelves && (
          <div className="shelf-edit-panel">
            {userShelves.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                No shelves created yet. Create one from the library page.
              </p>
            ) : (
              <div className="shelf-checkbox-list">
                {userShelves.map((shelf) => (
                  <label key={shelf.shelf_id} className="shelf-checkbox-item">
                    <input
                      type="checkbox"
                      checked={selectedShelfIds.includes(shelf.shelf_id)}
                      onChange={() => toggleShelf(shelf.shelf_id)}
                    />
                    {shelf.name}
                  </label>
                ))}
              </div>
            )}

            <button
              className="btn btn-primary btn-sm"
              onClick={handleSaveShelves}
              style={{ marginTop: 8 }}
            >
              Save
            </button>
          </div>
        )}

        <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
          <button className="btn" onClick={() => setShowPdf((prev) => !prev)}>
            {showPdf ? "Hide PDF" : "Show PDF"}
          </button>
          <button className="btn" onClick={() => setShowText((prev) => !prev)}>
            {showText ? "Hide Text" : "Show Extracted Text"}
          </button>
          <button className="btn btn-danger" onClick={handleDelete}>
            Delete
          </button>
        </div>
      </div>

      {showPdf && (
        <div style={{ marginTop: 24 }}>
          <h2 style={{ marginBottom: 12 }}>PDF Viewer</h2>
          <iframe
            src={pdfUrl}
            title="PDF Viewer"
            style={{
              width: "100%",
              height: "80vh",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius)",
              background: "#fff",
            }}
          />
        </div>
      )}

      {showText && (
        <div style={{ marginTop: 24 }}>
          <h2 style={{ marginBottom: 12 }}>Extracted Text</h2>
          {textLoading ? (
            <p>Loading extracted text...</p>
          ) : textError ? (
            <p style={{ color: "var(--color-danger)" }}>{textError}</p>
          ) : (
            <pre className="text-viewer">{extractedText}</pre>
          )}
        </div>
      )}
    </div>
  );
}
