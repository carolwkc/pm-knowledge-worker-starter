import type { SourceRef, SourceSummary } from './api';
import type { BrowserState } from './useKnowledge';

function Pages({
  offset,
  hasMore,
  busy,
  onPage,
}: {
  offset: number;
  hasMore: boolean;
  busy: boolean;
  onPage: (offset: number) => void;
}) {
  return (
    <div className="page-controls">
      <button
        className="quiet-button"
        disabled={busy || offset === 0}
        onClick={() => onPage(Math.max(0, offset - 20))}
      >
        Previous
      </button>
      <span>Page {Math.floor(offset / 20) + 1}</span>
      <button
        className="quiet-button"
        disabled={busy || !hasMore}
        onClick={() => onPage(offset + 20)}
      >
        Next
      </button>
    </div>
  );
}

export function SourceBrowser({
  browser,
  busy,
  versionId,
  onCatalogue,
  onHistory,
  onVersion,
  onFilter,
}: {
  browser: BrowserState;
  busy: boolean;
  versionId?: string;
  onCatalogue: (title: string, offset: number) => void;
  onHistory: (source: SourceSummary, offset: number, openLatest: boolean) => void;
  onVersion: (ref: SourceRef) => void;
  onFilter: (title: string) => void;
}) {
  const title = browser.filterDraft;
  return (
    <section className="browser-panel" aria-labelledby="browser-heading">
      <h1 id="browser-heading">Browse original sources</h1>
      <p className="lead">
        Explore your workspace’s documents and their immutable version history.
      </p>
      <section aria-label="Source catalogue">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onCatalogue(title, 0);
          }}
        >
          <label htmlFor="title-filter">Filter by title</label>
          <input
            id="title-filter"
            value={title}
            onChange={(event) => onFilter(event.target.value)}
            maxLength={200}
          />
          <div className="browser-actions">
            <button type="submit" disabled={busy}>
              Apply filter
            </button>
            <button
              className="quiet-button"
              type="button"
              disabled={busy}
              onClick={() => {
                onFilter('');
                onCatalogue('', 0);
              }}
            >
              Clear
            </button>
            <button
              className="quiet-button"
              type="button"
              disabled={busy}
              onClick={() => onCatalogue(browser.title, 0)}
            >
              Refresh
            </button>
          </div>
        </form>
        {browser.title && (
          <p className="small-print">Showing titles containing “{browser.title}”.</p>
        )}
        <ul className="source-list">
          {browser.sources.map((source) => (
            <li key={source.source_document_id}>
              <button
                className="citation-button"
                aria-label={`Open ${source.title}`}
                aria-pressed={browser.selected?.source_document_id === source.source_document_id}
                onClick={() => onHistory(source, 0, true)}
              >
                <span>
                  {source.title}
                  <small>
                    Version {source.latest_version_number} · Ingested {source.latest_ingested_at}
                  </small>
                </span>
              </button>
            </li>
          ))}
        </ul>
        {browser.loaded && !browser.sources.length && (
          <p role="status">
            {browser.title
              ? 'No titles match this filter.'
              : browser.offset
                ? 'No documents on this page. Go to the previous page or refresh.'
                : 'No documents yet. Ask an editor to upload a source.'}
          </p>
        )}
        <Pages
          offset={browser.offset}
          hasMore={browser.hasMore}
          busy={busy}
          onPage={(offset) => onCatalogue(browser.title, offset)}
        />
      </section>
      {browser.selected && (
        <section className="version-history" aria-label="Version history">
          <h2>Version history</h2>
          <p>{browser.selected.title}</p>
          <ul className="source-list">
            {browser.versions.map((version) => (
              <li key={version.document_version_id}>
                <button
                  className="citation-button"
                  aria-label={`Open version ${version.version_number}`}
                  aria-pressed={versionId === version.document_version_id}
                  onClick={() => onVersion(version)}
                >
                  <span>
                    Version {version.version_number}
                    {version.source_is_latest ? ' · Latest' : ' · Historical'}
                    <small>Ingested {version.ingested_at}</small>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {!busy && browser.versionsLoaded && !browser.versions.length && (
            <p>No versions on this page.</p>
          )}
          <Pages
            offset={browser.versionOffset}
            hasMore={browser.versionsHasMore}
            busy={busy}
            onPage={(offset) => onHistory(browser.selected!, offset, false)}
          />
        </section>
      )}
    </section>
  );
}
