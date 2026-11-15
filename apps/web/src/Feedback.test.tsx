import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import App from './App';

const quote = 'Synthetic café quartz evidence.\r\n';
const citation = {
  citation: '1',
  source_document_id: 's1',
  document_version_id: 'v1',
  chunk_id: 'c1',
  title: 'Synthetic source',
  external_uri: 'javascript:inert',
  ordinal: 0,
  excerpt: quote,
  start_char: 0,
  end_char: Array.from(quote).length,
};
const answer = {
  answer: `Extracted evidence (verbatim source text):\n\n[1] "${quote}"`,
  status: 'grounded',
  sources: [citation],
};
const record = {
  id: '11111111-1111-4111-8111-111111111111',
  workspace_id: 'w1',
  submission_id: '22222222-2222-4222-8222-222222222222',
  created_at: '2026-01-01T00:00:00Z',
  created_by: 'reader-id',
  question: 'Original question',
  mode: 'keyword',
  rating: 'not_helpful',
  reason: 'missing_evidence',
  comment: '<img src=x onerror=alert(1)>',
  answer,
};
function reply(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
function mockApi(
  options: {
    role?: string;
    empty?: boolean;
    post?: (body: Record<string, unknown>) => Promise<Response>;
    list?: (path: string) => Promise<Response>;
    detail?: () => Promise<Response>;
  } = {},
) {
  const posts: Record<string, unknown>[] = [];
  let role = options.role ?? 'reader';
  const fetcher = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const path = String(input);
    if (path.endsWith('/me')) return reply({ id: 'reader-id', name: 'Synthetic user' });
    if (path.endsWith('/workspaces'))
      return reply({
        workspaces: [
          { id: 'w1', name: 'Aurora', role },
          { id: 'w2', name: 'Orbit', role: 'reader' },
        ],
      });
    if (path.endsWith('/ask'))
      return reply(
        options.empty
          ? {
              answer:
                'Insufficient evidence: no matching source excerpts were found in this workspace.',
              status: 'insufficient_evidence',
              sources: [],
            }
          : answer,
      );
    if (path.includes('/sources?')) return reply({ sources: [], has_more: false });
    if (path.endsWith('/versions/v1'))
      return reply({
        workspace_id: 'w1',
        source_document_id: 's1',
        document_version_id: 'v1',
        title: citation.title,
        external_uri: citation.external_uri,
        version_number: 1,
        sha256: 'a'.repeat(64),
        ingested_at: record.created_at,
        plain_text: quote,
        source_is_latest: false,
      });
    if (path.endsWith('/feedback') && init?.method === 'POST') {
      const body = JSON.parse(String(init.body));
      posts.push(body);
      return options.post
        ? options.post(body)
        : reply({ ...record, submission_id: body.submission_id }, 201);
    }
    if (path.includes('/feedback?'))
      return options.list ? options.list(path) : reply({ feedback: [record], has_more: false });
    if (path.endsWith(`/feedback/${record.id}`))
      return options.detail ? options.detail() : reply(record);
    return reply({}, 404);
  });
  vi.stubGlobal('fetch', fetcher);
  return {
    posts,
    fetcher,
    setRole: (value: string) => {
      role = value;
    },
  };
}
async function connect() {
  await userEvent.type(screen.getByLabelText('API token'), 'synthetic-token');
  await userEvent.click(screen.getByRole('button', { name: 'Connect' }));
  await screen.findByLabelText('Workspace');
}
async function ask() {
  await userEvent.type(screen.getByLabelText('Your question'), 'Original question');
  await userEvent.click(screen.getByRole('button', { name: 'Ask question' }));
  await screen.findByRole('button', { name: 'Submit feedback' });
}
async function rate() {
  await userEvent.click(screen.getByLabelText('Not helpful', { exact: true }));
}

it('saves only on explicit submit and pins the original question and mode', async () => {
  const { posts } = mockApi();
  render(<App />);
  await connect();
  await ask();
  expect(posts).toHaveLength(0);
  fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'Edited draft' } });
  await userEvent.selectOptions(screen.getByLabelText('Retrieval mode'), 'hybrid');
  await rate();
  await userEvent.selectOptions(screen.getByLabelText('Reason (optional)'), 'missing_evidence');
  await userEvent.type(
    screen.getByLabelText('Feedback comment (optional)'),
    '  Needs context 👋  ',
  );
  await userEvent.click(screen.getByRole('button', { name: 'Submit feedback' }));
  await screen.findByText(/Feedback saved/);
  expect(posts).toHaveLength(1);
  expect(posts[0]).toMatchObject({
    question: 'Original question',
    mode: 'keyword',
    answer,
    rating: 'not_helpful',
    reason: 'missing_evidence',
    comment: 'Needs context 👋',
  });
  expect(screen.queryByRole('button', { name: 'Submit feedback' })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Browse sources' }));
  await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
  expect(screen.getByText(/Feedback saved/)).toBeVisible();
});

it('submits helpful insufficient-evidence feedback without a negative reason or blank comment', async () => {
  const { posts } = mockApi({ empty: true });
  render(<App />);
  await connect();
  await ask();
  await userEvent.click(screen.getByLabelText('Helpful', { exact: true }));
  await userEvent.click(screen.getByRole('button', { name: 'Submit feedback' }));
  await screen.findByText(/Feedback saved/);
  expect(posts[0]).toMatchObject({
    rating: 'helpful',
    answer: { status: 'insufficient_evidence', sources: [] },
  });
  expect(posts[0].reason).toBeUndefined();
  expect(posts[0].comment).toBeUndefined();
});

it('freezes uncertain submissions and retries explicitly with the same UUID and body', async () => {
  const { posts } = mockApi({
    post: async (body) => {
      if (posts.length === 1) throw new TypeError('lost response');
      return reply({ ...record, submission_id: body.submission_id });
    },
  });
  render(<App />);
  await connect();
  await ask();
  await rate();
  await userEvent.click(screen.getByRole('button', { name: 'Submit feedback' }));
  const retry = await screen.findByRole('button', { name: 'Retry feedback submission' });
  expect(posts).toHaveLength(1);
  expect(screen.queryByLabelText('Feedback comment (optional)')).not.toBeInTheDocument();
  await userEvent.click(retry);
  await screen.findByText(/Feedback saved/);
  expect(posts).toHaveLength(2);
  expect(posts[1]).toEqual(posts[0]);
});

it.each([422, 409, 503])(
  'handles feedback failure %s safely without automatic retries',
  async (status) => {
    const { posts } = mockApi({
      post: async () => reply({ detail: 'sensitive server body' }, status),
    });
    render(<App />);
    await connect();
    await ask();
    await rate();
    await userEvent.click(screen.getByRole('button', { name: 'Submit feedback' }));
    await screen.findByRole('alert');
    expect(posts).toHaveLength(1);
    expect(screen.queryByText('sensitive server body')).not.toBeInTheDocument();
    if (status === 422) expect(screen.getByLabelText('Feedback comment (optional)')).toBeVisible();
  },
);

it('validates Unicode comment limits and clears unsent drafts across views and questions', async () => {
  mockApi();
  render(<App />);
  await connect();
  await ask();
  await rate();
  fireEvent.change(screen.getByLabelText('Feedback comment (optional)'), {
    target: { value: '👋'.repeat(1001) },
  });
  expect(screen.getByRole('button', { name: 'Submit feedback' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Feedback comment (optional)'), {
    target: { value: 'bad\0comment' },
  });
  expect(screen.getByRole('button', { name: 'Submit feedback' })).toBeDisabled();
  await userEvent.click(screen.getByRole('button', { name: 'Browse sources' }));
  await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
  expect(screen.getByLabelText('Feedback comment (optional)')).toHaveValue('');
  await userEvent.click(screen.getByRole('button', { name: 'Ask question' }));
  await screen.findByRole('button', { name: 'Submit feedback' });
  expect(screen.getByLabelText('Not helpful', { exact: true })).not.toBeChecked();
});

it('lets owners inspect reported context and exact historical evidence as inert text', async () => {
  mockApi({ role: 'owner' });
  render(<App />);
  await connect();
  await userEvent.click(screen.getByRole('button', { name: 'Feedback' }));
  await userEvent.click(await screen.findByRole('button', { name: `Open feedback ${record.id}` }));
  await screen.findByRole('heading', { name: 'User-reported Q&A context' });
  expect(screen.getByText(record.comment)).toBeVisible();
  expect(document.querySelector('img')).toBeNull();
  await userEvent.click(screen.getByRole('button', { name: '[1] Synthetic source' }));
  await screen.findByText('Historical version');
  expect(screen.getByTestId('source-text').querySelector('mark')?.textContent).toBe(quote);
});

it('pages and filters feedback, resetting details and offset on refresh', async () => {
  const paths: string[] = [];
  mockApi({
    role: 'owner',
    list: async (path) => {
      paths.push(path);
      return reply({ feedback: [record], has_more: !path.includes('offset=20') });
    },
  });
  render(<App />);
  await connect();
  await userEvent.click(screen.getByRole('button', { name: 'Feedback' }));
  await userEvent.click(await screen.findByRole('button', { name: 'Next' }));
  await screen.findByText('Page 2');
  expect(paths.at(-1)).toContain('offset=20');
  await userEvent.selectOptions(screen.getByLabelText('Feedback rating'), 'not_helpful');
  await screen.findByText('Page 1');
  expect(paths.at(-1)).toContain('rating=not_helpful');
  await userEvent.click(screen.getByRole('button', { name: 'Refresh' }));
  await waitFor(() => expect(paths).toHaveLength(4));
  expect(paths.at(-1)).toContain('rating=not_helpful');
  expect(paths.at(-1)).toContain('offset=0');
});

it('hides owner controls from readers and clears feedback after demotion', async () => {
  const api = mockApi({ role: 'owner', detail: async () => reply({}, 403) });
  render(<App />);
  await connect();
  await userEvent.click(screen.getByRole('button', { name: 'Feedback' }));
  const open = await screen.findByRole('button', { name: `Open feedback ${record.id}` });
  api.setRole('reader');
  await userEvent.click(open);
  await waitFor(() =>
    expect(screen.queryByRole('button', { name: 'Feedback' })).not.toBeInTheDocument(),
  );
  expect(screen.queryByText('Original question')).not.toBeInTheDocument();
});

it('leaves the owner view when initial feedback navigation detects demotion', async () => {
  const api = mockApi({ role: 'owner', list: async () => reply({}, 403) });
  render(<App />);
  await connect();
  api.setRole('reader');
  await userEvent.click(screen.getByRole('button', { name: 'Feedback' }));
  await waitFor(() =>
    expect(screen.queryByRole('button', { name: 'Feedback' })).not.toBeInTheDocument(),
  );
  expect(screen.queryByRole('heading', { name: 'Q&A feedback' })).not.toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'What would you like to understand?' })).toBeVisible();
});

it.each([200, 401, 404])(
  'ignores delayed feedback response %s after workspace change',
  async (status) => {
    let finish!: (r: Response) => void;
    mockApi({
      post: () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    });
    render(<App />);
    await connect();
    await ask();
    await rate();
    await userEvent.click(screen.getByRole('button', { name: 'Submit feedback' }));
    await userEvent.selectOptions(screen.getByLabelText('Workspace'), 'w2');
    await act(async () => finish(reply({}, status)));
    expect(screen.getByLabelText('Workspace')).toHaveValue('w2');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByText(/Feedback saved/)).not.toBeInTheDocument();
  },
);

it('rejects unusable receipts and preserves the submission for explicit retry', async () => {
  const { posts } = mockApi({
    post: async (body) =>
      reply({ ...record, workspace_id: 'w2', submission_id: body.submission_id }, 201),
  });
  render(<App />);
  await connect();
  await ask();
  await rate();
  await userEvent.click(screen.getByRole('button', { name: 'Submit feedback' }));
  await screen.findByRole('button', { name: 'Retry feedback submission' });
  expect(posts).toHaveLength(1);
  expect(screen.queryByText(/Feedback saved/)).not.toBeInTheDocument();
});

it('preserves an aborted submission across view navigation without accepting its late success', async () => {
  let finish!: (r: Response) => void;
  const { posts } = mockApi({
    post: async (body) => {
      if (posts.length === 1)
        return new Promise((resolve) => {
          finish = resolve;
        });
      return reply({ ...record, submission_id: body.submission_id });
    },
  });
  render(<App />);
  await connect();
  await ask();
  await rate();
  await userEvent.click(screen.getByRole('button', { name: 'Submit feedback' }));
  await userEvent.click(screen.getByRole('button', { name: 'Browse sources' }));
  await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
  await act(async () => finish(reply({ ...record, submission_id: posts[0].submission_id }, 201)));
  expect(screen.queryByText(/Feedback saved/)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Retry feedback submission' }));
  await screen.findByText(/Feedback saved/);
  expect(posts[1]).toEqual(posts[0]);
});
