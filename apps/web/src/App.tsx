import { useState } from 'react';
import type { RetrievalMode } from './api';
import { SourcePanel } from './SourcePanel';
import { SourceBrowser } from './SourceBrowser';
import { DecisionBrowser } from './DecisionBrowser';
import { UploadForm } from './UploadForm';
import { FeedbackForm } from './FeedbackForm';
import { FeedbackBrowser } from './FeedbackBrowser';
import { useKnowledge } from './useKnowledge';

export default function App() {
  const desk = useKnowledge();
  const [token, setToken] = useState('');
  const selected = desk.workspaces.find((w) => w.id === desk.workspaceId);
  const status =
    desk.busy === 'connect'
      ? 'Connecting…'
      : desk.busy === 'ask'
        ? 'Finding source evidence…'
        : desk.busy === 'source'
          ? 'Opening the source…'
          : desk.busy === 'catalogue'
            ? 'Loading source catalogue…'
            : desk.busy === 'history'
              ? 'Loading version history…'
              : desk.busy === 'records'
                ? 'Loading knowledge records…'
                : desk.busy === 'detail'
                  ? 'Opening the record and its evidence…'
                  : desk.busy === 'generate'
                    ? 'Generating source quotations…'
                    : desk.busy === 'review'
                      ? 'Recording your review…'
                      : desk.busy === 'upload'
                        ? 'Saving your source and opening its evidence…'
                        : desk.busy === 'feedback'
                          ? 'Saving feedback…'
                          : '';

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <header className="app-header">
        <div className="brand">
          <span className="brand-icon" aria-hidden="true">
            k<span>·</span>
          </span>
          <span>PM Knowledge Worker</span>
        </div>
        {desk.user ? (
          <div className="identity">
            <span>{desk.user.name}</span>
            <button className="quiet-button" onClick={() => desk.disconnect()}>
              Disconnect
            </button>
          </div>
        ) : (
          <span className="header-note">Your team’s evidence, in context</span>
        )}
      </header>
      <main id="main">
        {!desk.user ? (
          <section className="connection-layout">
            <div className="intro">
              <h1>Good questions deserve original sources.</h1>
              <p>
                Ask about your team’s product knowledge. Read the evidence, then follow each
                citation back to its context.
              </p>
              <div className="evidence-motif" aria-hidden="true">
                <span>Question</span>
                <i />
                <span>Evidence</span>
                <i />
                <span>Original source</span>
              </div>
            </div>
            <div className="connection-panel">
              <h2>Connect to your workspace</h2>
              <p>Use the API token supplied by your operator.</p>
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  const submitted = token.trim();
                  setToken('');
                  if (submitted) void desk.connect(submitted);
                }}
              >
                <label htmlFor="token">API token</label>
                <input
                  id="token"
                  type="password"
                  autoComplete="off"
                  spellCheck={false}
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                  required
                  disabled={desk.busy === 'connect'}
                />
                <button type="submit" disabled={!token.trim() || desk.busy === 'connect'}>
                  {desk.busy === 'connect' ? 'Connecting…' : 'Connect'}
                </button>
              </form>
              <p className="small-print">
                Your token stays in this tab’s memory. Refreshing the page disconnects you.
              </p>
            </div>
          </section>
        ) : (
          <>
            <div className="workspace-bar">
              <div>
                <label htmlFor="workspace">Workspace</label>
                <select
                  id="workspace"
                  value={desk.workspaceId}
                  onChange={(event) => desk.selectWorkspace(event.target.value)}
                  disabled={!desk.workspaces.length}
                >
                  {!desk.workspaces.length && <option value="">No workspaces available</option>}
                  {desk.workspaces.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name}
                    </option>
                  ))}
                </select>
              </div>
              {selected && <span className="role-label">{selected.role} access</span>}
            </div>
            {desk.workspaces.length > 0 && (
              <nav className="view-navigation" aria-label="Workspace views">
                {selected?.role === 'owner' && (
                  <button
                    className="quiet-button"
                    aria-pressed={desk.view === 'feedback'}
                    onClick={() => desk.selectView('feedback')}
                  >
                    Feedback
                  </button>
                )}
                <button
                  className="quiet-button"
                  aria-pressed={desk.view === 'ask'}
                  onClick={() => desk.selectView('ask')}
                >
                  Ask
                </button>
                <button
                  className="quiet-button"
                  aria-pressed={desk.view === 'browse'}
                  onClick={() => desk.selectView('browse')}
                >
                  Browse sources
                </button>
                <button
                  className="quiet-button"
                  aria-pressed={desk.view === 'decisions'}
                  onClick={() => desk.selectView('decisions')}
                >
                  Decisions
                </button>
                {selected && selected.role !== 'reader' && (
                  <button
                    className="quiet-button"
                    aria-pressed={desk.view === 'proposals'}
                    onClick={() => desk.selectView('proposals')}
                  >
                    Review queue
                  </button>
                )}
              </nav>
            )}
            {!desk.workspaces.length ? (
              <section className="empty-workspace">
                <h1>No workspaces yet</h1>
                <p>
                  Ask your operator to add you to a workspace, then disconnect and connect again.
                </p>
              </section>
            ) : (
              <div className="desk-layout">
                {desk.view === 'feedback' ? (
                  <FeedbackBrowser desk={desk} />
                ) : desk.view === 'decisions' || desk.view === 'proposals' ? (
                  <DecisionBrowser desk={desk} />
                ) : desk.view === 'browse' ? (
                  <SourceBrowser
                    key={desk.workspaceId}
                    browser={desk.browser}
                    onFilter={desk.setTitleFilter}
                    busy={desk.busy !== null}
                    versionId={desk.source?.version.document_version_id}
                    onCatalogue={(title, offset) => void desk.loadCatalogue(title, offset)}
                    onHistory={(source, offset, openLatest) =>
                      void desk.loadHistory(source, offset, openLatest)
                    }
                    onVersion={(ref) => void desk.openVersion(ref)}
                    upload={
                      <section className="upload-panel" aria-label="Source uploads">
                        {desk.canUpload && !desk.uploadTarget && (
                          <div className="browser-actions">
                            <button
                              disabled={desk.busy !== null}
                              onClick={() => desk.openUpload(null)}
                            >
                              Add source
                            </button>
                            {desk.browser.selected && (
                              <button
                                className="quiet-button"
                                disabled={desk.busy !== null}
                                onClick={() => desk.openUpload(desk.browser.selected)}
                              >
                                Upload new version
                              </button>
                            )}
                          </div>
                        )}
                        {desk.canUpload && desk.uploadTarget && (
                          <UploadForm
                            destination={desk.uploadTarget.source?.title ?? null}
                            busy={desk.busy !== null}
                            onSubmit={(input) => void desk.submitUpload(input)}
                            onCancel={desk.cancelUpload}
                          />
                        )}
                        {desk.uploadReceipt && (
                          <div className="upload-receipt" role="status">
                            <p>
                              {desk.uploadReceipt.duplicate
                                ? 'Existing content reused'
                                : 'Source saved'}
                              : version {desk.uploadReceipt.version_number}.
                            </p>
                            <p className="small-print">
                              Source ID: {desk.uploadReceipt.source_document_id}
                              <br />
                              Version ID: {desk.uploadReceipt.document_version_id}
                              <br />
                              SHA-256: {desk.uploadReceipt.sha256}
                              <br />
                              Chunks: {desk.uploadReceipt.chunk_count}
                            </p>
                            {desk.uploadReceipt.duplicate && (
                              <p className="small-print">
                                Reusing historical content does not make it the latest version.
                              </p>
                            )}
                          </div>
                        )}
                        {desk.uploadUncertain && (
                          <button
                            className="quiet-button"
                            disabled={desk.busy !== null}
                            onClick={() => void desk.loadCatalogue('', 0)}
                          >
                            Inspect source catalogue
                          </button>
                        )}
                      </section>
                    }
                  />
                ) : (
                  <section className="question-panel" aria-labelledby="question-heading">
                    <h1 id="question-heading">What would you like to understand?</h1>
                    <p className="lead">
                      Find the source evidence behind your team’s product decisions.
                    </p>
                    <form
                      aria-label="Ask your workspace"
                      onSubmit={(event) => {
                        event.preventDefault();
                        void desk.ask();
                      }}
                    >
                      <label htmlFor="question">Your question</label>
                      <textarea
                        id="question"
                        value={desk.question}
                        onChange={(event) => desk.setQuestion(event.target.value)}
                        maxLength={1000}
                        required
                        rows={3}
                        placeholder="Why was troubleshooting acceleration prioritised?"
                        aria-describedby="question-help"
                      />
                      <div className="question-options">
                        <div>
                          <label htmlFor="mode">Retrieval mode</label>
                          <select
                            id="mode"
                            value={desk.mode}
                            onChange={(event) => desk.setMode(event.target.value as RetrievalMode)}
                          >
                            <option value="keyword">Keyword</option>
                            <option value="semantic">Semantic</option>
                            <option value="hybrid">Hybrid</option>
                          </select>
                        </div>
                        <button
                          type="submit"
                          disabled={!desk.question.trim() || desk.busy === 'ask'}
                        >
                          Ask question
                        </button>
                      </div>
                      <p id="question-help" className="small-print">
                        Answers quote your sources directly. Semantic and hybrid modes require local
                        embeddings to be enabled.
                      </p>
                    </form>
                    {desk.answer ? (
                      <section className="answer" aria-labelledby="answer-heading">
                        <div className="answer-heading">
                          <h2 id="answer-heading">
                            {desk.answer.status === 'grounded'
                              ? 'Quoted source evidence'
                              : 'Insufficient evidence'}
                          </h2>
                          <span className="answer-status">
                            {desk.answer.status === 'grounded'
                              ? `${desk.answer.sources.length} cited ${desk.answer.sources.length === 1 ? 'excerpt' : 'excerpts'}`
                              : 'No matching excerpts'}
                          </span>
                        </div>
                        <p className="answer-text">{desk.answer.answer}</p>
                        {desk.answer.sources.length > 0 && (
                          <>
                            <p className="small-print">
                              Matching text is evidence from a source; it may not fully answer your
                              question or establish that the source is correct.
                            </p>
                            <h3>Inspect the sources</h3>
                            <ul className="citation-list">
                              {desk.answer.sources.map((c) => (
                                <li key={c.citation}>
                                  <button
                                    className="citation-button"
                                    aria-label={`[${c.citation}] ${c.title}`}
                                    aria-pressed={desk.source?.citation?.chunk_id === c.chunk_id}
                                    onClick={() => void desk.openSource(c)}
                                  >
                                    <span className="citation-number">[{c.citation}]</span>
                                    <span>
                                      {c.title}
                                      <small>Open original context</small>
                                    </span>
                                    <span aria-hidden="true">↗</span>
                                  </button>
                                </li>
                              ))}
                            </ul>
                          </>
                        )}
                        {desk.answerContext && (
                          <FeedbackForm
                            key={desk.answerContext.submission_id}
                            submission={desk.feedbackSubmission}
                            busy={desk.busy !== null}
                            onSubmit={(draft) => void desk.submitFeedback(draft)}
                            onRetry={() => void desk.submitFeedback()}
                          />
                        )}
                      </section>
                    ) : (
                      <div className="answer-placeholder">
                        <h2>Start with a question</h2>
                        <p>Matching excerpts will appear here, with citations you can inspect.</p>
                      </div>
                    )}
                  </section>
                )}
                <div>
                  <SourcePanel
                    source={desk.source}
                    loading={
                      desk.busy === 'source' || desk.busy === 'history' || desk.busy === 'detail'
                    }
                    browsing={desk.view === 'browse'}
                    context={
                      desk.view === 'proposals'
                        ? 'proposal'
                        : desk.view === 'decisions'
                          ? 'decision'
                          : undefined
                    }
                  />
                  {desk.view === 'browse' && desk.source && selected?.role !== 'reader' && (
                    <section className="generation-panel" aria-label="Proposal generation">
                      <p>
                        Generate decision proposals as exact source quotations. Nothing is approved
                        automatically.
                      </p>
                      <button
                        disabled={desk.busy !== null || !desk.source.version.source_is_latest}
                        onClick={() => void desk.generate()}
                      >
                        Generate proposals
                      </button>
                      {!desk.source.version.source_is_latest && (
                        <p className="notice">Open the latest version to generate proposals.</p>
                      )}
                      {desk.generated && (
                        <>
                          <p role="status">{desk.generated}</p>
                          <button
                            className="quiet-button"
                            onClick={() => desk.selectView('proposals')}
                          >
                            Open review queue
                          </button>
                        </>
                      )}
                    </section>
                  )}
                </div>
              </div>
            )}
          </>
        )}
        <div className="feedback" aria-live="polite" role="status">
          {status}
        </div>
        {desk.error && (
          <div className="error global-error" role="alert">
            {desk.error}
            {desk.retry && (
              <button className="quiet-button retry-button" onClick={desk.retry}>
                Retry
              </button>
            )}
          </div>
        )}
      </main>
      <footer>Evidence first. Human judgment always.</footer>
    </div>
  );
}
