import { useEffect, useRef } from 'react';
import type { FeedbackFilter } from './api';
import { reasonLabel } from './feedbackState';
import type { useKnowledge } from './useKnowledge';

export function FeedbackBrowser({ desk }: { desk: ReturnType<typeof useKnowledge> }) {
  const state = desk.feedback;
  const record = state.selected;
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (record) heading.current?.focus();
  }, [record]);
  return (
    <section className="browser-panel" aria-label="Workspace feedback">
      <h1>Q&amp;A feedback</h1>
      <p className="lead">Member opinions and reported context, visible to workspace owners.</p>
      <label htmlFor="feedback-filter">Feedback rating</label>
      <select
        id="feedback-filter"
        value={state.rating}
        disabled={desk.busy !== null}
        onChange={(e) => void desk.loadFeedback(e.target.value as FeedbackFilter)}
      >
        <option value="all">All</option>
        <option value="helpful">Helpful</option>
        <option value="not_helpful">Not helpful</option>
      </select>
      <div className="browser-actions">
        <button disabled={desk.busy !== null} onClick={() => void desk.loadFeedback(state.rating)}>
          Refresh
        </button>
      </div>
      <ul className="source-list">
        {state.records.map((item) => (
          <li key={item.id}>
            <button
              className="citation-button"
              disabled={desk.busy !== null}
              aria-label={`Open feedback ${item.id}`}
              aria-pressed={record?.id === item.id}
              onClick={() => void desk.openFeedback(item.id)}
            >
              <span>
                <span className="record-quote">{item.question}</span>
                <small>
                  {item.rating === 'helpful' ? 'Helpful' : 'Not helpful'}
                  {item.reason ? ` · ${reasonLabel(item.reason)}` : ''}
                </small>
                <small>
                  Submitted by {item.created_by} · {item.created_at}
                </small>
              </span>
            </button>
          </li>
        ))}
      </ul>
      {state.loaded && !state.records.length && <p role="status">No feedback on this page.</p>}
      <div className="page-controls">
        <button
          disabled={desk.busy !== null || state.offset === 0}
          onClick={() => void desk.loadFeedback(state.rating, Math.max(0, state.offset - 20))}
        >
          Previous
        </button>
        <span>Page {Math.floor(state.offset / 20) + 1}</span>
        <button
          disabled={desk.busy !== null || !state.hasMore}
          onClick={() => void desk.loadFeedback(state.rating, state.offset + 20)}
        >
          Next
        </button>
      </div>
      {record && (
        <section aria-labelledby="feedback-context-heading">
          <h2 id="feedback-context-heading" tabIndex={-1} ref={heading}>
            User-reported Q&amp;A context
          </h2>
          <p className="small-print">
            Citations match saved source evidence. This report does not establish that the service
            returned this result for the question.
          </p>
          <h3>Reported question</h3>
          <p>{record.question}</p>
          <p>Retrieval mode: {record.mode}</p>
          <p>
            {record.rating === 'helpful' ? 'Helpful' : 'Not helpful'}
            {record.reason ? ` · ${reasonLabel(record.reason)}` : ''}
          </p>
          <p>
            Submitted by {record.created_by} · {record.created_at}
          </p>
          <h3>Reported answer</h3>
          <p className="answer-text">{record.answer.answer}</p>
          {record.comment && (
            <>
              <h3>Comment</h3>
              <p className="answer-text">{record.comment}</p>
            </>
          )}
          <ul className="citation-list">
            {record.answer.sources.map((citation) => (
              <li key={citation.citation}>
                <button
                  className="citation-button"
                  disabled={desk.busy !== null}
                  aria-label={`[${citation.citation}] ${citation.title}`}
                  onClick={() => void desk.openFeedbackSource(citation)}
                >
                  [{citation.citation}] {citation.title}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}
