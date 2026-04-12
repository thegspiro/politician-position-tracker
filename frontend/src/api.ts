import type {
  Politician,
  PoliticianDetail,
  Issue,
  IssueDetail,
  Statement,
  PaginatedResponse,
} from './types';

const API_BASE = '/api';

// ── Auth token management ───────────────────────────────────

let authToken: string | null = localStorage.getItem('auth_token');

export function getToken(): string | null {
  return authToken;
}

export function setToken(token: string | null) {
  authToken = token;
  if (token) {
    localStorage.setItem('auth_token', token);
  } else {
    localStorage.removeItem('auth_token');
  }
}

export function isLoggedIn(): boolean {
  return authToken !== null;
}

// ── Request helper ──────────────────────────────────────────

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { ...headers, ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    if (res.status === 401) {
      setToken(null);
    }
    const body = await res.text().catch(() => '');
    throw new Error(`API error ${res.status}: ${body}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

// ── Auth ────────────────────────────────────────────────────

export function login(password: string): Promise<{ token: string }> {
  return request<{ token: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
}

// ── Politicians ─────────────────────────────────────────────

export function fetchPoliticians(
  skip = 0,
  limit = 200,
): Promise<PaginatedResponse<Politician>> {
  return request<PaginatedResponse<Politician>>(
    `/politicians?skip=${skip}&limit=${limit}`,
  );
}

export function fetchPolitician(
  id: number | string,
): Promise<PoliticianDetail> {
  return request<PoliticianDetail>(`/politicians/${id}`);
}

export function createPolitician(
  data: Omit<Politician, 'id' | 'created_at' | 'updated_at'>,
): Promise<Politician> {
  return request<Politician>('/politicians', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updatePolitician(
  id: number | string,
  data: Omit<Politician, 'id' | 'created_at' | 'updated_at'>,
): Promise<Politician> {
  return request<Politician>(`/politicians/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deletePolitician(id: number | string): Promise<void> {
  return request<void>(`/politicians/${id}`, { method: 'DELETE' });
}

// ── Issues ──────────────────────────────────────────────────

export function fetchIssues(
  skip = 0,
  limit = 200,
): Promise<PaginatedResponse<Issue>> {
  return request<PaginatedResponse<Issue>>(
    `/issues?skip=${skip}&limit=${limit}`,
  );
}

export function fetchIssue(id: number | string): Promise<IssueDetail> {
  return request<IssueDetail>(`/issues/${id}`);
}

export function createIssue(
  data: Omit<Issue, 'id' | 'created_at'>,
): Promise<Issue> {
  return request<Issue>('/issues', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateIssue(
  id: number | string,
  data: Omit<Issue, 'id' | 'created_at'>,
): Promise<Issue> {
  return request<Issue>(`/issues/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deleteIssue(id: number | string): Promise<void> {
  return request<void>(`/issues/${id}`, { method: 'DELETE' });
}

// ── Statements ──────────────────────────────────────────────

export interface StatementQueryParams {
  politician_id?: number | string;
  issue_id?: number | string;
  platform?: string;
  search?: string;
  skip?: number;
  limit?: number;
  sort?: string;
}

export function fetchStatements(
  params?: StatementQueryParams,
): Promise<PaginatedResponse<Statement>> {
  const query = new URLSearchParams();
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== '') {
        query.set(key, String(value));
      }
    }
  }
  const qs = query.toString();
  return request<PaginatedResponse<Statement>>(
    `/statements${qs ? `?${qs}` : ''}`,
  );
}

export function fetchStatement(id: number | string): Promise<Statement> {
  return request<Statement>(`/statements/${id}`);
}

export function createStatement(data: {
  politician_id: number;
  issue_ids: number[];
  title: string;
  analysis: string;
  post_url: string;
  post_platform: string;
  post_content?: string | null;
  screenshot_url?: string | null;
  post_date?: string | null;
  sources?: { source_type: string; title: string; url: string; description: string }[];
}): Promise<Statement> {
  return request<Statement>('/statements', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateStatement(
  id: number | string,
  data: {
    politician_id: number;
    issue_ids: number[];
    title: string;
    analysis: string;
    post_url: string;
    post_platform: string;
    post_content?: string | null;
    screenshot_url?: string | null;
    post_date?: string | null;
    sources?: { source_type: string; title: string; url: string; description: string }[];
  },
): Promise<Statement> {
  return request<Statement>(`/statements/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deleteStatement(id: number | string): Promise<void> {
  return request<void>(`/statements/${id}`, { method: 'DELETE' });
}

// ── Upload ──────────────────────────────────────────────────

export async function uploadFile(file: File): Promise<{ url: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const headers: Record<string, string> = {};
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  const res = await fetch(`${API_BASE}/uploads`, {
    method: 'POST',
    headers,
    body: formData,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`Upload error ${res.status}: ${body}`);
  }
  return res.json();
}

// ── Export / Import ──────────────────────────────────────────

export function exportData(): Promise<unknown> {
  return request<unknown>('/export');
}

export function importData(
  data: unknown,
): Promise<{ message: string; imported: Record<string, number> }> {
  return request<{ message: string; imported: Record<string, number> }>(
    '/import',
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
  );
}
