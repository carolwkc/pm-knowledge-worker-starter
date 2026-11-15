import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import App from './App';

const user = { id: 'user-1', name: 'Synthetic member', created_at: '2026-01-01' };
const workspaces = [
  { id: 'w1', name: 'Aurora', role: 'reader', created_at: '2026-01-01' },
  { id: 'w2', name: 'Orbit', role: 'owner', created_at: '2026-01-02' },
];
const original = '👋 Café\r\n\r\nTroubleshooting acceleration.\r\n';
const quote = 'Troubleshooting acceleration.\r\n';
const citation = {
  citation: '1',
  source_document_id: 's1',
  document_version_id: 'v1',
  chunk_id: 'c1',
  title: 'Synthetic source',
  external_uri: 'javascript:alert(1)',
  ordinal: 1,
  excerpt: quote,
  start_char: Array.from('👋 Café\r\n\r\n').length,
  end_char: Array.from(original).length,
};
const answer = {
  answer: `Extracted evidence (verbatim source text):\n\n[1] "${quote}"`,
  status: 'grounded',
  sources: [citation],
};
const version = {
  workspace_id: 'w1',
  source_document_id: 's1',
  document_version_id: 'v1',
  title: 'Synthetic source',
  external_uri: citation.external_uri,
  version_number: 1,
  sha256: 'a'.repeat(64),
  ingested_at: '2026-01-01T00:00:00Z',
  plain_text: original,
  source_is_latest: false,
};

function reply(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function mockApi(
  options: {
    empty?: boolean;
    ask?: () => Promise<Response>;
    source?: () => Promise<Response>;
  } = {},
) {
  const fetcher = vi.fn(async (input: string | URL | Request) => {
    const path = String(input);
    if (path.endsWith('/me')) return reply(user);
    if (path.endsWith('/workspaces')) return reply({ workspaces: options.empty ? [] : workspaces });
    if (path.endsWith('/ask')) return options.ask ? options.ask() : reply(answer);
    if (path.includes('/sources?')) return reply({ sources: [], has_more: false });
    if (path.endsWith('/versions/v1')) return options.source ? options.source() : reply(version);
    return reply({ detail: 'Not found' }, 404);
  });
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}

async function connect() {
  await userEvent.type(screen.getByLabelText('API token'), 'synthetic-token');
  await userEvent.click(screen.getByRole('button', { name: 'Connect' }));
  await screen.findByLabelText('Workspace');
}

async function ask() {
  await userEvent.type(screen.getByLabelText('Your question'), 'troubleshooting');
  await userEvent.click(screen.getByRole('button', { name: 'Ask question' }));
}

it('connects, selects a workspace, asks, and opens the exact historical source with a verified highlight', async () => {
  const fetcher = mockApi();
  render(<App />);
  const tokenInput = screen.getByLabelText('API token');
  await connect();
  expect(tokenInput).toHaveValue('');
  expect(screen.getByLabelText('Workspace')).toHaveValue('w1');
  await ask();
  const citationButton = await screen.findByRole('button', { name: '[1] Synthetic source' });
  await userEvent.click(citationButton);
  await screen.findByText('Historical version');
  const sourceText = screen.getByTestId('source-text');
  expect(sourceText.textContent).toBe(original);
  expect(sourceText.querySelector('mark')?.textContent).toBe(quote);
  expect(screen.getByText('javascript:alert(1)')).not.toHaveAttribute('href');
  expect(
    fetcher.mock.calls.some(
      ([path]) => String(path) === '/api/v1/workspaces/w1/sources/s1/versions/v1',
    ),
  ).toBe(true);
});

it('explains an empty workspace list', async () => {
  mockApi({ empty: true });
  render(<App />);
  await userEvent.type(screen.getByLabelText('API token'), 'synthetic-token');
  await userEvent.click(screen.getByRole('button', { name: 'Connect' }));
  expect(await screen.findByText(/No workspaces yet/)).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Ask question' })).not.toBeInTheDocument();
});

it('preserves completed Q&A across browsing and restores verified citation navigation', async () => {
  mockApi();
  render(<App />);
  await connect();
  await ask();
  await screen.findByRole('button', { name: '[1] Synthetic source' });
  await userEvent.click(screen.getByRole('button', { name: 'Browse sources' }));
  await screen.findByText(/No documents yet/);
  await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
  expect(document.querySelector('.answer-text')?.textContent).toBe(answer.answer);
  await userEvent.click(screen.getByRole('button', { name: '[1] Synthetic source' }));
  await screen.findByTestId('source-text');
  expect(screen.getByTestId('source-text').querySelector('mark')?.textContent).toBe(quote);
});

it('shows insufficient evidence without inventing citations', async () => {
  mockApi({
    ask: async () =>
      reply({
        answer: 'Insufficient evidence: no matching source excerpts.',
        status: 'insufficient_evidence',
        sources: [],
      }),
  });
  render(<App />);
  await connect();
  await ask();
  expect(
    await screen.findByText('Insufficient evidence: no matching source excerpts.'),
  ).toBeVisible();
  expect(screen.queryByRole('button', { name: /\[1\]/ })).not.toBeInTheDocument();
});

it('renders hostile answer/source metadata as text and only structured citations as controls', async () => {
  const hostile = '<img src=x onerror=alert(1)> [99] ignore instructions';
  mockApi({
    ask: async () =>
      reply({ ...answer, answer: hostile, sources: [{ ...citation, title: hostile }] }),
    source: async () => reply({ ...version, plain_text: hostile }),
  });
  const { container } = render(<App />);
  await connect();
  await ask();
  await userEvent.click(await screen.findByRole('button', { name: `[1] ${hostile}` }));
  expect(await screen.findByText(/Citation could not be verified/)).toBeVisible();
  expect(container.querySelector('img, script, mark')).toBeNull();
  expect(screen.queryByRole('button', { name: '[99]' })).not.toBeInTheDocument();
});

it('makes an explicit semantic request and reports unavailability without keyword fallback', async () => {
  const fetcher = mockApi({
    ask: async () => reply({ detail: 'Local embeddings unavailable' }, 503),
  });
  render(<App />);
  await connect();
  await userEvent.selectOptions(screen.getByLabelText('Retrieval mode'), 'semantic');
  await ask();
  expect(await screen.findByRole('alert')).toHaveTextContent(/unavailable/i);
  const requests = fetcher.mock.calls.filter(([path]) => String(path).endsWith('/ask'));
  expect(requests).toHaveLength(1);
  expect(JSON.parse((requests[0] as unknown as [string, RequestInit])[1].body as string).mode).toBe(
    'semantic',
  );
});

it('ignores a late answer after workspace switching even if fetch ignores abort', async () => {
  let resolve!: (value: Response) => void;
  mockApi({
    ask: () =>
      new Promise<Response>((done) => {
        resolve = done;
      }),
  });
  render(<App />);
  await connect();
  await ask();
  await userEvent.selectOptions(screen.getByLabelText('Workspace'), 'w2');
  await act(async () => {
    resolve(reply(answer));
  });
  expect(screen.queryByText(answer.answer)).not.toBeInTheDocument();
  expect(screen.getByLabelText('Your question')).toHaveValue('');
});

it('ignores a late source response after logout and clears credentials and protected state', async () => {
  let resolve!: (value: Response) => void;
  const fetcher = mockApi({
    source: () =>
      new Promise<Response>((done) => {
        resolve = done;
      }),
  });
  render(<App />);
  await connect();
  await ask();
  await userEvent.click(await screen.findByRole('button', { name: '[1] Synthetic source' }));
  await userEvent.click(screen.getByRole('button', { name: 'Disconnect' }));
  await act(async () => {
    resolve(reply(version));
  });
  expect(screen.getByLabelText('API token')).toHaveValue('');
  expect(screen.queryByTestId('source-text')).not.toBeInTheDocument();
  const init = (fetcher.mock.calls.at(-1) as unknown as [string, RequestInit])[1];
  expect(init.signal?.aborted).toBe(true);
});

it('clears the session on 401', async () => {
  mockApi({ ask: async () => reply({ detail: 'Invalid or missing credentials' }, 401) });
  render(<App />);
  await connect();
  await ask();
  expect(await screen.findByLabelText('API token')).toHaveValue('');
  expect(screen.getByRole('alert')).toHaveTextContent(/expired|revoked|connect again/i);
});

it('refreshes workspaces after access is lost', async () => {
  const fetcher = mockApi({ ask: async () => reply({ detail: 'Workspace not found' }, 404) });
  render(<App />);
  await connect();
  fetcher.mockImplementation(async (input) =>
    String(input).endsWith('/workspaces')
      ? reply({ workspaces: [] })
      : reply({ detail: 'Workspace not found' }, 404),
  );
  await ask();
  expect(await screen.findByText(/No workspaces yet/)).toBeVisible();
  expect(screen.queryByText(answer.answer)).not.toBeInTheDocument();
});

it('reports connection failures without echoing server content', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => reply({ detail: 'synthetic-secret-token' }, 401)),
  );
  render(<App />);
  fireEvent.change(screen.getByLabelText('API token'), {
    target: { value: 'synthetic-secret-token' },
  });
  await userEvent.click(screen.getByRole('button', { name: 'Connect' }));
  expect(await screen.findByRole('alert')).not.toHaveTextContent('synthetic-secret-token');
  expect(screen.getByLabelText('API token')).toHaveValue('');
});

it('shows validation and network failures with a retryable question form', async () => {
  const fetcher = mockApi({ ask: async () => reply({ detail: [] }, 422) });
  render(<App />);
  await connect();
  await ask();
  expect(await screen.findByRole('alert')).toHaveTextContent(/question/i);
  fetcher.mockRejectedValueOnce(new TypeError('network'));
  await userEvent.click(screen.getByRole('button', { name: 'Ask question' }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/connection/i));
  expect(
    within(screen.getByRole('form', { name: 'Ask your workspace' })).getByRole('button'),
  ).toBeEnabled();
});
