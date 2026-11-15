import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { expect, test as base } from '@playwright/test';

interface Seed {
  ownerToken: string;
  readerToken: string;
  editorToken: string;
  readerTokenId: string;
  workspaces: string[];
  users: string[];
}

async function connectBrowser(
  page: import('@playwright/test').Page,
  token: string,
  workspace: string,
) {
  await page.goto('/');
  await page.getByLabel('API token').fill(token);
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await expect(page.getByLabel('Workspace', { exact: true })).toBeVisible();
  await page.getByLabel('Workspace', { exact: true }).selectOption(workspace);
  await expect(page.getByLabel('Workspace', { exact: true })).toHaveValue(workspace);
}
function provision(payload: object) {
  const result = spawnSync('uv', ['run', 'python', 'apps/web/e2e/fixtures.py'], {
    cwd: fileURLToPath(new URL('../../../', import.meta.url)),
    input: JSON.stringify(payload),
    encoding: 'utf8',
    env: process.env,
  });
  if (result.status !== 0)
    throw new Error(
      'Browser fixture command failed; check E2E_DATABASE_URL and database migrations.',
    );
  return JSON.parse(result.stdout);
}

const test = base.extend<{ seed: Seed }>({
  seed: async ({ baseURL }, provide) => {
    if (!baseURL) throw new Error('Configure a browser test baseURL.');
    const seed = provision({ action: 'create' }) as Seed;
    try {
      await provide(seed);
    } finally {
      provision({ action: 'cleanup', users: seed.users, workspaces: seed.workspaces });
    }
  },
});

test('browser uploads preserve bytes, answer citations and historical version identity', async ({
  page,
  request,
  seed,
}) => {
  const workspace = seed.workspaces[0];
  const root = `/api/v1/workspaces/${workspace}`;
  const original =
    '👋 Synthetic café notes.\r\n\r\nDecision: preserve syntheticquartz evidence.\r\n<img src=x onerror=alert(1)>\r\n';
  const changed = 'Decision: keep currentnebula evidence.\r\n';
  await connectBrowser(page, seed.editorToken, workspace);
  await page.getByRole('button', { name: 'Browse sources', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Add source', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Add source', exact: true }).focus();
  await page.keyboard.press('Enter');
  await page.getByLabel('Source title', { exact: true }).fill('Synthetic Task008 upload');
  await page.getByLabel('Source URI (optional)', { exact: true }).fill('javascript:inert-upload');
  await page
    .getByLabel('Source file', { exact: true })
    .setInputFiles({ name: 'notes.MD', mimeType: 'text/markdown', buffer: Buffer.from(original) });
  if (process.env.E2E_UPLOAD_SCREENSHOT_PATH)
    await page.screenshot({ path: process.env.E2E_UPLOAD_SCREENSHOT_PATH, fullPage: true });
  const headers = { Authorization: `Bearer ${seed.editorToken}` };
  expect((await (await request.get(`${root}/sources`, { headers })).json()).sources).toHaveLength(
    0,
  );
  const posted = page.waitForResponse(
    (response) => response.request().method() === 'POST' && response.url().endsWith('/sources'),
  );
  await page.getByRole('button', { name: 'Upload source', exact: true }).click();
  const firstResponse = await posted;
  expect(firstResponse.status()).toBe(201);
  const first = await firstResponse.json();
  await expect(page.getByText('Source saved: version 1.', { exact: true })).toBeVisible();
  await expect(page.getByTestId('source-text')).toBeVisible();
  expect(await page.getByTestId('source-text').textContent()).toBe(original);
  await expect(
    page.getByRole('heading', { name: 'Synthetic Task008 upload', exact: true }),
  ).toBeFocused();
  await expect(page.locator('.source-text img')).toHaveCount(0);
  await page.getByRole('button', { name: 'Ask', exact: true }).click();
  await page.getByLabel('Your question', { exact: true }).fill('syntheticquartz');
  await page.getByRole('button', { name: 'Ask question', exact: true }).click();
  await page.getByRole('button', { name: '[1] Synthetic Task008 upload', exact: true }).click();
  expect(await page.getByTestId('source-text').textContent()).toBe(original);
  await expect(page.locator('mark')).toContainText('syntheticquartz');
  await page.getByRole('button', { name: 'Browse sources', exact: true }).click();
  await page.getByRole('button', { name: 'Open Synthetic Task008 upload', exact: true }).click();
  await page.getByRole('button', { name: 'Upload new version', exact: true }).click();
  await expect(page.getByLabel('Source title', { exact: true })).toHaveCount(0);
  await page
    .getByLabel('Source file', { exact: true })
    .setInputFiles({ name: 'new.txt', mimeType: 'text/plain', buffer: Buffer.from(changed) });
  await page.getByRole('button', { name: 'Upload version', exact: true }).click();
  await expect(page.getByText('Source saved: version 2.', { exact: true })).toBeVisible();
  await expect(page.getByTestId('source-text')).toHaveText(changed);
  await page.getByRole('button', { name: 'Upload new version', exact: true }).click();
  await page
    .getByLabel('Source file', { exact: true })
    .setInputFiles({ name: 'old.txt', mimeType: 'text/plain', buffer: Buffer.from(original) });
  const reposted = page.waitForResponse(
    (response) => response.request().method() === 'POST' && response.url().endsWith('/versions'),
  );
  await page.getByRole('button', { name: 'Upload version', exact: true }).click();
  const duplicateResponse = await reposted;
  expect(duplicateResponse.status()).toBe(200);
  expect(await duplicateResponse.json()).toEqual({ ...first, duplicate: true });
  await expect(
    page.getByText('Existing content reused: version 1.', { exact: true }),
  ).toBeVisible();
  await expect(page.getByText('Historical version', { exact: true })).toBeVisible();
  expect(await page.getByTestId('source-text').textContent()).toBe(original);
  const catalogue = await (await request.get(`${root}/sources`, { headers })).json();
  expect(catalogue.sources).toHaveLength(1);
  expect(catalogue.sources[0].latest_version_number).toBe(2);
  expect(
    (await (await request.get(`${root}/proposals`, { headers })).json()).proposals,
  ).toHaveLength(0);
  await page.getByRole('button', { name: 'Ask', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Quoted source evidence', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Disconnect', exact: true }).click();

  await page.setViewportSize({ width: 390, height: 844 });
  await connectBrowser(page, seed.readerToken, workspace);
  await page.getByRole('button', { name: 'Browse sources', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Add source', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Open Synthetic Task008 upload', exact: true }).click();
  await expect(page.getByTestId('source-text')).toHaveText(changed);
  await expect(page.getByRole('button', { name: 'Upload new version', exact: true })).toHaveCount(
    0,
  );
  await expect(page.getByRole('button', { name: 'Open version 1', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Open version 1', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Historical version', { exact: true })).toBeVisible();
  expect(await page.getByTestId('source-text').textContent()).toBe(original);
  await page.getByText('Source details', { exact: true }).click();
  await expect(page.getByText('javascript:inert-upload', { exact: true })).toBeVisible();
  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
  const readerHeaders = { Authorization: `Bearer ${seed.readerToken}` };
  expect(
    (
      await request.post(`${root}/sources`, {
        headers: readerHeaders,
        multipart: {
          title: 'Forbidden',
          file: {
            name: 'no.txt',
            mimeType: 'text/plain',
            buffer: Buffer.from('Synthetic forbidden'),
          },
        },
      })
    ).status(),
  ).toBe(403);
  expect(
    (
      await request.post(`${root}/sources/${first.source_document_id}/versions`, {
        headers: readerHeaders,
        multipart: {
          file: {
            name: 'no.txt',
            mimeType: 'text/plain',
            buffer: Buffer.from('Synthetic forbidden'),
          },
        },
      })
    ).status(),
  ).toBe(403);
  expect(
    (
      await request.get(
        `/api/v1/workspaces/${seed.workspaces[1]}/sources/${first.source_document_id}/versions/${first.document_version_id}`,
        { headers: { Authorization: `Bearer ${seed.ownerToken}` } },
      )
    ).status(),
  ).toBe(404);
});

test('browser upload rejects invalid UTF-8 and clears drafts after editor demotion', async ({
  page,
  request,
  seed,
}) => {
  const workspace = seed.workspaces[0];
  const root = `/api/v1/workspaces/${workspace}`;
  await connectBrowser(page, seed.editorToken, workspace);
  await page.getByRole('button', { name: 'Browse sources', exact: true }).click();
  await page.getByRole('button', { name: 'Add source', exact: true }).click();
  await page.getByLabel('Source title', { exact: true }).fill('Synthetic invalid text');
  await page
    .getByLabel('Source file', { exact: true })
    .setInputFiles({ name: 'invalid.txt', mimeType: 'text/plain', buffer: Buffer.from([0xff]) });
  await page.getByRole('button', { name: 'Upload source', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('nonblank UTF-8 text');
  await expect(page.getByLabel('Source title', { exact: true })).toHaveValue(
    'Synthetic invalid text',
  );
  const headers = { Authorization: `Bearer ${seed.ownerToken}` };
  expect((await (await request.get(`${root}/sources`, { headers })).json()).sources).toHaveLength(
    0,
  );
  expect(
    (
      await request.put(`${root}/members/${seed.users[2]}`, { headers, data: { role: 'reader' } })
    ).status(),
  ).toBe(200);
  await page.getByLabel('Source file', { exact: true }).setInputFiles({
    name: 'valid.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Synthetic valid text'),
  });
  await page.getByRole('button', { name: 'Upload source', exact: true }).click();
  await expect(page.getByText('reader access', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Source file', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Add source', exact: true })).toHaveCount(0);
});

test('editor generates, owner confirms review with a concurrent source update, reader verifies historical decision', async ({
  page,
  request,
  seed,
}) => {
  const workspace = seed.workspaces[0];
  const root = `/api/v1/workspaces/${workspace}`;
  const first = 'Decision: ship café diagnostics.\r\nPreserve evidence.';
  const second = 'We decided to defer alerting.';
  const original = `👋 Synthetic Task007 notes.\r\n\r\n${first}\r\n\r\n${second}`;
  const headers = { Authorization: `Bearer ${seed.ownerToken}` };
  const uploaded = await request.post(`${root}/sources`, {
    headers,
    multipart: {
      title: 'Synthetic Task007 decision notes',
      external_uri: 'javascript:inert-decision-metadata',
      file: { name: 'decisions.txt', mimeType: 'text/plain', buffer: Buffer.from(original) },
    },
  });
  expect(uploaded.status()).toBe(201);
  const receipt = await uploaded.json();
  await connectBrowser(page, seed.editorToken, workspace);
  await page.getByRole('button', { name: 'Browse sources', exact: true }).click();
  await page
    .getByRole('button', { name: 'Open Synthetic Task007 decision notes', exact: true })
    .click();
  await expect(page.getByTestId('source-text')).toHaveText(original);
  await page.getByRole('button', { name: 'Generate proposals', exact: true }).click();
  await expect(
    page.getByText('Created 2 new proposals; 2 proposals returned.', { exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Generate proposals', exact: true }).click();
  await expect(
    page.getByText(/Existing proposals and review history were preserved/),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Open review queue', exact: true }).click();
  const generated = await (await request.get(`${root}/proposals`, { headers })).json();
  const proposalA = generated.proposals.find((p: { statement: string }) => p.statement === first);
  const proposalB = generated.proposals.find((p: { statement: string }) => p.statement === second);
  await page.getByRole('button', { name: `Open proposal ${proposalA.id}`, exact: true }).click();
  await expect(page.getByTestId('source-text')).toHaveText(original);
  await expect(page.getByRole('button', { name: 'Approve', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Disconnect', exact: true }).click();

  await connectBrowser(page, seed.ownerToken, workspace);
  await page.getByRole('button', { name: 'Review queue', exact: true }).click();
  await page.getByRole('button', { name: `Open proposal ${proposalA.id}`, exact: true }).click();
  await expect(page.getByRole('button', { name: 'Approve', exact: true })).toBeEnabled();
  await page.getByLabel('Review comment', { exact: true }).fill('Synthetic human review.');
  await page.getByRole('button', { name: 'Approve', exact: true }).click();
  expect((await (await request.get(`${root}/decisions`, { headers })).json()).decisions).toEqual(
    [],
  );
  await page.getByRole('button', { name: 'Confirm approve', exact: true }).click();
  await expect(page.getByText('Review recorded: approved.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: `Open proposal ${proposalB.id}`, exact: true }).click();
  await expect(page.getByRole('button', { name: 'Approve', exact: true })).toBeEnabled();
  expect(
    (
      await request.post(`${root}/sources/${receipt.source_document_id}/versions`, {
        headers,
        multipart: {
          file: {
            name: 'updated.txt',
            mimeType: 'text/plain',
            buffer: Buffer.from('Decision: a newer synthetic strategy.'),
          },
        },
      })
    ).status(),
  ).toBe(201);
  await page.getByRole('button', { name: 'Approve', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm approve', exact: true }).click();
  await expect(page.getByText(/Review conflict/)).toBeVisible();
  await expect(page.getByText('Historical version', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Approve', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Reject', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm reject', exact: true }).click();
  await expect(page.getByText('Review recorded: rejected.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Disconnect', exact: true }).click();

  await page.setViewportSize({ width: 390, height: 844 });
  await connectBrowser(page, seed.readerToken, workspace);
  await page.getByRole('button', { name: 'Decisions', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Review queue', exact: true })).toHaveCount(0);
  const decisions = await (await request.get(`${root}/decisions`, { headers })).json();
  expect(decisions.decisions).toHaveLength(1);
  await page
    .getByRole('button', { name: `Open decision ${decisions.decisions[0].id}`, exact: true })
    .focus();
  await page.keyboard.press('Enter');
  await expect(
    page.getByRole('heading', { name: 'Synthetic Task007 decision notes', exact: true }),
  ).toBeFocused();
  expect(await page.getByTestId('source-text').textContent()).toBe(original);
  expect(await page.locator('mark').textContent()).toBe(first);
  await expect(page.getByText('Historical version', { exact: true })).toBeVisible();
  await page.getByText('Source details', { exact: true }).click();
  await expect(page.getByText('javascript:inert-decision-metadata', { exact: true })).toBeVisible();
  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
  expect(
    (
      await request.get(`${root}/proposals`, {
        headers: { Authorization: `Bearer ${seed.readerToken}` },
      })
    ).status(),
  ).toBe(403);
  expect(
    (
      await request.get(
        `/api/v1/workspaces/${seed.workspaces[1]}/decisions/${decisions.decisions[0].id}`,
        { headers },
      )
    ).status(),
  ).toBe(404);
  if (process.env.E2E_DECISION_SCREENSHOT_PATH)
    await page.screenshot({ path: process.env.E2E_DECISION_SCREENSHOT_PATH, fullPage: true });
  provision({ action: 'revoke', tokenId: seed.readerTokenId });
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  await expect(page.getByLabel('API token')).toHaveValue('');
  await expect(page.getByTestId('source-text')).toHaveCount(0);
});

test('owner demotion clears the review draft and removes authoritative controls', async ({
  page,
  request,
  seed,
}) => {
  const root = `/api/v1/workspaces/${seed.workspaces[0]}`;
  const headers = { Authorization: `Bearer ${seed.ownerToken}` };
  const receipt = await (
    await request.post(`${root}/sources`, {
      headers,
      multipart: {
        title: 'Synthetic demotion evidence',
        file: {
          name: 'decision.txt',
          mimeType: 'text/plain',
          buffer: Buffer.from('Decision: test membership changes.'),
        },
      },
    })
  ).json();
  const generated = await (
    await request.post(
      `${root}/sources/${receipt.source_document_id}/versions/${receipt.document_version_id}/proposals`,
      { headers },
    )
  ).json();
  await connectBrowser(page, seed.ownerToken, seed.workspaces[0]);
  await page.getByRole('button', { name: 'Review queue', exact: true }).click();
  await page
    .getByRole('button', { name: `Open proposal ${generated.proposals[0].id}`, exact: true })
    .click();
  await expect(page.getByRole('button', { name: 'Approve', exact: true })).toBeEnabled();
  await page.getByLabel('Review comment', { exact: true }).fill('Synthetic private review draft.');
  expect(
    (
      await request.put(`${root}/members/${seed.users[2]}`, { headers, data: { role: 'owner' } })
    ).status(),
  ).toBe(200);
  expect(
    (
      await request.put(`${root}/members/${seed.users[0]}`, { headers, data: { role: 'reader' } })
    ).status(),
  ).toBe(200);
  await page.getByRole('button', { name: 'Approve', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm approve', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Approved decisions', exact: true }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: 'Review queue', exact: true })).toHaveCount(0);
  await expect(page.getByLabel('Review comment', { exact: true })).toHaveCount(0);
  await expect(page.getByTestId('source-text')).toHaveCount(0);
  expect((await (await request.get(`${root}/decisions`, { headers })).json()).decisions).toEqual(
    [],
  );
});

test('reader asks, verifies pinned evidence after an update, and cannot read a foreign workspace', async ({
  page,
  request,
  seed,
}) => {
  const original =
    '👋 Synthetic café notes.\r\n\r\nTroubleshooting acceleration reduces incident recovery time.\r\n';
  const quote = 'Troubleshooting acceleration reduces incident recovery time.';
  const upload = async (workspace: string, content: string, sourceId?: string) => {
    const result = await request.post(
      `/api/v1/workspaces/${workspace}/sources${sourceId ? `/${sourceId}/versions` : ''}`,
      {
        headers: { Authorization: `Bearer ${seed.ownerToken}` },
        multipart: {
          ...(sourceId
            ? {}
            : {
                title: 'Synthetic incident strategy',
                external_uri: 'javascript:inert-source-metadata',
              }),
          file: { name: 'synthetic.txt', mimeType: 'text/plain', buffer: Buffer.from(content) },
        },
      },
    );
    expect(result.status()).toBe(201);
    return result.json();
  };
  const receipt = await upload(seed.workspaces[0], original);
  const foreign = await upload(seed.workspaces[1], 'Foreign synthetic evidence.');
  await page.goto('/');
  await page.getByLabel('API token').fill(seed.readerToken);
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await expect(page.getByLabel('Workspace', { exact: true })).toHaveValue(seed.workspaces[0]);
  await expect(page.getByLabel('Workspace', { exact: true }).locator('option')).toHaveCount(1);
  await page.getByLabel('Your question').fill('troubleshooting acceleration');
  await page.getByRole('button', { name: 'Ask question', exact: true }).click();
  const citation = page.getByRole('button', {
    name: '[1] Synthetic incident strategy',
    exact: true,
  });
  await expect(citation).toBeVisible();
  await upload(
    seed.workspaces[0],
    'New synthetic strategy replaces the original.',
    receipt.source_document_id,
  );
  await citation.click();
  await expect(page.getByText('Historical version', { exact: true })).toBeVisible();
  expect(await page.getByTestId('source-text').textContent()).toBe(original);
  expect(await page.locator('mark').textContent()).toBe(quote);
  await expect(
    page.getByRole('heading', { name: 'Synthetic incident strategy', exact: true }),
  ).toBeFocused();
  await page.getByText('Source details', { exact: true }).click();
  await expect(page.getByText('javascript:inert-source-metadata', { exact: true })).toBeVisible();
  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0);
  const denied = await request.get(
    `/api/v1/workspaces/${seed.workspaces[1]}/sources/${foreign.source_document_id}/versions/${foreign.document_version_id}`,
    {
      headers: { Authorization: `Bearer ${seed.readerToken}` },
    },
  );
  expect(denied.status()).toBe(404);
  const mismatch = await request.get(
    `/api/v1/workspaces/${seed.workspaces[0]}/sources/${foreign.source_document_id}/versions/${foreign.document_version_id}`,
    {
      headers: { Authorization: `Bearer ${seed.readerToken}` },
    },
  );
  expect(mismatch.status()).toBe(404);
  expect(
    await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length })),
  ).toEqual({ local: 0, session: 0 });
  if (process.env.E2E_SCREENSHOT_PATH)
    await page.screenshot({ path: process.env.E2E_SCREENSHOT_PATH, fullPage: true });
  await page.reload();
  await expect(page.getByLabel('API token')).toHaveValue('');
  await expect(page.getByTestId('source-text')).toHaveCount(0);
});

test('missing evidence, unavailable semantic mode, and token revocation are explicit', async ({
  page,
  seed,
}) => {
  await page.goto('/');
  await page.getByLabel('API token').fill(seed.readerToken);
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await page.getByLabel('Your question').fill('nonexistentplatypus');
  await page.getByRole('button', { name: 'Ask question', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Insufficient evidence', exact: true }),
  ).toBeVisible();
  await page.getByLabel('Retrieval mode').selectOption('semantic');
  await page.getByRole('button', { name: 'Ask question', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('retrieval mode is unavailable');
  await expect(page.getByLabel('Retrieval mode')).toHaveValue('semantic');
  provision({ action: 'revoke', tokenId: seed.readerTokenId });
  await page.getByRole('button', { name: 'Ask question', exact: true }).click();
  await expect(page.getByLabel('API token')).toHaveValue('');
  await expect(page.getByRole('alert')).toContainText('Connect again');
});

test('connection works by keyboard at a narrow viewport', async ({ page, seed }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByLabel('API token').focus();
  await page.keyboard.type(seed.readerToken);
  await page.keyboard.press('Enter');
  await expect(page.getByLabel('Workspace', { exact: true })).toBeVisible();
  await page.getByLabel('Your question').fill('nonexistentplatypus');
  await page.getByRole('button', { name: 'Ask question', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Insufficient evidence', exact: true }),
  ).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.getByRole('button', { name: 'Disconnect' }).click();
  await expect(page.getByLabel('API token')).toHaveValue('');
});

test('reader browses, filters literal titles, and opens exact historical text without citation marks', async ({
  page,
  request,
  seed,
}) => {
  const original = '👋 Synthetic café notes.\r\n\r\nOriginal browser evidence.\r\n';
  const upload = async (title: string, content: string, sourceId?: string) => {
    const response = await request.post(
      `/api/v1/workspaces/${seed.workspaces[0]}/sources${sourceId ? `/${sourceId}/versions` : ''}`,
      {
        headers: { Authorization: `Bearer ${seed.ownerToken}` },
        multipart: {
          ...(sourceId ? {} : { title, external_uri: 'javascript:inert-browser-metadata' }),
          file: { name: 'synthetic.txt', mimeType: 'text/plain', buffer: Buffer.from(content) },
        },
      },
    );
    expect(response.status()).toBe(201);
    return response.json();
  };
  const receipt = await upload('Synthetic roadmap 100%_ready', original);
  await upload('', 'Updated browser evidence.', receipt.source_document_id);
  // The target source is beyond the first catalogue page.
  for (let i = 0; i < 20; i++)
    await upload(`Synthetic catalogue document ${i}`, `Synthetic body ${i}.`);
  await page.goto('/');
  await page.getByLabel('API token').fill(seed.readerToken);
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await page.getByRole('button', { name: 'Browse sources', exact: true }).click();
  const catalogue = page.getByRole('region', { name: 'Source catalogue', exact: true });
  await expect(catalogue.getByRole('button', { name: /^Open Synthetic/ })).toHaveCount(20);
  await catalogue.getByRole('button', { name: 'Next', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Open Synthetic roadmap 100%_ready', exact: true }),
  ).toBeVisible();
  await page.getByLabel('Filter by title').fill('%_');
  await page.getByRole('button', { name: 'Apply filter', exact: true }).click();
  await expect(catalogue.getByRole('button', { name: /^Open Synthetic/ })).toHaveCount(1);
  await expect(catalogue.getByRole('button', { name: 'Previous', exact: true })).toBeDisabled();
  await page
    .getByRole('button', { name: 'Open Synthetic roadmap 100%_ready', exact: true })
    .click();
  await expect(page.getByTestId('source-text')).toHaveText('Updated browser evidence.');
  await page.getByRole('button', { name: 'Open version 1', exact: true }).click();
  await expect(page.getByText('Historical version', { exact: true })).toBeVisible();
  expect(await page.getByTestId('source-text').textContent()).toBe(original);
  await expect(page.locator('mark')).toHaveCount(0);
  await expect(
    page.getByRole('heading', { name: 'Synthetic roadmap 100%_ready', exact: true }),
  ).toBeFocused();
  await page.getByText('Source details', { exact: true }).click();
  await expect(page.getByText('javascript:inert-browser-metadata', { exact: true })).toBeVisible();
  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0);
  await expect(page.getByText('Chunk ID', { exact: true })).toHaveCount(0);
  if (process.env.E2E_SOURCE_BROWSER_SCREENSHOT_PATH)
    await page.screenshot({ path: process.env.E2E_SOURCE_BROWSER_SCREENSHOT_PATH, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  const filter = page.getByLabel('Filter by title');
  await filter.focus();
  await filter.fill('no-matching-title');
  await page.keyboard.press('Enter');
  await expect(page.getByText('No titles match this filter.', { exact: true })).toBeVisible();
  await expect(page.getByTestId('source-text')).toHaveCount(0);
  expect(
    await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length })),
  ).toEqual({ local: 0, session: 0 });
  await page.reload();
  await expect(page.getByLabel('API token')).toHaveValue('');
});

test('browsing clears source state when workspace membership is removed', async ({
  page,
  request,
  seed,
}) => {
  const upload = await request.post(`/api/v1/workspaces/${seed.workspaces[0]}/sources`, {
    headers: { Authorization: `Bearer ${seed.ownerToken}` },
    multipart: {
      title: 'Synthetic revoked guide',
      file: {
        name: 'synthetic.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('Synthetic revocation evidence.'),
      },
    },
  });
  expect(upload.status()).toBe(201);
  await page.goto('/');
  await page.getByLabel('API token').fill(seed.readerToken);
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await page.getByRole('button', { name: 'Browse sources', exact: true }).click();
  await page.getByRole('button', { name: 'Open Synthetic revoked guide', exact: true }).click();
  await expect(page.getByTestId('source-text')).toHaveText('Synthetic revocation evidence.');
  const removed = await request.delete(
    `/api/v1/workspaces/${seed.workspaces[0]}/members/${seed.users[1]}`,
    { headers: { Authorization: `Bearer ${seed.ownerToken}` } },
  );
  expect(removed.status()).toBe(204);
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'No workspaces yet', exact: true })).toBeVisible();
  await expect(page.getByTestId('source-text')).toHaveCount(0);
  await expect(
    page.getByRole('button', { name: 'Open Synthetic revoked guide', exact: true }),
  ).toHaveCount(0);
});
