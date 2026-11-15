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
export interface Evidence {
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
export interface Citation extends Evidence {
  citation: string;
}
export type ProposalFilter = 'pending' | 'approved' | 'rejected' | 'all';
export type ReviewAction = 'approve' | 'reject';
export interface ReviewWrite {
  action: ReviewAction;
  comment?: string;
}
export interface Proposal {
  id: string;
  workspace_id: string;
  kind: 'decision';
  statement: string;
  evidence: Evidence;
  extraction_method: 'deterministic_source_quotation';
  extractor_version: string;
  created_by: string;
  created_at: string;
  status: Exclude<ProposalFilter, 'all'>;
  review: {
    id: string;
    reviewer_id: string;
    action: ReviewAction;
    comment: string | null;
    created_at: string;
  } | null;
  decision_id: string | null;
}
export interface Decision {
  id: string;
  workspace_id: string;
  proposal_id: string;
  statement: string;
  evidence: Evidence;
  approved_by: string;
  approved_at: string;
  source_is_latest: boolean;
}
export interface Extraction {
  proposals: Proposal[];
  created_count: number;
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
export interface SourceRef {
  source_document_id: string;
  document_version_id: string;
}
export interface SourceSummary {
  workspace_id: string;
  source_document_id: string;
  title: string;
  external_uri: string | null;
  created_at: string;
  latest_version_id: string;
  latest_version_number: number;
  latest_ingested_at: string;
}
export type SourceVersionSummary = Omit<SourceVersion, 'title' | 'external_uri' | 'plain_text'>;
export interface SourceList {
  sources: SourceSummary[];
  has_more: boolean;
}
export interface SourceVersionList {
  versions: SourceVersionSummary[];
  has_more: boolean;
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
  method: 'GET' | 'POST' = body ? 'POST' : 'GET',
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method,
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
  decisions: (token: string, workspace: string, offset: number, signal: AbortSignal) =>
    request<{ decisions: Decision[] }>(
      `${workspacePath(workspace)}/decisions?limit=21&offset=${offset}`,
      token,
      signal,
    ),
  proposals: (
    token: string,
    workspace: string,
    status: ProposalFilter,
    offset: number,
    signal: AbortSignal,
  ) =>
    request<{ proposals: Proposal[] }>(
      `${workspacePath(workspace)}/proposals?status=${status}&limit=21&offset=${offset}`,
      token,
      signal,
    ),
  decision: (token: string, workspace: string, id: string, signal: AbortSignal) =>
    request<Decision>(
      `${workspacePath(workspace)}/decisions/${encodeURIComponent(id)}`,
      token,
      signal,
    ),
  proposal: (token: string, workspace: string, id: string, signal: AbortSignal) =>
    request<Proposal>(
      `${workspacePath(workspace)}/proposals/${encodeURIComponent(id)}`,
      token,
      signal,
    ),
  review: (token: string, workspace: string, id: string, body: ReviewWrite, signal: AbortSignal) =>
    request<Proposal>(
      `${workspacePath(workspace)}/proposals/${encodeURIComponent(id)}/review`,
      token,
      signal,
      body,
    ),
  generate: (token: string, workspace: string, ref: SourceRef, signal: AbortSignal) =>
    request<Extraction>(
      `${workspacePath(workspace)}/sources/${encodeURIComponent(ref.source_document_id)}/versions/${encodeURIComponent(ref.document_version_id)}/proposals`,
      token,
      signal,
      undefined,
      'POST',
    ),
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
  sources: (token: string, workspace: string, title: string, offset: number, signal: AbortSignal) =>
    request<SourceList>(
      `${workspacePath(workspace)}/sources?${new URLSearchParams({ title, offset: String(offset), limit: '20' })}`,
      token,
      signal,
    ),
  versions: (
    token: string,
    workspace: string,
    sourceId: string,
    offset: number,
    signal: AbortSignal,
  ) =>
    request<SourceVersionList>(
      `${workspacePath(workspace)}/sources/${encodeURIComponent(sourceId)}/versions?${new URLSearchParams({ offset: String(offset), limit: '20' })}`,
      token,
      signal,
    ),
  source: (token: string, workspace: string, source: SourceRef, signal: AbortSignal) =>
    request<SourceVersion>(
      `${workspacePath(workspace)}/sources/${encodeURIComponent(source.source_document_id)}/versions/${encodeURIComponent(source.document_version_id)}`,
      token,
      signal,
    ),
};
