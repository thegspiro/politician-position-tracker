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

export interface Source {
  id: number;
  source_type: 'post' | 'analysis';
  title: string;
  url: string;
  description: string | null;
}

export interface SourceInput {
  source_type: 'post' | 'analysis';
  title: string;
  url: string;
  description: string;
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
