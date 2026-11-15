import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import App from './App';

const quote = 'Decision: ship café diagnostics.\r\nKeep original text.';
const original = `👋 Synthetic notes.\r\n\r\n${quote}`;
const evidence = {
  source_document_id: 's1',
  document_version_id: 'v1',
  chunk_id: 'c1',
  title: 'Synthetic decision source',
  external_uri: 'javascript:inert',
  ordinal: 1,
  excerpt: quote,
  start_char: Array.from(original).length - Array.from(quote).length,
  end_char: Array.from(original).length,
};
const proposal = {
  id: 'p1',
  workspace_id: 'w1',
  kind: 'decision',
  statement: quote,
  evidence,
  extraction_method: 'deterministic_source_quotation',
  extractor_version: 'decision-marker-v1',
  created_by: 'u1',
  created_at: '2026-01-01',
  status: 'pending',
  review: null,
  decision_id: null,
};
const decision = {
  id: 'd1',
  workspace_id: 'w1',
  proposal_id: 'p1',
  statement: quote,
  evidence,
  approved_by: 'u1',
  approved_at: '2026-01-02',
  source_is_latest: true,
};
const version = {
  workspace_id: 'w1',
  ...evidence,
  version_number: 1,
  sha256: 'a'.repeat(64),
  ingested_at: '2026-01-01',
  plain_text: original,
  source_is_latest: true,
};
const reply = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
type Override = (url: URL, init: RequestInit) => Promise<Response | undefined>;
function setup(role = 'owner', override?: Override) {
  let current = { ...proposal } as Record<string, unknown>;
  const fetcher = vi.fn(async (path: string, init: RequestInit) => {
    const url = new URL(path, 'http://localhost');
    const custom = await override?.(url, init);
    if (custom) return custom;
    if (url.pathname.includes('/w2/'))
      return reply(url.pathname.endsWith('/decisions') ? { decisions: [] } : { proposals: [] });
    if (url.pathname.endsWith('/me')) return reply({ id: 'u1', name: 'Synthetic member' });
    if (url.pathname.endsWith('/workspaces'))
      return reply({
        workspaces: [
          { id: 'w1', name: 'Aurora', role },
          { id: 'w2', name: 'Orbit', role: 'reader' },
        ],
      });
    if (url.pathname.endsWith('/review')) {
      const body = JSON.parse(init.body as string);
      current = {
        ...proposal,
        status: body.action === 'approve' ? 'approved' : 'rejected',
        decision_id: body.action === 'approve' ? 'd1' : null,
        review: {
          id: 'r1',
          reviewer_id: 'u1',
          action: body.action,
          comment: body.comment ?? null,
          created_at: '2026-01-02',
        },
      };
      return reply(current);
    }
    if (url.pathname.endsWith('/proposals') && init.method === 'POST')
      return reply({ proposals: [current], created_count: 1 });
    if (url.pathname.endsWith('/proposals'))
      return reply({
        proposals:
          url.searchParams.get('status') === 'all' ||
          url.searchParams.get('status') === current.status
            ? [current]
            : [],
      });
    if (url.pathname.endsWith('/proposals/p1')) return reply(current);
    if (url.pathname.endsWith('/decisions')) return reply({ decisions: [decision] });
    if (url.pathname.endsWith('/decisions/d1')) return reply(decision);
    if (url.pathname.endsWith('/sources'))
      return reply({
        sources: [
          {
            ...evidence,
            workspace_id: 'w1',
            latest_version_id: 'v1',
            latest_version_number: 1,
            latest_ingested_at: '2026-01-01',
            created_at: '2026-01-01',
          },
        ],
        has_more: false,
      });
    if (url.pathname.endsWith('/versions')) return reply({ versions: [version], has_more: false });
    if (url.pathname.endsWith('/versions/v1')) return reply(version);
    return reply({}, 404);
  });
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}
async function connect(view = 'Review queue') {
  render(<App />);
  await userEvent.type(screen.getByLabelText('API token'), 'synthetic-token');
  await userEvent.click(screen.getByRole('button', { name: 'Connect' }));
  await screen.findByLabelText('Workspace');
  await userEvent.click(screen.getByRole('button', { name: view }));
}
async function openProposal() {
  await userEvent.click(await screen.findByRole('button', { name: 'Open proposal p1' }));
  await screen.findByTestId('source-text');
}
const reviews = (fetcher: ReturnType<typeof setup>) =>
  fetcher.mock.calls.filter(([p]) => p.endsWith('/review'));

it('requires explicit confirmation, publishes and preserves exact verified source evidence', async () => {
  const fetcher = setup();
  await connect();
  await openProposal();
  expect(screen.getByTestId('source-text').textContent).toBe(original);
  expect(document.querySelector('mark')?.textContent).toBe(quote);
  await userEvent.type(screen.getByLabelText('Review comment'), '  Checked evidence.  ');
  await userEvent.click(screen.getByRole('button', { name: 'Approve' }));
  expect(reviews(fetcher)).toHaveLength(0);
  expect(screen.getByText(/will become a workspace decision/)).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Confirm approve' }));
  await screen.findByText('Review recorded: approved.');
  expect(reviews(fetcher)).toHaveLength(1);
  expect(JSON.parse(reviews(fetcher)[0][1].body as string)).toEqual({
    action: 'approve',
    comment: 'Checked evidence.',
  });
  expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Open published decision' }));
  await screen.findByRole('heading', { name: 'Approved decision' });
  expect(document.querySelector('mark')?.textContent).toBe(quote);
});

it.each(['reader', 'editor'])('limits %s controls and shows decision attribution', async (role) => {
  setup(role);
  await connect('Decisions');
  expect(!!screen.queryByRole('button', { name: 'Review queue' })).toBe(role === 'editor');
  await userEvent.click(await screen.findByRole('button', { name: 'Open decision d1' }));
  await screen.findByTestId('source-text');
  expect(screen.getByText('u1')).toBeVisible();
  expect(screen.queryByLabelText('Review comment')).not.toBeInTheDocument();
  if (role === 'editor') {
    await userEvent.click(screen.getByRole('button', { name: 'Review queue' }));
    await openProposal();
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument();
  }
});

it('blocks stale approval but permits confirmed rejection and cancellation', async () => {
  const fetcher = setup('owner', async (url) =>
    url.pathname.endsWith('/versions/v1')
      ? reply({ ...version, source_is_latest: false })
      : undefined,
  );
  await connect();
  await openProposal();
  expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled();
  await userEvent.click(screen.getByRole('button', { name: 'Reject' }));
  await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(reviews(fetcher)).toHaveLength(0);
  await userEvent.click(screen.getByRole('button', { name: 'Reject' }));
  await userEvent.click(screen.getByRole('button', { name: 'Confirm reject' }));
  await screen.findByText('Review recorded: rejected.');
});

it('generates only on explicit action from the viewed latest source', async () => {
  const fetcher = setup('editor');
  await connect('Browse sources');
  await userEvent.click(
    await screen.findByRole('button', { name: 'Open Synthetic decision source' }),
  );
  await screen.findByTestId('source-text');
  await userEvent.click(screen.getByRole('button', { name: 'Generate proposals' }));
  await screen.findByText('Created 1 new proposal; 1 proposal returned.');
  const call = fetcher.mock.calls.find(
    ([p, i]) => p.includes('/versions/v1/proposals') && i.method === 'POST',
  );
  expect(call?.[1].body).toBeUndefined();
  expect(reviews(fetcher)).toHaveLength(0);
  await userEvent.click(screen.getByRole('button', { name: 'Open review queue' }));
  await screen.findByRole('button', { name: 'Open proposal p1' });
});

it('uses 21-record lookahead and resets detail on status changes', async () => {
  const fetcher = setup('owner', async (url) =>
    url.pathname.endsWith('/proposals')
      ? reply({
          proposals:
            url.searchParams.get('offset') === '20'
              ? []
              : Array.from({ length: 21 }, (_, i) => ({ ...proposal, id: `p${i + 1}` })),
        })
      : undefined,
  );
  await connect();
  const queue = await screen.findByRole('region', { name: 'Proposal catalogue' });
  expect(await within(queue).findAllByRole('button', { name: /^Open proposal/ })).toHaveLength(20);
  expect(fetcher.mock.calls.some(([p]) => p.includes('limit=21'))).toBe(true);
  await userEvent.click(within(queue).getByRole('button', { name: 'Next' }));
  await screen.findByText('No proposals on this page.');
  await userEvent.selectOptions(screen.getByLabelText('Proposal status'), 'all');
  await screen.findByRole('button', { name: 'Open proposal p1' });
  expect(within(queue).getByRole('button', { name: 'Previous' })).toBeDisabled();
});

it('ignores late proposal data after a workspace change', async () => {
  let resolve!: (v: Response) => void;
  setup('owner', async (url) =>
    url.pathname.endsWith('/proposals/p1')
      ? new Promise((done) => {
          resolve = done;
        })
      : undefined,
  );
  await connect();
  await userEvent.click(await screen.findByRole('button', { name: 'Open proposal p1' }));
  await userEvent.selectOptions(screen.getByLabelText('Workspace'), 'w2');
  await act(async () => resolve(reply(proposal)));
  expect(screen.queryByLabelText('Review comment')).not.toBeInTheDocument();
  expect(screen.queryByTestId('source-text')).not.toBeInTheDocument();
});

it.each(['span', 'statement', 'workspace', 'source', 'version'])(
  'blocks approval when %s evidence verification fails',
  async (mismatch) => {
    setup('owner', async (url) => {
      if (url.pathname.endsWith('/proposals/p1') && mismatch === 'statement')
        return reply({ ...proposal, statement: 'Unsupported claim' });
      if (!url.pathname.endsWith('/versions/v1')) return;
      return reply({
        ...version,
        ...(mismatch === 'span' ? { plain_text: 'Mismatched original.' } : {}),
        ...(mismatch === 'workspace' ? { workspace_id: 'w2' } : {}),
        ...(mismatch === 'source' ? { source_document_id: 'other' } : {}),
        ...(mismatch === 'version' ? { document_version_id: 'other' } : {}),
      });
    });
    await connect();
    await userEvent.click(await screen.findByRole('button', { name: 'Open proposal p1' }));
    const approve = await screen.findByRole('button', { name: 'Approve' });
    expect(approve).toBeDisabled();
    if (['workspace', 'source', 'version'].includes(mismatch)) {
      await screen.findByRole('alert');
      expect(screen.queryByTestId('source-text')).not.toBeInTheDocument();
    } else await screen.findByTestId('source-text');
  },
);

it('validates comments by Unicode characters, omits blanks and invalidates confirmation on edit', async () => {
  const fetcher = setup();
  await connect();
  await openProposal();
  const comment = screen.getByLabelText('Review comment');
  fireEvent.change(comment, { target: { value: '👋'.repeat(1001) } });
  expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled();
  fireEvent.change(comment, { target: { value: 'a\0b' } });
  expect(screen.getByRole('button', { name: 'Reject' })).toBeDisabled();
  fireEvent.change(comment, { target: { value: '👋'.repeat(1000) } });
  expect(screen.getByRole('button', { name: 'Approve' })).toBeEnabled();
  await userEvent.click(screen.getByRole('button', { name: 'Approve' }));
  fireEvent.change(comment, { target: { value: '  ' } });
  expect(screen.queryByRole('button', { name: 'Confirm approve' })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Reject' }));
  await userEvent.click(screen.getByRole('button', { name: 'Confirm reject' }));
  await screen.findByText('Review recorded: rejected.');
  expect(JSON.parse(reviews(fetcher)[0][1].body as string)).toEqual({ action: 'reject' });
});

it.each([0, 1, 2])('reports extraction outcome %s without automatic approval', async (outcome) => {
  const fetcher = setup('editor', async (url, init) =>
    url.pathname.endsWith('/proposals') && init.method === 'POST'
      ? reply({ created_count: outcome === 1 ? 1 : 0, proposals: outcome === 0 ? [] : [proposal] })
      : undefined,
  );
  await connect('Browse sources');
  await userEvent.click(
    await screen.findByRole('button', { name: 'Open Synthetic decision source' }),
  );
  await screen.findByTestId('source-text');
  await userEvent.click(screen.getByRole('button', { name: 'Generate proposals' }));
  await screen.findByText(
    outcome === 0
      ? /No decision proposals matched/
      : outcome === 1
        ? /Created 1 new proposal/
        : /Existing proposals and review history were preserved/,
  );
  expect(reviews(fetcher)).toHaveLength(0);
});

it('keeps the original source after a generation freshness conflict and offers catalogue refresh', async () => {
  setup('editor', async (url, init) =>
    url.pathname.endsWith('/proposals') && init.method === 'POST' ? reply({}, 409) : undefined,
  );
  await connect('Browse sources');
  await userEvent.click(
    await screen.findByRole('button', { name: 'Open Synthetic decision source' }),
  );
  await screen.findByTestId('source-text');
  await userEvent.click(screen.getByRole('button', { name: 'Generate proposals' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/newer version/);
  expect(screen.getByTestId('source-text').textContent).toBe(original);
  expect(screen.getByRole('button', { name: 'Generate proposals' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Retry' })).toBeVisible();
});

it.each([409, 503, 'network'])(
  'reconciles review outcome %s without repeating the write',
  async (failure) => {
    let attempted = false;
    const terminal = {
      ...proposal,
      status: 'approved',
      decision_id: 'd1',
      review: {
        id: 'r2',
        reviewer_id: 'another-owner',
        action: 'approve',
        comment: '<script>inert</script>',
        created_at: '2026-02-02',
      },
    };
    const fetcher = setup('owner', async (url) => {
      if (url.pathname.endsWith('/review')) {
        attempted = true;
        if (typeof failure === 'string') throw new TypeError('connection lost');
        return reply({}, failure);
      }
      if (url.pathname.endsWith('/proposals/p1') && attempted) return reply(terminal);
    });
    await connect();
    await openProposal();
    await userEvent.click(screen.getByRole('button', { name: 'Approve' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirm approve' }));
    expect(await screen.findByText('another-owner')).toBeVisible();
    await screen.findByTestId('source-text');
    expect(reviews(fetcher)).toHaveLength(1);
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument();
    expect(document.querySelector('script')).toBeNull();
  },
);

it('requires reconfirmation after an uncertain pending review and a failed reconciliation', async () => {
  let attempted = false,
    reads = 0;
  const fetcher = setup('owner', async (url) => {
    if (url.pathname.endsWith('/review')) {
      attempted = true;
      return reply({}, 503);
    }
    if (attempted && url.pathname.endsWith('/proposals/p1') && ++reads === 1) return reply({}, 503);
  });
  await connect();
  await openProposal();
  await userEvent.click(screen.getByRole('button', { name: 'Reject' }));
  await userEvent.click(screen.getByRole('button', { name: 'Confirm reject' }));
  await screen.findByRole('alert');
  expect(screen.getByRole('button', { name: 'Reject' })).toBeDisabled();
  await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
  await screen.findByTestId('source-text');
  expect(screen.getByRole('button', { name: 'Reject' })).toBeEnabled();
  expect(screen.queryByRole('button', { name: 'Confirm reject' })).not.toBeInTheDocument();
  expect(reviews(fetcher)).toHaveLength(1);
});

it('preserves a saved review when catalogue refresh fails and retries only the read', async () => {
  let lists = 0;
  const fetcher = setup('owner', async (url) =>
    url.pathname.endsWith('/proposals') && ++lists === 2 ? reply({}, 503) : undefined,
  );
  await connect();
  await openProposal();
  await userEvent.click(screen.getByRole('button', { name: 'Approve' }));
  await userEvent.click(screen.getByRole('button', { name: 'Confirm approve' }));
  await screen.findByText('Review recorded: approved.');
  await screen.findByRole('alert');
  expect(screen.getByRole('button', { name: 'Open published decision' })).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
  await screen.findByText('No pending proposals.');
  expect(screen.getByText('Review recorded: approved.')).toBeVisible();
  expect(reviews(fetcher)).toHaveLength(1);
});

it('refills and backtracks a pending queue after reconciliation discovers a terminal review', async () => {
  let attempted = false;
  setup('owner', async (url) => {
    if (url.pathname.endsWith('/review')) {
      attempted = true;
      return reply({}, 503);
    }
    if (url.pathname.endsWith('/proposals/p1') && attempted)
      return reply({
        ...proposal,
        status: 'rejected',
        review: {
          id: 'r1',
          reviewer_id: 'another-owner',
          action: 'reject',
          comment: null,
          created_at: '2026-02-01',
        },
      });
    if (url.pathname.endsWith('/proposals'))
      return reply({
        proposals:
          url.searchParams.get('offset') === '20'
            ? attempted
              ? []
              : [proposal]
            : attempted
              ? [{ ...proposal, id: 'p2' }]
              : Array.from({ length: 21 }, (_, i) => ({ ...proposal, id: `p${i + 2}` })),
      });
  });
  await connect();
  const catalogue = screen.getByRole('region', { name: 'Proposal catalogue' });
  await userEvent.click(await within(catalogue).findByRole('button', { name: 'Next' }));
  await openProposal();
  await userEvent.click(screen.getByRole('button', { name: 'Reject' }));
  await userEvent.click(screen.getByRole('button', { name: 'Confirm reject' }));
  await screen.findByText('another-owner');
  await within(catalogue).findByRole('button', { name: 'Open proposal p2' });
  expect(
    within(catalogue).queryByRole('button', { name: 'Open proposal p1' }),
  ).not.toBeInTheDocument();
  expect(within(catalogue).getByRole('button', { name: 'Previous' })).toBeDisabled();
});

it.each(
  ['view', 'workspace', 'logout'].flatMap((change) =>
    [200, 401, 404].map((status) => ({ change, status })),
  ),
)(
  'ignores a late review $status after changing $change and prevents duplicate submission',
  async ({ change, status }) => {
    let resolve!: (r: Response) => void;
    const fetcher = setup('owner', async (url) =>
      url.pathname.endsWith('/review')
        ? new Promise((done) => {
            resolve = done;
          })
        : undefined,
    );
    await connect();
    await openProposal();
    await userEvent.type(screen.getByLabelText('Review comment'), 'private draft');
    await userEvent.click(screen.getByRole('button', { name: 'Approve' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirm approve' }));
    expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled();
    if (change === 'view') await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
    if (change === 'workspace')
      await userEvent.selectOptions(screen.getByLabelText('Workspace'), 'w2');
    if (change === 'logout')
      await userEvent.click(screen.getByRole('button', { name: 'Disconnect' }));
    await act(async () => resolve(reply({ ...proposal, status: 'approved' }, status)));
    expect(screen.queryByText('private draft')).not.toBeInTheDocument();
    expect(screen.queryByTestId('source-text')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(reviews(fetcher)).toHaveLength(1);
    if (change === 'view') {
      await userEvent.click(screen.getByRole('button', { name: 'Review queue' }));
      await openProposal();
      expect(screen.getByLabelText('Review comment')).toHaveValue('');
    }
  },
);

it('clears drafts, source and owner controls when review detects demotion to reader', async () => {
  let demoted = false;
  setup('owner', async (url) => {
    if (url.pathname.endsWith('/review')) {
      demoted = true;
      return reply({}, 403);
    }
    if (demoted && url.pathname.endsWith('/workspaces'))
      return reply({ workspaces: [{ id: 'w1', name: 'Aurora', role: 'reader' }] });
  });
  await connect();
  await openProposal();
  await userEvent.type(screen.getByLabelText('Review comment'), 'private draft');
  await userEvent.click(screen.getByRole('button', { name: 'Approve' }));
  await userEvent.click(screen.getByRole('button', { name: 'Confirm approve' }));
  await screen.findByRole('heading', { name: 'Approved decisions' });
  expect(screen.queryByRole('button', { name: 'Review queue' })).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Review comment')).not.toBeInTheDocument();
  expect(screen.queryByTestId('source-text')).not.toBeInTheDocument();
});
