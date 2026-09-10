import type {
  Politician,
  PoliticianDetail,
  Issue,
  IssueDetail,
  Statement,
  SourcePayload,
  StatementCitations,
  StatementSort,
  User,
  PaginatedResponse,
} from './types';

interface StatementPayload {
  politician_id: number;
  issue_ids: number[];
  title: string;
  analysis: string;
  post_url: string;
  post_platform: string;
  post_content?: string | null;
  screenshot_url?: string | null;
  post_date?: string | null;
  sources?: SourcePayload[];
}

const API_BASE = '/api';

// ── Auth token management ───────────────────────────────────

const TOKEN_KEY = 'auth_token';
const TOKEN_EXPIRY_KEY = 'auth_token_expires_at';

let authToken: string | null = localStorage.getItem(TOKEN_KEY);

/** Epoch milliseconds at which the stored token stops being accepted. */
function storedExpiry(): number | null {
  const raw = localStorage.getItem(TOKEN_EXPIRY_KEY);
  if (!raw) return null;
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

/**
 * Sessions now expire server-side. Dropping a token the moment it lapses means
 * the admin sees the login screen instead of a wall of failed requests.
 */
function tokenHasExpired(): boolean {
  const expiry = storedExpiry();
  return expiry !== null && Date.now() >= expiry;
}

export function getToken(): string | null {
  if (authToken && tokenHasExpired()) {
    setToken(null);
  }
  return authToken;
}

export function setToken(token: string | null, expiresIn?: number) {
  authToken = token;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    if (expiresIn !== undefined) {
      localStorage.setItem(
        TOKEN_EXPIRY_KEY,
        String(Date.now() + expiresIn * 1000),
      );
    }
  } else {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_EXPIRY_KEY);
  }
}

export function isLoggedIn(): boolean {
  return getToken() !== null;
}

// ── Request helper ──────────────────────────────────────────

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
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

export interface LoginResponse {
  token: string;
  /** Token lifetime in seconds. */
  expires_in: number;
  username: string;
  role: string;
  display_name: string | null;
}

export function login(
  username: string,
  password: string,
): Promise<LoginResponse> {
  return request<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

// ── Users ───────────────────────────────────────────────────

export interface UserInput {
  username: string;
  password?: string;
  display_name?: string | null;
  role?: string;
  is_active?: boolean;
}

export function fetchCurrentUser(): Promise<User> {
  return request<User>('/users/me');
}

export function fetchUsers(): Promise<User[]> {
  return request<User[]>('/users');
}

export function createUser(data: UserInput): Promise<User> {
  return request<User>('/users', { method: 'POST', body: JSON.stringify(data) });
}

export function updateUser(uid: string, data: UserInput): Promise<User> {
  return request<User>(`/users/${uid}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deleteUser(uid: string): Promise<void> {
  return request<void>(`/users/${uid}`, { method: 'DELETE' });
}

export function changeOwnPassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  return request<void>('/users/me/password', {
    method: 'POST',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
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
  sort?: StatementSort;
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

export function createStatement(data: StatementPayload): Promise<Statement> {
  return request<Statement>('/statements', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateStatement(
  id: number | string,
  data: StatementPayload,
): Promise<Statement> {
  return request<Statement>(`/statements/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export interface ArchiveResponse {
  archive_url: string;
  archived_at: string | null;
}

/** Capture a Wayback snapshot for one source, on demand. */
export function archiveSource(
  statementId: number | string,
  uid: string,
): Promise<ArchiveResponse> {
  return request<ArchiveResponse>(
    `/statements/${statementId}/sources/${uid}/archive`,
    { method: 'POST' },
  );
}

export function fetchStatementCitations(
  id: number | string,
): Promise<StatementCitations> {
  return request<StatementCitations>(`/statements/${id}/citations`);
}

/** Download URLs for a statement's bibliography. */
export function citationExportUrls(id: number | string) {
  return {
    bibtex: `${API_BASE}/statements/${id}/citations.bib`,
    cslJson: `${API_BASE}/statements/${id}/citations.json`,
  };
}

export function deleteStatement(id: number | string): Promise<void> {
  return request<void>(`/statements/${id}`, { method: 'DELETE' });
}

// ── Upload ──────────────────────────────────────────────────

export async function uploadFile(file: File): Promise<{ url: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
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
