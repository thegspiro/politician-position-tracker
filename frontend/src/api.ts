import type {
  Politician,
  PoliticianDetail,
  Issue,
  IssueDetail,
  Statement,
} from './types';

const API_BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`API error ${res.status}: ${body}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

// ── Politicians ──────────────────────────────────────────────

export function fetchPoliticians(): Promise<Politician[]> {
  return request<Politician[]>('/politicians');
}

export function fetchPolitician(id: number | string): Promise<PoliticianDetail> {
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
  data: Partial<Omit<Politician, 'id' | 'created_at' | 'updated_at'>>,
): Promise<Politician> {
  return request<Politician>(`/politicians/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deletePolitician(id: number | string): Promise<void> {
  return request<void>(`/politicians/${id}`, { method: 'DELETE' });
}

// ── Issues ───────────────────────────────────────────────────

export function fetchIssues(): Promise<Issue[]> {
  return request<Issue[]>('/issues');
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
  data: Partial<Omit<Issue, 'id' | 'created_at'>>,
): Promise<Issue> {
  return request<Issue>(`/issues/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deleteIssue(id: number | string): Promise<void> {
  return request<void>(`/issues/${id}`, { method: 'DELETE' });
}

// ── Statements ───────────────────────────────────────────────

export interface StatementQueryParams {
  politician_id?: number | string;
  issue_id?: number | string;
  platform?: string;
  search?: string;
}

export function fetchStatements(
  params?: StatementQueryParams,
): Promise<Statement[]> {
  const query = new URLSearchParams();
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== '') {
        query.set(key, String(value));
      }
    }
  }
  const qs = query.toString();
  return request<Statement[]>(`/statements${qs ? `?${qs}` : ''}`);
}

export function fetchStatement(id: number | string): Promise<Statement> {
  return request<Statement>(`/statements/${id}`);
}

export function createStatement(
  data: Omit<Statement, 'id' | 'created_at' | 'updated_at' | 'politician' | 'issue' | 'sources'> & {
    sources?: { title: string; url: string; description: string }[];
  },
): Promise<Statement> {
  return request<Statement>('/statements', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateStatement(
  id: number | string,
  data: Partial<
    Omit<Statement, 'id' | 'created_at' | 'updated_at' | 'politician' | 'issue' | 'sources'> & {
      sources?: { title: string; url: string; description: string }[];
    }
  >,
): Promise<Statement> {
  return request<Statement>(`/statements/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deleteStatement(id: number | string): Promise<void> {
  return request<void>(`/statements/${id}`, { method: 'DELETE' });
}
