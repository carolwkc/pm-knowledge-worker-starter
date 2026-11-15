import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import App from './App';
import { api } from './api';

const original = '👋 Synthetic café\r\n\r\nDecision: preserve evidence.\r\n';
const receipt = {
  workspace_id: 'w1',
  source_document_id: 's1',
  document_version_id: 'v1',
  version_number: 1,
  sha256: 'a'.repeat(64),
  chunk_count: 2,
  duplicate: false,
};
const version = {
  ...receipt,
  title: 'Synthetic notes',
  external_uri: 'javascript:inert',
  plain_text: original,
  ingested_at: '2026-01-01',
  source_is_latest: true,
};
const summary = {
  workspace_id: 'w1',
  source_document_id: 's1',
  title: version.title,
  external_uri: version.external_uri,
  created_at: '2026-01-01',
  latest_version_id: 'v1',
  latest_version_number: 1,
  latest_ingested_at: '2026-01-01',
};
const reply = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });

function mockUploads(
  options: {
    role?: 'reader' | 'editor' | 'owner';
    post?: () => Promise<Response>;
    catalogue?: (url: URL) => Promise<Response>;
    source?: () => Promise<Response>;
    history?: () => Promise<Response>;
    access?: () => string;
  } = {},
) {
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    const url = new URL(path, 'http://localhost');
    if (url.pathname.endsWith('/me')) return reply({ id: 'u1', name: 'Synthetic editor' });
    if (url.pathname.endsWith('/workspaces'))
      return reply({
        workspaces: [
          { id: 'w1', name: 'Aurora', role: options.access?.() ?? options.role ?? 'editor' },
          { id: 'w2', name: 'Orbit', role: 'owner' },
        ],
      });
    if (init?.method === 'POST') return options.post ? options.post() : reply(receipt, 201);
    if (url.pathname.includes('/versions/'))
      return options.source ? options.source() : reply(version);
    if (url.pathname.endsWith('/versions'))
      return options.history ? options.history() : reply({ versions: [version], has_more: false });
    if (url.pathname.endsWith('/sources'))
      return options.catalogue
        ? options.catalogue(url)
        : reply({ sources: url.pathname.includes('/w1/') ? [summary] : [], has_more: false });
    return reply({}, 404);
  });
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}

async function browse() {
  render(<App />);
  await userEvent.type(screen.getByLabelText('API token'), 'synthetic-token');
  await userEvent.click(screen.getByRole('button', { name: 'Connect' }));
  await screen.findByLabelText('Workspace');
  await userEvent.click(screen.getByRole('button', { name: 'Browse sources' }));
  await screen.findByRole('button', { name: 'Open Synthetic notes' });
}
async function newDraft(file = new File([original], 'notes.MD', { type: 'text/markdown' })) {
  await userEvent.click(screen.getByRole('button', { name: 'Add source' }));
  await userEvent.type(screen.getByLabelText('Source title'), '  Synthetic notes  ');
  // Disable accept filtering here so validation tests can exercise unsupported extensions.
  await userEvent.setup({ applyAccept: false }).upload(screen.getByLabelText('Source file'), file);
}
const posts = (fetcher: ReturnType<typeof mockUploads>) =>
  fetcher.mock.calls.filter(([, init]) => init?.method === 'POST');

it('sends the original File as multipart without a content-type header and preserves JSON calls', async () => {
  const fetcher = mockUploads();
  const file = new File([original], 'notes.md');
  const signal = new AbortController().signal;
  expect(
    await api.uploadSource('token', 'w/1', { title: 'Notes', external_uri: 'inert', file }, signal),
  ).toEqual(receipt);
  const [path, init] = fetcher.mock.calls[0];
  expect(path).toBe('/api/v1/workspaces/w%2F1/sources');
  expect(init).toMatchObject({
    method: 'POST',
    headers: { Authorization: 'Bearer token' },
    signal,
    cache: 'no-store',
    credentials: 'omit',
  });
  expect(new Headers(init?.headers).has('Content-Type')).toBe(false);
  const body = init?.body as FormData;
  expect(body.get('file')).toBe(file);
  expect(body.get('title')).toBe('Notes');
  expect(body.get('external_uri')).toBe('inert');
  await api.uploadVersion('token', 'w1', 's/1', file, signal);
  expect(fetcher.mock.calls[1][0]).toBe('/api/v1/workspaces/w1/sources/s%2F1/versions');
  expect([...(fetcher.mock.calls[1][1]?.body as FormData).keys()]).toEqual(['file']);
  await api.ask('token', 'w1', 'why?', 'keyword', signal);
  expect(fetcher.mock.calls[2][1]).toMatchObject({
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: 'why?', mode: 'keyword' }),
  });
});

it('requires explicit submission, opens the exact uploaded version and clears the file draft', async () => {
  const fetcher = mockUploads();
  await browse();
  await newDraft();
  await userEvent.type(screen.getByLabelText('Source URI (optional)'), 'javascript:inert');
  expect(posts(fetcher)).toHaveLength(0);
  await userEvent.click(screen.getByRole('button', { name: 'Upload source' }));
  expect(await screen.findByText('Source saved: version 1.')).toBeVisible();
  expect((await screen.findByTestId('source-text')).textContent).toBe(original);
  expect(screen.queryByLabelText('Source file')).not.toBeInTheDocument();
  expect(posts(fetcher)).toHaveLength(1);
  expect((posts(fetcher)[0][1]?.body as FormData).get('title')).toBe('Synthetic notes');
  expect(screen.getByRole('region', { name: 'Version history' })).toBeVisible();
  expect(screen.getByText('javascript:inert')).not.toHaveAttribute('href');
});

it.each(['reader', 'editor', 'owner'] as const)(
  'offers uploads only to authorized %s roles',
  async (role) => {
    mockUploads({ role });
    await browse();
    expect(screen.queryByRole('button', { name: 'Add source' }) !== null).toBe(role !== 'reader');
    await userEvent.click(screen.getByRole('button', { name: 'Open Synthetic notes' }));
    await screen.findByTestId('source-text');
    expect(screen.queryByRole('button', { name: 'Upload new version' }) !== null).toBe(
      role !== 'reader',
    );
  },
);

it('reuses a historical version without reactivating it or editing destination metadata', async () => {
  const fetcher = mockUploads({
    post: async () => reply({ ...receipt, duplicate: true }),
    source: async () => reply({ ...version, source_is_latest: false }),
  });
  await browse();
  await userEvent.click(screen.getByRole('button', { name: 'Open Synthetic notes' }));
  await screen.findByText('Historical version', { exact: true });
  await userEvent.click(screen.getByRole('button', { name: 'Upload new version' }));
  expect(screen.queryByLabelText('Source title')).not.toBeInTheDocument();
  await userEvent.upload(screen.getByLabelText('Source file'), new File([original], 'old.txt'));
  await userEvent.click(screen.getByRole('button', { name: 'Upload version' }));
  expect(await screen.findByText('Existing content reused: version 1.')).toBeVisible();
  expect(await screen.findByText('Historical version', { exact: true })).toBeVisible();
  expect(posts(fetcher)[0][0]).toContain('/sources/s1/versions');
  expect(screen.getByRole('button', { name: 'Generate proposals' })).toBeDisabled();
});

it.each([
  { file: new File(['x'], 'bad.pdf'), message: /Markdown.*plain-text/ },
  { file: new File([], 'empty.txt'), message: /1 byte/ },
  { file: new File(['x'.repeat(1048577)], 'large.txt'), message: /1 MiB/ },
])('rejects $file.name before sending it', async ({ file, message }) => {
  const fetcher = mockUploads();
  await browse();
  await newDraft(file);
  await userEvent.click(screen.getByRole('button', { name: 'Upload source' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(message);
  expect(posts(fetcher)).toHaveLength(0);
});

it.each([413, 415, 422])(
  'keeps a correctable draft after HTTP %s without exposing error bodies',
  async (status) => {
    const fetcher = mockUploads({ post: async () => reply({ detail: 'SECRET response' }, status) });
    await browse();
    await newDraft();
    await userEvent.click(screen.getByRole('button', { name: 'Upload source' }));
    await screen.findByRole('alert');
    expect(screen.getByLabelText('Source title')).toHaveValue('  Synthetic notes  ');
    expect((screen.getByLabelText('Source file') as HTMLInputElement).files).toHaveLength(1);
    expect(screen.queryByText(/SECRET/)).not.toBeInTheDocument();
    expect(posts(fetcher)).toHaveLength(1);
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument();
  },
);

it('retains confirmed success across a refresh failure and retries GETs only', async () => {
  let catalogues = 0;
  const fetcher = mockUploads({
    catalogue: async () =>
      ++catalogues === 2 ? reply({}, 503) : reply({ sources: [], has_more: false }),
  });
  render(<App />);
  await userEvent.type(screen.getByLabelText('API token'), 'synthetic-token');
  await userEvent.click(screen.getByRole('button', { name: 'Connect' }));
  await screen.findByLabelText('Workspace');
  await userEvent.click(screen.getByRole('button', { name: 'Browse sources' }));
  await screen.findByText('No documents yet. Ask an editor to upload a source.');
  await newDraft();
  await userEvent.click(screen.getByRole('button', { name: 'Upload source' }));
  expect(await screen.findByText('Source saved: version 1.')).toBeVisible();
  await screen.findByRole('alert');
  await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
  expect((await screen.findByTestId('source-text')).textContent).toBe(original);
  expect(screen.getByText('Source saved: version 1.')).toBeVisible();
  expect(posts(fetcher)).toHaveLength(1);
});

it.each(['network', 'server', 'mismatch', 'malformed'])(
  'requires manual inspection after an uncertain %s outcome',
  async (failure) => {
    const fetcher = mockUploads({
      post: async () => {
        if (failure === 'network') throw new TypeError('offline');
        return reply(
          failure === 'mismatch' ? { ...receipt, workspace_id: 'foreign' } : {},
          failure === 'server' ? 500 : 201,
        );
      },
    });
    await browse();
    await newDraft();
    await userEvent.click(screen.getByRole('button', { name: 'Upload source' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/Upload outcome uncertain/);
    expect(screen.queryByText('Source saved: version 1.')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Inspect source catalogue' }));
    await waitFor(() => expect(screen.queryByLabelText('Source file')).not.toBeInTheDocument());
    expect(posts(fetcher)).toHaveLength(1);
  },
);

it.each(
  ['view', 'workspace', 'logout'].flatMap((change) =>
    [200, 401, 404].map((status) => ({ change, status })),
  ),
)('ignores late upload $status after $change', async ({ change, status }) => {
  let resolve!: (response: Response) => void;
  const fetcher = mockUploads({
    post: () =>
      new Promise((done) => {
        resolve = done;
      }),
  });
  await browse();
  await newDraft();
  fireEvent.submit(screen.getByRole('form', { name: 'Upload source' }));
  fireEvent.submit(screen.getByRole('form', { name: 'Upload source' }));
  expect(posts(fetcher)).toHaveLength(1);
  if (change === 'view') await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
  if (change === 'workspace')
    await userEvent.selectOptions(screen.getByLabelText('Workspace'), 'w2');
  if (change === 'logout')
    await userEvent.click(screen.getByRole('button', { name: 'Disconnect' }));
  await act(async () => resolve(reply(receipt, status)));
  expect(screen.queryByText(/Source saved/)).not.toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Source file')).not.toBeInTheDocument();
  if (change !== 'logout') expect(screen.getByText('Synthetic editor')).toBeVisible();
});

it.each([
  { title: '😀'.repeat(200), uri: '😀'.repeat(2048), valid: true },
  { title: '😀'.repeat(201), uri: '', valid: false },
  { title: 'Notes', uri: '😀'.repeat(2049), valid: false },
  { title: '   ', uri: '', valid: false },
  { title: 'nul\0title', uri: '', valid: false },
  { title: 'Notes', uri: 'nul\0uri', valid: false },
])('validates Unicode metadata bounds ($valid)', async ({ title, uri, valid }) => {
  const fetcher = mockUploads();
  await browse();
  await newDraft();
  fireEvent.change(screen.getByLabelText('Source title'), { target: { value: title } });
  fireEvent.change(screen.getByLabelText('Source URI (optional)'), { target: { value: uri } });
  await userEvent.click(screen.getByRole('button', { name: 'Upload source' }));
  if (valid) {
    await screen.findByText('Source saved: version 1.');
    expect(posts(fetcher)).toHaveLength(1);
    expect((posts(fetcher)[0][1]?.body as FormData).get('title')).toBe(title);
    expect((posts(fetcher)[0][1]?.body as FormData).get('external_uri')).toBe(uri);
  } else {
    expect(await screen.findByRole('alert')).toHaveTextContent(/title|URI/);
    expect(posts(fetcher)).toHaveLength(0);
  }
});

it('accepts exactly one MiB with a case-insensitive markdown suffix and omits blank URI', async () => {
  const fetcher = mockUploads();
  await browse();
  await newDraft(new File(['x'.repeat(1048576)], 'NOTES.MARKDOWN'));
  await userEvent.type(screen.getByLabelText('Source URI (optional)'), '  ');
  await userEvent.click(screen.getByRole('button', { name: 'Upload source' }));
  await screen.findByText('Source saved: version 1.');
  expect((posts(fetcher)[0][1]?.body as FormData).has('external_uri')).toBe(false);
});

it.each(['cancel', 'source', 'view', 'workspace'])(
  'clears unsent file and metadata on %s changes',
  async (change) => {
    const fetcher = mockUploads();
    await browse();
    await newDraft();
    if (change === 'cancel') await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    if (change === 'source') {
      await userEvent.click(screen.getByRole('button', { name: 'Open Synthetic notes' }));
      await screen.findByTestId('source-text');
    }
    if (change === 'view') {
      await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
      await userEvent.click(screen.getByRole('button', { name: 'Browse sources' }));
      await screen.findByRole('button', { name: 'Open Synthetic notes' });
    }
    if (change === 'workspace') {
      await userEvent.selectOptions(screen.getByLabelText('Workspace'), 'w2');
      await screen.findByText('No documents yet. Ask an editor to upload a source.');
    }
    expect(screen.queryByLabelText('Source file')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Add source' }));
    expect(screen.getByLabelText('Source title')).toHaveValue('');
    expect((screen.getByLabelText('Source file') as HTMLInputElement).files).toHaveLength(0);
    expect(posts(fetcher)).toHaveLength(0);
  },
);

it.each(['source', 'history'])(
  'retains receipt and retries only reads after %s failure',
  async (kind) => {
    let reads = 0;
    const transient = async () =>
      ++reads === 1
        ? reply({}, 503)
        : reply(kind === 'source' ? version : { versions: [version], has_more: false });
    const fetcher = mockUploads(kind === 'source' ? { source: transient } : { history: transient });
    await browse();
    await newDraft();
    await userEvent.click(screen.getByRole('button', { name: 'Upload source' }));
    await screen.findByRole('alert');
    expect(screen.getByText('Source saved: version 1.')).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect((await screen.findByTestId('source-text')).textContent).toBe(original);
    expect(posts(fetcher)).toHaveLength(1);
  },
);

it.each([401, 403, 404])(
  'clears draft and refreshes authorization after upload HTTP %s',
  async (status) => {
    let demoted = false;
    const fetcher = mockUploads({
      access: () => (demoted ? 'reader' : 'editor'),
      post: async () => {
        demoted = true;
        return reply({}, status);
      },
    });
    await browse();
    await newDraft();
    await userEvent.click(screen.getByRole('button', { name: 'Upload source' }));
    await screen.findByRole('alert');
    expect(screen.queryByLabelText('Source file')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Add source' })).not.toBeInTheDocument();
    expect(screen.queryByText(/Source saved/)).not.toBeInTheDocument();
    expect(posts(fetcher)).toHaveLength(1);
    if (status === 401) expect(screen.getByLabelText('API token')).toBeVisible();
    else await screen.findByText('reader access');
  },
);

it('resets filter and pages after saving, even if the target is absent from the catalogue page', async () => {
  let uploaded = false;
  const fetcher = mockUploads({
    catalogue: async () => reply({ sources: uploaded ? [] : [summary], has_more: !uploaded }),
    post: async () => {
      uploaded = true;
      return reply(receipt, 201);
    },
  });
  await browse();
  await userEvent.type(screen.getByLabelText('Filter by title'), 'irrelevant');
  await userEvent.click(screen.getByRole('button', { name: 'Apply filter' }));
  await userEvent.click(
    within(screen.getByRole('region', { name: 'Source catalogue' })).getByRole('button', {
      name: 'Next',
    }),
  );
  await screen.findByText('Page 2');
  await newDraft();
  await userEvent.click(screen.getByRole('button', { name: 'Upload source' }));
  await screen.findByTestId('source-text');
  await waitFor(() =>
    expect(screen.getByRole('region', { name: 'Version history' })).toHaveTextContent('Version 1'),
  );
  expect(screen.getByLabelText('Filter by title')).toHaveValue('');
  expect(
    within(screen.getByRole('region', { name: 'Source catalogue' })).getByRole('button', {
      name: 'Previous',
    }),
  ).toBeDisabled();
  expect(posts(fetcher)).toHaveLength(1);
});

it('does not display mismatched exact-version evidence after a confirmed upload', async () => {
  mockUploads({ source: async () => reply({ ...version, document_version_id: 'wrong' }) });
  await browse();
  await newDraft();
  await userEvent.click(screen.getByRole('button', { name: 'Upload source' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/did not match/);
  expect(screen.getByText('Source saved: version 1.')).toBeVisible();
  expect(screen.queryByTestId('source-text')).not.toBeInTheDocument();
});
