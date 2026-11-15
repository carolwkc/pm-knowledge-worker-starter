import type {
  FeedbackCreate,
  FeedbackFilter,
  FeedbackRecord,
  FeedbackReceipt,
  FeedbackSummary,
} from './api';

export interface FeedbackSubmission {
  body: FeedbackCreate;
  status: 'pending' | 'uncertain' | 'saved' | 'conflict';
  receipt?: FeedbackReceipt;
}
export interface FeedbackState {
  records: FeedbackSummary[];
  selected: FeedbackRecord | null;
  rating: FeedbackFilter;
  offset: number;
  hasMore: boolean;
  loaded: boolean;
}
export const emptyFeedback = (): FeedbackState => ({
  records: [],
  selected: null,
  rating: 'all',
  offset: 0,
  hasMore: false,
  loaded: false,
});

export const reasonLabel = (reason: string | null) =>
  ({
    missing_evidence: 'Missing evidence',
    irrelevant_evidence: 'Irrelevant evidence',
    other: 'Other',
  })[reason ?? ''] ?? '';

export function validReceipt(
  receipt: FeedbackReceipt,
  workspace: string,
  submission: string,
): boolean {
  return (
    !!receipt &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(receipt.id) &&
    receipt.workspace_id === workspace &&
    receipt.submission_id === submission &&
    typeof receipt.created_at === 'string' &&
    Number.isFinite(Date.parse(receipt.created_at))
  );
}
