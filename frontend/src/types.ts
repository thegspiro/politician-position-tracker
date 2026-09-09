export interface Politician {
  id: number;
  name: string;
  party: string;
  office: string;
  state: string | null;
  photo_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface Issue {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

export type MediaType =
  | 'webpage'
  | 'document'
  | 'video'
  | 'audio'
  | 'article'
  | 'dataset';

export const MEDIA_TYPES: MediaType[] = [
  'webpage',
  'document',
  'video',
  'audio',
  'article',
  'dataset',
];

export const MEDIA_TYPE_LABELS: Record<MediaType, string> = {
  webpage: 'Web page',
  document: 'Document',
  video: 'Video',
  audio: 'Audio',
  article: 'News article',
  dataset: 'Dataset',
};

export type CitationStyle = 'notes-bibliography' | 'author-date';

export const CITATION_STYLE_LABELS: Record<CitationStyle, string> = {
  'notes-bibliography': 'Notes-Bibliography',
  'author-date': 'Author-Date',
};

/** A personal name, or a corporate one via `literal`. */
export interface Author {
  given?: string | null;
  family?: string | null;
  literal?: string | null;
}

/** A run of citation text. Italics are structural, never markup. */
export interface CitationSpan {
  text: string;
  italic: boolean;
}

export interface CitationForm {
  /** Plain text, for copying. */
  text: string;
  /** The same content as renderable runs. */
  spans: CitationSpan[];
}

export interface CitationSet {
  note: CitationForm;
  bibliography: CitationForm;
  author_date_citation: CitationForm;
  author_date_reference: CitationForm;
}

export const DOCUMENT_TYPES = [
  'bill',
  'statute',
  'hearing',
  'committee_report',
  'court_opinion',
  'executive_order',
  'other',
] as const;

export type DocumentType = (typeof DOCUMENT_TYPES)[number];

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  bill: 'Bill',
  statute: 'Statute',
  hearing: 'Hearing',
  committee_report: 'Committee report',
  court_opinion: 'Court opinion',
  executive_order: 'Executive order',
  other: 'Other',
};

export interface Source {
  id: number;
  /** Stable public identifier. Survives statement edits, so citations and
   *  fragment links can point at it. */
  uid: string;
  source_type: 'post' | 'analysis';
  title: string;
  url: string;
  description: string | null;
  media_type: MediaType;
  publisher: string | null;
  published_date: string | null;
  /** Verbatim passage being relied on. */
  excerpt: string | null;
  /** Where in the source the excerpt lives: "p. 14", "sec. 203", "01:23:45". */
  locator: string | null;
  archive_url: string | null;
  archived_at: string | null;
  retrieved_at: string | null;
  sort_order: number;
  authors: Author[];
  container_title: string | null;
  edition: string | null;
  document_type: DocumentType | null;
  bill_number: string | null;
  congress_number: number | null;
  congress_session: string | null;
  committee: string | null;
  report_number: string | null;
  /** Rendered server-side, so exports cannot drift from what is displayed. */
  citations?: CitationSet;
}

export interface SourceInput {
  /** Present when editing an existing source, so its uid is preserved. */
  uid?: string;
  source_type: 'post' | 'analysis';
  title: string;
  url: string;
  description: string;
  media_type: MediaType;
  publisher: string;
  published_date: string;
  excerpt: string;
  locator: string;
  archive_url: string;
  archived_at: string;
  retrieved_at: string;
  authors: Author[];
  container_title: string;
  edition: string;
  document_type: DocumentType | '';
  bill_number: string;
  congress_number: string;
  congress_session: string;
  committee: string;
  report_number: string;
}

/** The shape sent to the API when creating or updating a statement's sources. */
export interface SourcePayload {
  uid?: string;
  source_type: 'post' | 'analysis';
  title: string;
  url: string;
  description: string | null;
  media_type: MediaType;
  publisher: string | null;
  published_date: string | null;
  excerpt: string | null;
  locator: string | null;
  archive_url: string | null;
  archived_at: string | null;
  retrieved_at: string | null;
  authors: Author[];
  container_title: string | null;
  edition: string | null;
  document_type: DocumentType | null;
  bill_number: string | null;
  congress_number: number | null;
  congress_session: string | null;
  committee: string | null;
  report_number: string | null;
}

/** Response of GET /api/statements/:id/citations. */
export interface StatementCitations {
  default_style: CitationStyle;
  site_name: string;
  sources: (CitationSet & {
    uid: string;
    source_type: 'post' | 'analysis';
    sort_order: number;
  })[];
  post: CitationSet;
  page: CitationSet;
}

export interface Statement {
  id: number;
  politician_id: number;
  title: string;
  analysis: string;
  post_url: string;
  post_platform: string;
  post_content: string | null;
  screenshot_url: string | null;
  post_date: string | null;
  created_at: string;
  updated_at: string;
  politician: Politician;
  issues: Issue[];
  sources?: Source[];
}

export interface PoliticianDetail extends Politician {
  statements: Statement[];
}

export interface IssueDetail extends Issue {
  statements: Statement[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}
