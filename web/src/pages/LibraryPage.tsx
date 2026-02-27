import { Link, useSearchParams } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { getDocuments } from "../api/client";
import type { DocumentSummary } from "../types/document";
import DocumentCard from "../components/DocumentCard";
import DocumentTable from "../components/DocumentTable";
import type { SortKey, SortOrder } from "../components/DocumentTable";
import ShelfSidebar from "../components/ShelfSidebar";

type ViewMode = "table" | "cards";

export default function LibraryPage() {
  const [searchParams] = useSearchParams();
  const searchQuery = searchParams.get("search") || "";

  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [sortBy, setSortBy] = useState<SortKey>("uploaded_date");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [loading, setLoading] = useState(true);
  const [activeShelfId, setActiveShelfId] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getDocuments({
      search: searchQuery || undefined,
      shelf: activeShelfId || undefined,
    })
      .then((res) => {
        setDocuments(res.documents);
        setTotal(res.total);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [searchQuery, activeShelfId]);

  const handleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
      return;
    }

    setSortBy(key);
    setSortOrder(key === "title" || key === "author" ? "asc" : "desc");
  };

  const sortedDocuments = useMemo(() => {
    const sorted = [...documents];
    sorted.sort((a, b) => {
      let cmp = 0;

      switch (sortBy) {
        case "title":
          cmp = a.title.toLowerCase().localeCompare(b.title.toLowerCase());
          break;
        case "author":
          cmp = (a.author || "").toLowerCase().localeCompare((b.author || "").toLowerCase());
          break;
        case "page_count":
          cmp = (a.page_count || 0) - (b.page_count || 0);
          break;
        case "uploaded_date":
          cmp = (a.uploaded_date || "").localeCompare(b.uploaded_date || "");
          break;
      }

      return sortOrder === "asc" ? cmp : -cmp;
    });

    return sorted;
  }, [documents, sortBy, sortOrder]);

  if (loading) {
    return <p>Loading...</p>;
  }

  return (
    <div className="library-layout">
      <ShelfSidebar activeShelfId={activeShelfId} onSelectShelf={setActiveShelfId} />

      <div className="library-main">
        {searchQuery && (
          <p style={{ marginBottom: 16, color: "var(--color-text-secondary)" }}>
            Search results for &ldquo;{searchQuery}&rdquo;
          </p>
        )}

        <div className="controls-bar">
          <div>
            <button
              className={`btn ${viewMode === "table" ? "btn-primary" : ""}`}
              onClick={() => setViewMode("table")}
              style={{ borderRadius: "var(--radius) 0 0 var(--radius)" }}
            >
              Table
            </button>
            <button
              className={`btn ${viewMode === "cards" ? "btn-primary" : ""}`}
              onClick={() => setViewMode("cards")}
              style={{ borderRadius: "0 var(--radius) var(--radius) 0", marginLeft: -1 }}
            >
              Cards
            </button>
          </div>

          <span className="total">{total} document(s)</span>
        </div>

        {total === 0 ? (
          <div className="empty-state">
            {searchQuery || activeShelfId !== null ? (
              <>
                <h3>No documents found</h3>
                <p>Try a different search query or shelf.</p>
              </>
            ) : (
              <>
                <h3>No documents in the library yet</h3>
                <p>
                  <Link to="/upload">Upload a document</Link> to get started.
                </p>
              </>
            )}
          </div>
        ) : viewMode === "table" ? (
          <DocumentTable
            documents={sortedDocuments}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleSort}
          />
        ) : (
          <div className="card-grid">
            {sortedDocuments.map((doc) => (
              <DocumentCard key={doc.document_id} document={doc} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
