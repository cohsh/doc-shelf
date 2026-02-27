import { useNavigate } from "react-router-dom";
import type { DocumentSummary } from "../types/document";
import TagBadge from "./TagBadge";

export type SortKey = "title" | "author" | "page_count" | "uploaded_date";
export type SortOrder = "asc" | "desc";

interface Props {
  documents: DocumentSummary[];
  sortBy: SortKey;
  sortOrder: SortOrder;
  onSort: (key: SortKey) => void;
}

export default function DocumentTable({
  documents,
  sortBy,
  sortOrder,
  onSort,
}: Props) {
  const navigate = useNavigate();

  const renderSortIndicator = (key: SortKey) => {
    if (sortBy !== key) return null;
    return <span className="sort-indicator">{sortOrder === "asc" ? "\u25B2" : "\u25BC"}</span>;
  };

  return (
    <table className="paper-table">
      <thead>
        <tr>
          <th className="sortable" onClick={() => onSort("title")}>
            Title {renderSortIndicator("title")}
          </th>
          <th className="sortable" onClick={() => onSort("author")}>
            Author {renderSortIndicator("author")}
          </th>
          <th>Subject</th>
          <th className="sortable" onClick={() => onSort("page_count")}>
            Pages {renderSortIndicator("page_count")}
          </th>
          <th className="sortable" onClick={() => onSort("uploaded_date")}>
            Uploaded {renderSortIndicator("uploaded_date")}
          </th>
          <th>Tags</th>
        </tr>
      </thead>
      <tbody>
        {documents.map((doc) => (
          <tr key={doc.document_id} onClick={() => navigate(`/documents/${doc.document_id}`)}>
            <td style={{ fontWeight: 500 }}>{doc.title}</td>
            <td style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
              {doc.author || "Unknown"}
            </td>
            <td style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
              {doc.subject || "-"}
            </td>
            <td>{doc.page_count}</td>
            <td style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
              {doc.uploaded_date}
            </td>
            <td>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {doc.tags.slice(0, 3).map((tag) => (
                  <TagBadge key={tag} tag={tag} />
                ))}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
