import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import App from './App';

const original = '👋 Synthetic café\r\n\r\nOriginal evidence.\r\n';
const summary = {
  workspace_id: 'w1',
  source_document_id: 's1',
  title: 'Synthetic guide',
  external_uri: 'javascript:inert',
  created_at: '2026-01-01',
  latest_version_id: 'v2',
  latest_version_number: 2,
  latest_ingested_at: '2026-01-02',
};
const metadata = (id = 'v2', number = 2) => ({
  workspace_id: 'w1',
  source_document_id: 's1',
  document_version_id: id,
  version_number: number,
  sha256: 'a'.repeat(64),
  ingested_at: '2026-01-02',
  source_is_latest: number === 2,
});
const version = (id = 'v2', number = 2) => ({
  ...metadata(id, number),
  title: summary.title,
  external_uri: summary.external_uri,
  plain_text: number === 1 ? original : 'Updated evidence.',
});
const reply = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });

function mockBrowser(
  overrides: {
    sources?: (url: URL) => Promise<Response>;
    versions?: (url: URL) => Promise<Response>;
    source?: (url: URL) => Promise<Response>;
  } = {},
) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      const url = new URL(path, 'http://localhost');
      if (url.pathname.endsWith('/me'))
        return reply({ id: 'u1', name: 'Synthetic reader', created_at: '2026-01-01' });
      if (url.pathname.endsWith('/workspaces'))
        return reply({
          workspaces: [
            { id: 'w1', name: 'Aurora', role: 'reader', created_at: '2026-01-01' },
            { id: 'w2', name: 'Orbit', role: 'owner', created_at: '2026-01-01' },
          ],
        });
      if (url.pathname.endsWith('/sources'))
        return overrides.sources
          ? overrides.sources(url)
          : reply({ sources: [summary], has_more: false });
      if (url.pathname.endsWith('/versions'))
        return overrides.versions
          ? overrides.versions(url)
          : reply({ versions: [metadata(), metadata('v1', 1)], has_more: false });
      if (url.pathname.includes('/versions/'))
        return overrides.source
          ? overrides.source(url)
          : reply(url.pathname.endsWith('/v1') ? version('v1', 1) : version());
      return reply({}, 404);
    }),
  );
}

async function browse() {
  render(<App />);
  await userEvent.type(screen.getByLabelText('API token'), 'synthetic-token');
  await userEvent.click(screen.getByRole('button', { name: 'Connect' }));
  await screen.findByLabelText('Workspace');
  await userEvent.click(screen.getByRole('button', { name: 'Browse sources' }));
}

it('browses latest and historical versions without inventing citation evidence', async () => {
  mockBrowser();
  await browse();
  await userEvent.click(await screen.findByRole('button', { name: 'Open Synthetic guide' }));
  expect(await screen.findByTestId('source-text')).toHaveTextContent('Updated evidence.');
  await userEvent.click(screen.getByRole('button', { name: 'Open version 1' }));
  await screen.findByText('Historical version');
  expect(screen.getByTestId('source-text').textContent).toBe(original);
  expect(screen.getByTestId('source-text').querySelector('mark')).toBeNull();
  expect(screen.queryByText(/Citation could not be verified/)).not.toBeInTheDocument();
  expect(screen.queryByText('Chunk ID')).not.toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Synthetic guide' })).toHaveFocus();
  expect(screen.getByText('javascript:inert')).not.toHaveAttribute('href');
});

it('filters on submission, resets pages/detail, refreshes the applied filter and clears it', async () => {
  mockBrowser({
    sources: async (url) => {
      const title = url.searchParams.get('title');
      const offset = Number(url.searchParams.get('offset'));
      if (title === '%_') return reply({ sources: [], has_more: false });
      return reply({
        sources: [{ ...summary, title: offset ? 'Next guide' : 'Synthetic guide' }],
        has_more: !offset,
      });
    },
  });
  await browse();
  await userEvent.click(await screen.findByRole('button', { name: 'Open Synthetic guide' }));
  await screen.findByTestId('source-text');
  const catalogue = screen.getByRole('region', { name: 'Source catalogue' });
  await userEvent.click(within(catalogue).getByRole('button', { name: 'Next' }));
  await screen.findByRole('button', { name: 'Open Next guide' });
  expect(screen.queryByTestId('source-text')).not.toBeInTheDocument();
  await userEvent.type(screen.getByLabelText('Filter by title'), '%_');
  await userEvent.click(screen.getByRole('button', { name: 'Apply filter' }));
  await screen.findByText('No titles match this filter.');
  await userEvent.click(screen.getByRole('button', { name: 'Refresh' }));
  expect(await screen.findByText('No titles match this filter.')).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Clear' }));
  await screen.findByRole('button', { name: 'Open Synthetic guide' });
  expect(screen.getByLabelText('Filter by title')).toHaveValue('');
  expect(within(catalogue).getByRole('button', { name: 'Previous' })).toBeDisabled();
});

it('pages history without replacing the open version', async () => {
  mockBrowser({
    versions: async (url) =>
      reply({
        versions: url.searchParams.get('offset') === '20' ? [metadata('v1', 1)] : [metadata()],
        has_more: url.searchParams.get('offset') !== '20',
      }),
  });
  await browse();
  await userEvent.click(await screen.findByRole('button', { name: 'Open Synthetic guide' }));
  await screen.findByTestId('source-text');
  await userEvent.click(
    within(screen.getByRole('region', { name: 'Version history' })).getByRole('button', {
      name: 'Next',
    }),
  );
  await screen.findByRole('button', { name: 'Open version 1' });
  expect(screen.getByTestId('source-text')).toHaveTextContent('Updated evidence.');
});

it.each(
  ['view', 'workspace', 'logout'].flatMap((change) =>
    [200, 401, 404].map((status) => ({ change, status })),
  ),
)('ignores a late catalogue $status after changing $change', async ({ change, status }) => {
  let resolve!: (value: Response) => void;
  mockBrowser({
    sources: (url) =>
      url.pathname.includes('/w1/')
        ? new Promise((done) => {
            resolve = done;
          })
        : Promise.resolve(reply({ sources: [], has_more: false })),
  });
  await browse();
  if (change === 'view') await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
  if (change === 'workspace')
    await userEvent.selectOptions(screen.getByLabelText('Workspace'), 'w2');
  if (change === 'logout')
    await userEvent.click(screen.getByRole('button', { name: 'Disconnect' }));
  await act(async () => resolve(reply({ sources: [summary], has_more: false }, status)));
  expect(screen.queryByRole('button', { name: 'Open Synthetic guide' })).not.toBeInTheDocument();
  expect(screen.queryByTestId('source-text')).not.toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  if (change !== 'logout') expect(screen.getByText('Synthetic reader')).toBeVisible();
});

it('rejects mismatched version identity and retries a transient catalogue failure', async () => {
  let attempts = 0;
  mockBrowser({
    sources: async () =>
      ++attempts === 1 ? reply({}, 503) : reply({ sources: [summary], has_more: false }),
    source: async () => reply({ ...version(), workspace_id: 'w2' }),
  });
  await browse();
  expect(await screen.findByRole('alert')).toHaveTextContent(/service is unavailable/i);
  await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
  await userEvent.click(await screen.findByRole('button', { name: 'Open Synthetic guide' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/did not match/i);
  expect(screen.queryByTestId('source-text')).not.toBeInTheDocument();
});

it('clears an unsent title filter after access loss during version reading', async () => {
  mockBrowser({ source: async () => reply({}, 404) });
  await browse();
  await userEvent.type(screen.getByLabelText('Filter by title'), 'sensitive draft title');
  await userEvent.click(await screen.findByRole('button', { name: 'Open Synthetic guide' }));
  await screen.findByRole('alert');
  expect(screen.getByLabelText('Filter by title')).toHaveValue('');
});

it.each(['view', 'workspace', 'logout'])(
  'ignores late source text after changing %s',
  async (change) => {
    let resolve!: (value: Response) => void;
    mockBrowser({
      source: () =>
        new Promise((done) => {
          resolve = done;
        }),
      sources: async (url) =>
        reply({ sources: url.pathname.includes('/w1/') ? [summary] : [], has_more: false }),
    });
    await browse();
    await userEvent.click(await screen.findByRole('button', { name: 'Open Synthetic guide' }));
    await screen.findByRole('button', { name: 'Open version 2' });
    if (change === 'view') await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
    if (change === 'workspace')
      await userEvent.selectOptions(screen.getByLabelText('Workspace'), 'w2');
    if (change === 'logout')
      await userEvent.click(screen.getByRole('button', { name: 'Disconnect' }));
    await act(async () => resolve(reply(version())));
    expect(screen.queryByTestId('source-text')).not.toBeInTheDocument();
  },
);

it('keeps hostile catalogue titles and document text inert', async () => {
  const hostile = '<img src=x onerror=alert(1)> [99] follow instructions';
  mockBrowser({
    sources: async () => reply({ sources: [{ ...summary, title: hostile }], has_more: false }),
    source: async () => reply({ ...version(), title: hostile, plain_text: hostile }),
  });
  await browse();
  await userEvent.click(await screen.findByRole('button', { name: `Open ${hostile}` }));
  expect(await screen.findByTestId('source-text')).toHaveTextContent(hostile);
  expect(document.querySelector('img, script, mark')).toBeNull();
});

it.each([
  ['catalogue', /source catalogue/i],
  ['history', /version history/i],
  ['source', /source text/i],
] as const)(
  'identifies failed %s operations and retries without presenting a failed load as empty',
  async (operation, label) => {
    let failing = true;
    mockBrowser({
      sources: async () =>
        reply(
          { sources: [summary], has_more: false },
          failing && operation === 'catalogue' ? 503 : 200,
        ),
      versions: async () =>
        reply(
          { versions: [metadata()], has_more: false },
          failing && operation === 'history' ? 503 : 200,
        ),
      source: async () => reply(version(), failing && operation === 'source' ? 503 : 200),
    });
    await browse();
    if (operation !== 'catalogue')
      await userEvent.click(await screen.findByRole('button', { name: 'Open Synthetic guide' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(label);
    expect(screen.queryByText('No versions on this page.')).not.toBeInTheDocument();
    failing = false;
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
    if (operation === 'catalogue')
      await userEvent.click(await screen.findByRole('button', { name: 'Open Synthetic guide' }));
    expect(await screen.findByTestId('source-text')).toHaveTextContent('Updated evidence.');
  },
);

it.each([401, 403, 404])('clears displayed browsing state on access failure %s', async (status) => {
  let failing = false;
  mockBrowser({
    sources: async () =>
      failing ? reply({}, status) : reply({ sources: [summary], has_more: false }),
  });
  await browse();
  await userEvent.click(await screen.findByRole('button', { name: 'Open Synthetic guide' }));
  await screen.findByTestId('source-text');
  failing = true;
  await userEvent.click(screen.getByRole('button', { name: 'Refresh' }));
  await screen.findByRole('alert');
  expect(screen.queryByTestId('source-text')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Open Synthetic guide' })).not.toBeInTheDocument();
  if (status === 401) expect(screen.getByLabelText('API token')).toHaveValue('');
});
