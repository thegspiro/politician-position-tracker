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
