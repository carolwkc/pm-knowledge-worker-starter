import { useState } from 'react';
import type { UploadSourceInput } from './api';

export function UploadForm({
  destination,
  busy,
  onSubmit,
  onCancel,
}: {
  destination: string | null;
  busy: boolean;
  onSubmit: (input: UploadSourceInput) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState('');
  const [uri, setUri] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const label = destination === null ? 'Upload source' : 'Upload version';
  return (
    <form
      aria-label={label}
      className="upload-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (busy) return;
        const name = title.trim();
        const external_uri = uri.trim();
        let message = '';
        if (!file) message = 'Choose a source file.';
        else if (!/\.(md|markdown|txt)$/i.test(file.name))
          message = 'Choose a Markdown (.md/.markdown) or plain-text (.txt) file.';
        else if (!file.size) message = 'The file must contain at least 1 byte of text.';
        else if (file.size > 1048576) message = 'The file must be at most 1 MiB (1,048,576 bytes).';
        else if (destination === null && (!name || [...name].length > 200 || name.includes('\0')))
          message = 'Use a nonblank title of at most 200 characters without NUL characters.';
        else if (
          destination === null &&
          ([...external_uri].length > 2048 || external_uri.includes('\0'))
        )
          message = 'Use a source URI of at most 2,048 characters without NUL characters.';
        setError(message);
        if (!message && file)
          onSubmit({ file, title: name, ...(external_uri ? { external_uri } : {}) });
      }}
    >
      <h2>{destination === null ? 'Add a source' : 'Append a source version'}</h2>
      {destination === null ? (
        <>
          <label htmlFor="upload-title">Source title</label>
          <input
            id="upload-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            disabled={busy}
          />
          <label htmlFor="upload-uri">Source URI (optional)</label>
          <input
            id="upload-uri"
            value={uri}
            onChange={(event) => setUri(event.target.value)}
            disabled={busy}
          />
        </>
      ) : (
        <p>Destination: {destination}. Existing versions and metadata are preserved.</p>
      )}
      <label htmlFor="upload-file">Source file</label>
      <input
        id="upload-file"
        type="file"
        accept=".md,.markdown,.txt"
        disabled={busy}
        onChange={(event) => {
          setFile(event.target.files?.[0] ?? null);
          setError('');
        }}
        aria-describedby="upload-help"
      />
      <p id="upload-help" className="small-print">
        One nonblank UTF-8 Markdown or text file, up to 1 MiB. Choosing a file does not upload it.
      </p>
      <div className="browser-actions">
        <button type="submit" disabled={busy}>
          {label}
        </button>
        <button type="button" className="quiet-button" disabled={busy} onClick={onCancel}>
          Cancel
        </button>
      </div>
      {busy && (
        <p role="status">
          Uploading. Leaving this view may still allow the server to save the file.
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
