export interface Shelf {
  shelf_id: string;
  name: string;
  name_ja: string;
  document_count: number;
  is_virtual: boolean;
  created_at?: string;
}

export interface DocumentSummary {
  document_id: string;
  title: string;
  author: string;
  subject: string;
  uploaded_date: string;
  page_count: number;
  char_count: number;
  tags: string[];
  readers_used?: string[];
  shelves?: string[];
}

export interface ReadingResult {
  title: string;
  author: string;
  document_type: string;
  summary: string;
  summary_ja: string;
  key_points: string[];
  key_points_ja: string[];
  keyword_explanations: string[];
  keyword_explanations_ja: string[];
  action_items?: string[];
  action_items_ja?: string[];
  tags: string[];
  confidence_notes: string;
}

export interface DocumentDetail {
  document_id: string;
  title: string;
  author: string;
  subject: string;
  creator: string;
  creation_date: string;
  uploaded_date: string;
  source_name: string;
  source_file: string;
  page_count: number;
  char_count: number;
  tags: string[];
  readers_used?: string[];
  readings?: {
    claude?: ReadingResult;
    codex?: ReadingResult;
  };
  shelves?: string[];
}

export type TaskStatusValue =
  | "pending"
  | "extracting"
  | "reading_claude"
  | "reading_codex"
  | "saving"
  | "completed"
  | "failed";

export interface TaskStatus {
  task_id: string;
  status: TaskStatusValue;
  progress_message: string;
  document_id: string | null;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface DocumentListResponse {
  documents: DocumentSummary[];
  total: number;
}
