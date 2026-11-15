import { useState } from 'react';
import type { RetrievalMode } from './api';
import { SourcePanel } from './SourcePanel';
import { SourceBrowser } from './SourceBrowser';
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
                {desk.view === 'browse' ? (
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
                      </section>
                    ) : (
                      <div className="answer-placeholder">
                        <h2>Start with a question</h2>
                        <p>Matching excerpts will appear here, with citations you can inspect.</p>
                      </div>
                    )}
                  </section>
                )}
                <SourcePanel
                  source={desk.source}
                  loading={desk.busy === 'source' || desk.busy === 'history'}
                  browsing={desk.view === 'browse'}
                />
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
