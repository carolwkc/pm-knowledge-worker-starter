import type { Decision, Proposal, ProposalFilter, ReviewAction, SourceVersion } from './api';
import { evidenceSpan } from './evidence';

export type WorkspaceView = 'ask' | 'browse' | 'decisions' | 'proposals' | 'feedback';
export type KnowledgeRecord = Decision | Proposal;
export interface DecisionState {
  records: KnowledgeRecord[];
  selected: KnowledgeRecord | null;
  status: ProposalFilter;
  offset: number;
  hasMore: boolean;
  loaded: boolean;
  comment: string;
  confirmation: ReviewAction | null;
  unresolved: boolean;
  notice: string;
}
export const emptyDecisions = (): DecisionState => ({
  records: [],
  selected: null,
  status: 'pending',
  offset: 0,
  hasMore: false,
  loaded: false,
  comment: '',
  confirmation: null,
  unresolved: false,
  notice: '',
});

export function verifiedRecord(
  record: KnowledgeRecord,
  version: SourceVersion | undefined,
): boolean {
  const ref = record.evidence;
  return (
    !!version &&
    version.workspace_id === record.workspace_id &&
    version.source_document_id === ref.source_document_id &&
    version.document_version_id === ref.document_version_id &&
    record.statement === ref.excerpt &&
    !!evidenceSpan(version.plain_text, ref.start_char, ref.end_char, ref.excerpt)
  );
}

export function validComment(comment: string): boolean {
  return !comment.includes('\0') && Array.from(comment.trim()).length <= 1000;
}
