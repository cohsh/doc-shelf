import { useNavigate } from "react-router-dom";
import type { DocumentSummary } from "../types/document";
import TagBadge from "./TagBadge";

interface Props {
  document: DocumentSummary;
}

export default function DocumentCard({ document }: Props) {
  const navigate = useNavigate();

  return (
    <div className="card" onClick={() => navigate(`/documents/${document.document_id}`)}>
      <div className="paper-card-title">{document.title}</div>
      <div className="paper-card-meta">
        {(document.author || "Unknown") + " · " + document.page_count + " pages · " + document.uploaded_date}
        {document.subject && <> · <em>{document.subject}</em></>}
      </div>
      <div className="paper-card-tags">
        {document.tags.slice(0, 5).map((tag) => (
          <TagBadge key={tag} tag={tag} />
        ))}
      </div>
    </div>
  );
}
