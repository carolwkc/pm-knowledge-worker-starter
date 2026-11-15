import { useEffect, useRef } from 'react';
import { evidenceSpan } from './evidence';
import type { OpenSource } from './useKnowledge';

export function SourcePanel({
  source,
  loading,
  browsing = false,
}: {
  source: OpenSource | null;
  loading: boolean;
  browsing?: boolean;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  const mark = useRef<HTMLElement>(null);
  useEffect(() => {
    if (source) {
      heading.current?.focus();
      mark.current?.scrollIntoView?.({ block: 'center' });
    }
  }, [source]);

  if (!source)
    return (
      <aside className="source-panel source-empty" aria-label="Source context">
        <span className="source-symbol" aria-hidden="true">
          [ ]
        </span>
        <h2>Keep the evidence in view</h2>
        <p>
          {loading
            ? 'Opening the source…'
            : browsing
              ? 'Choose a document to inspect its original text and version history.'
              : 'Choose a citation after asking a question to inspect its original text and context.'}
        </p>
      </aside>
    );

  const { version, citation } = source;
  const span = citation
    ? evidenceSpan(version.plain_text, citation.start_char, citation.end_char, citation.excerpt)
    : null;
  return (
    <aside className="source-panel" aria-labelledby="source-heading">
      <div className="panel-heading">
        <span className="section-label">Original source</span>
        <h2 id="source-heading" ref={heading} tabIndex={-1}>
          {version.title}
        </h2>
        <p className="version-label">
          Version {version.version_number}{' '}
          <span className="version-state">
            {version.source_is_latest ? 'Latest version' : 'Historical version'}
          </span>
        </p>
        {!version.source_is_latest && (
          <p className="notice">
            {citation
              ? 'A newer version exists. This is the version cited by the answer.'
              : 'A newer version exists. You are viewing a historical version.'}
          </p>
        )}
      </div>
      {citation && !span && (
        <p className="error" role="alert">
          Citation could not be verified against the original text. No highlight is shown.
        </p>
      )}
      <pre className="source-text" data-testid="source-text">
        {span ? (
          <>
            {span.before}
            <mark ref={mark}>{span.quote}</mark>
            {span.after}
          </>
        ) : (
          version.plain_text
        )}
      </pre>
      <details className="provenance">
        <summary>Source details</summary>
        <dl>
          <dt>Source ID</dt>
          <dd>{version.source_document_id}</dd>
          <dt>Version ID</dt>
          <dd>{version.document_version_id}</dd>
          {citation && (
            <>
              <dt>Chunk ID</dt>
              <dd>{citation.chunk_id}</dd>
              <dt>Character span</dt>
              <dd>
                {citation.start_char}–{citation.end_char} (end exclusive)
              </dd>
            </>
          )}
          <dt>Ingested</dt>
          <dd>{version.ingested_at}</dd>
          <dt>SHA-256</dt>
          <dd>{version.sha256}</dd>
          {version.external_uri && (
            <>
              <dt>External URI</dt>
              <dd>{version.external_uri}</dd>
            </>
          )}
        </dl>
      </details>
    </aside>
  );
}
