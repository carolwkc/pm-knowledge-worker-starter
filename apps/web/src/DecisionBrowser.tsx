import { useEffect, useRef } from 'react';
import type { ProposalFilter } from './api';
import { validComment } from './decisionState';
import type { useKnowledge } from './useKnowledge';

export function DecisionBrowser({ desk }: { desk: ReturnType<typeof useKnowledge> }) {
  const queue = desk.view === 'proposals';
  const state = desk.decisions;
  const record = state.selected;
  const proposal = record && 'status' in record ? record : null;
  const decision = record && 'approved_by' in record ? record : null;
  const owner = desk.workspaces.find((w) => w.id === desk.workspaceId)?.role === 'owner';
  const heading = useRef<HTMLHeadingElement>(null);
  const confirmation = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (record) heading.current?.focus();
  }, [record]);
  useEffect(() => {
    if (state.confirmation) confirmation.current?.focus();
  }, [state.confirmation]);
  return (
    <section
      className="browser-panel decision-browser"
      aria-label={queue ? 'Proposal workspace' : 'Decision workspace'}
    >
      <h1>{queue ? 'Review proposed decisions' : 'Approved decisions'}</h1>
      <p className="lead">
        {queue
          ? 'Proposals quote original sources. Owners decide which quotations to publish.'
          : 'Human-approved source quotations, with their original evidence and attribution.'}
      </p>
      <section aria-label={queue ? 'Proposal catalogue' : 'Decision catalogue'}>
        {queue && (
          <>
            <label htmlFor="proposal-status">Proposal status</label>
            <select
              id="proposal-status"
              value={state.status}
              disabled={desk.busy !== null}
              onChange={(e) => void desk.loadRecords(e.target.value as ProposalFilter)}
            >
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="all">All</option>
            </select>
          </>
        )}
        <div className="browser-actions">
          <button
            className="quiet-button"
            disabled={desk.busy !== null}
            onClick={() => void desk.loadRecords(state.status)}
          >
            Refresh
          </button>
        </div>
        <ul className="source-list">
          {state.records.map((item) => (
            <li key={item.id}>
              <button
                className="citation-button"
                aria-label={`Open ${queue ? 'proposal' : 'decision'} ${item.id}`}
                aria-pressed={record?.id === item.id}
                onClick={() => void desk.openRecord(item.id)}
              >
                <span>
                  <span className="record-quote">{item.statement}</span>
                  <small>{item.evidence.title}</small>
                  <small>
                    {'status' in item
                      ? `Status: ${item.status}`
                      : `Approved ${item.approved_at} · ${item.source_is_latest ? 'Latest evidence' : 'Historical evidence'}`}
                  </small>
                  {'approved_by' in item && <small>Approved by {item.approved_by}</small>}
                </span>
              </button>
            </li>
          ))}
        </ul>
        {state.loaded && !state.records.length && (
          <p role="status">
            {queue
              ? state.offset
                ? 'No proposals on this page.'
                : `No ${state.status === 'all' ? '' : state.status + ' '}proposals.`
              : state.offset
                ? 'No decisions on this page.'
                : 'No approved decisions yet.'}
          </p>
        )}
        <div className="page-controls">
          <button
            className="quiet-button"
            disabled={desk.busy !== null || state.offset === 0}
            onClick={() => void desk.loadRecords(state.status, Math.max(0, state.offset - 20))}
          >
            Previous
          </button>
          <span>Page {Math.floor(state.offset / 20) + 1}</span>
          <button
            className="quiet-button"
            disabled={desk.busy !== null || !state.hasMore}
            onClick={() => void desk.loadRecords(state.status, state.offset + 20)}
          >
            Next
          </button>
        </div>
      </section>
      {record && (
        <section className="record-detail" aria-labelledby="record-heading">
          <h2 id="record-heading" tabIndex={-1} ref={heading}>
            {proposal ? 'Decision proposal' : 'Approved decision'}
          </h2>
          <p className="small-print">
            Exact source quotation. Review records human judgment, not factual truth.
          </p>
          <blockquote className="record-quote">{record.statement}</blockquote>
          <dl className="record-metadata">
            <dt>Record ID</dt>
            <dd>{record.id}</dd>
            <dt>Source</dt>
            <dd>{record.evidence.title}</dd>
            {proposal && (
              <>
                <dt>Status</dt>
                <dd>{proposal.status}</dd>
                <dt>Proposed by</dt>
                <dd>{proposal.created_by}</dd>
                <dt>Proposed at</dt>
                <dd>{proposal.created_at}</dd>
                <dt>Extraction</dt>
                <dd>
                  {proposal.extraction_method} · {proposal.extractor_version}
                </dd>
              </>
            )}
            {decision && (
              <>
                <dt>Approved by</dt>
                <dd>{decision.approved_by}</dd>
                <dt>Approved at</dt>
                <dd>{decision.approved_at}</dd>
                <dt>Evidence freshness at decision read</dt>
                <dd>{decision.source_is_latest ? 'Latest evidence' : 'Historical evidence'}</dd>
              </>
            )}
            {proposal?.review && (
              <>
                <dt>Reviewed by</dt>
                <dd>{proposal.review.reviewer_id}</dd>
                <dt>Reviewed at</dt>
                <dd>{proposal.review.created_at}</dd>
                <dt>Review action</dt>
                <dd>{proposal.review.action}</dd>
                {proposal.review.comment !== null && (
                  <>
                    <dt>Review comment</dt>
                    <dd className="record-quote">{proposal.review.comment}</dd>
                  </>
                )}
              </>
            )}
          </dl>
          {proposal?.decision_id && (
            <button
              className="quiet-button"
              onClick={() => void desk.openRecord(proposal.decision_id!, 'decisions')}
            >
              Open published decision
            </button>
          )}
          {proposal?.status === 'pending' && owner && (
            <div className="review-form">
              {!desk.canApprove && (
                <p className="notice">
                  Approval requires verified matching evidence from the latest source version.
                </p>
              )}
              {state.unresolved && (
                <p className="notice">Reload the proposal and its evidence before reviewing.</p>
              )}
              <label htmlFor="review-comment">Review comment</label>
              <textarea
                id="review-comment"
                value={state.comment}
                disabled={desk.busy !== null || state.unresolved}
                onChange={(e) => desk.setReviewComment(e.target.value)}
                aria-describedby="comment-help"
              />
              <p className="small-print" id="comment-help">
                Optional. Up to 1,000 Unicode characters; no NUL characters.
              </p>
              {!validComment(state.comment) && (
                <p className="error" role="alert">
                  Use at most 1,000 characters without NUL characters.
                </p>
              )}
              <div className="browser-actions">
                <button
                  disabled={!desk.canApprove || desk.busy !== null || !validComment(state.comment)}
                  onClick={() => desk.prepareReview('approve')}
                >
                  Approve
                </button>
                <button
                  className="quiet-button"
                  disabled={!desk.canReview || desk.busy !== null || !validComment(state.comment)}
                  onClick={() => desk.prepareReview('reject')}
                >
                  Reject
                </button>
              </div>
              {state.confirmation && (
                <section className="review-confirmation" aria-labelledby="confirm-heading">
                  <h3 id="confirm-heading" ref={confirmation} tabIndex={-1}>
                    Confirm {state.confirmation}
                  </h3>
                  <p>
                    {state.confirmation === 'approve'
                      ? 'This quotation will become a workspace decision visible to all members.'
                      : 'This proposal will be rejected. No decision will be published.'}
                  </p>
                  <blockquote className="record-quote">{proposal.statement}</blockquote>
                  <p className="record-quote">{state.comment.trim() || 'No review comment.'}</p>
                  <div className="browser-actions">
                    <button disabled={desk.busy !== null} onClick={() => void desk.submitReview()}>
                      Confirm {state.confirmation}
                    </button>
                    <button className="quiet-button" onClick={desk.cancelReview}>
                      Cancel
                    </button>
                  </div>
                </section>
              )}
            </div>
          )}
        </section>
      )}
      {state.notice && (
        <p className="notice" role="status">
          {state.notice}
        </p>
      )}
    </section>
  );
}
