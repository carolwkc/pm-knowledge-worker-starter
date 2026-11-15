export type RetrievalMode = 'keyword' | 'semantic' | 'hybrid';
export interface User {
  id: string;
  name: string;
  created_at: string;
}
export interface Workspace {
  id: string;
  name: string;
  role: 'reader' | 'editor' | 'owner';
  created_at: string;
}
export interface Citation {
  citation: string;
  source_document_id: string;
  document_version_id: string;
  chunk_id: string;
  title: string;
  external_uri: string | null;
  ordinal: number;
  excerpt: string;
  start_char: number;
  end_char: number;
}
export interface Answer {
  answer: string;
  status: 'grounded' | 'insufficient_evidence';
  sources: Citation[];
}
export interface SourceVersion {
  workspace_id: string;
  source_document_id: string;
  document_version_id: string;
  title: string;
  external_uri: string | null;
  version_number: number;
  sha256: string;
  ingested_at: string;
  plain_text: string;
  source_is_latest: boolean;
}

export class ApiError extends Error {
  constructor(public status: number) {
    super('API request failed');
  }
}

async function request<T>(
  path: string,
  token: string,
  signal: AbortSignal,
  body?: object,
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method: body ? 'POST' : 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal,
    cache: 'no-store',
    credentials: 'omit',
  });
  // Never surface arbitrary server bodies, which may contain sensitive submitted values.
  if (!response.ok) throw new ApiError(response.status);
  return response.json() as Promise<T>;
}

const workspacePath = (id: string) => `/workspaces/${encodeURIComponent(id)}`;
export const api = {
  me: (token: string, signal: AbortSignal) => request<User>('/me', token, signal),
  workspaces: (token: string, signal: AbortSignal) =>
    request<{ workspaces: Workspace[] }>('/workspaces', token, signal),
  ask: (
    token: string,
    workspace: string,
    question: string,
    mode: RetrievalMode,
    signal: AbortSignal,
  ) => request<Answer>(`${workspacePath(workspace)}/ask`, token, signal, { question, mode }),
  source: (token: string, workspace: string, citation: Citation, signal: AbortSignal) =>
    request<SourceVersion>(
      `${workspacePath(workspace)}/sources/${encodeURIComponent(citation.source_document_id)}/versions/${encodeURIComponent(citation.document_version_id)}`,
      token,
      signal,
    ),
};
