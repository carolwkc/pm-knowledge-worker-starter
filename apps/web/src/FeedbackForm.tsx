import { useState } from 'react';
import type { FeedbackRating, FeedbackReason } from './api';
import type { FeedbackSubmission } from './feedbackState';
import { validComment } from './decisionState';

export interface FeedbackDraft {
  rating: FeedbackRating;
  reason?: FeedbackReason;
  comment?: string;
}
export function FeedbackForm({
  submission,
  busy,
  onSubmit,
  onRetry,
}: {
  submission: FeedbackSubmission | null;
  busy: boolean;
  onSubmit: (draft: FeedbackDraft) => void;
  onRetry: () => void;
}) {
  const [rating, setRating] = useState<FeedbackRating | ''>('');
  const [reason, setReason] = useState<FeedbackReason | ''>('');
  const [comment, setComment] = useState('');
  if (submission?.status === 'saved')
    return (
      <section aria-label="Answer feedback">
        <p role="status">Feedback saved. Receipt: {submission.receipt?.id}</p>
      </section>
    );
  if (submission)
    return (
      <section aria-label="Answer feedback">
        <p role="status">
          {submission.status === 'pending'
            ? 'Saving feedback…'
            : submission.status === 'conflict'
              ? 'This submission identifier is already used. Feedback cannot be resubmitted for this answer.'
              : 'Feedback outcome uncertain. Your submission is preserved; retry to discover or save the same feedback.'}
        </p>
        {submission.status === 'uncertain' && (
          <button disabled={busy} onClick={onRetry}>
            Retry feedback submission
          </button>
        )}
      </section>
    );
  return (
    <form
      className="feedback-form"
      aria-label="Answer feedback"
      onSubmit={(event) => {
        event.preventDefault();
        if (!rating || !validComment(comment) || busy) return;
        onSubmit({
          rating,
          ...(rating === 'not_helpful' && reason ? { reason } : {}),
          ...(comment.trim() ? { comment: comment.trim() } : {}),
        });
      }}
    >
      <fieldset disabled={busy}>
        <legend>Was this result helpful?</legend>
        <label>
          <input
            type="radio"
            name="feedback-rating"
            checked={rating === 'helpful'}
            onChange={() => {
              setRating('helpful');
              setReason('');
            }}
          />{' '}
          Helpful
        </label>
        <label>
          <input
            type="radio"
            name="feedback-rating"
            checked={rating === 'not_helpful'}
            onChange={() => setRating('not_helpful')}
          />{' '}
          Not helpful
        </label>
        {rating === 'not_helpful' && (
          <>
            <label htmlFor="feedback-reason">Reason (optional)</label>
            <select
              id="feedback-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value as FeedbackReason | '')}
            >
              <option value="">No reason selected</option>
              <option value="missing_evidence">Missing evidence</option>
              <option value="irrelevant_evidence">Irrelevant evidence</option>
              <option value="other">Other</option>
            </select>
          </>
        )}
        <label htmlFor="feedback-comment">Feedback comment (optional)</label>
        <textarea
          id="feedback-comment"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={3}
          aria-describedby="feedback-help"
        />
        {!validComment(comment) && (
          <p role="alert">Use at most 1,000 Unicode characters without NUL characters.</p>
        )}
        <p id="feedback-help" className="small-print">
          Submitting saves this question, answer, citations and comment for workspace owners.
          Feedback is your opinion and does not change approved knowledge.
        </p>
        <button type="submit" disabled={!rating || !validComment(comment) || busy}>
          Submit feedback
        </button>
      </fieldset>
    </form>
  );
}
