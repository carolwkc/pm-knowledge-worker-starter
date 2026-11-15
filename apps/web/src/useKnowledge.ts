import { useEffect, useRef, useState } from 'react';
import {
  api,
  ApiError,
  type Answer,
  type Citation,
  type RetrievalMode,
  type SourceVersion,
  type SourceRef,
  type SourceSummary,
  type SourceVersionSummary,
  type User,
  type Workspace,
} from './api';

interface Session {
  token: string;
  user: User;
}
export interface OpenSource {
  version: SourceVersion;
  citation: Citation | null;
}

export interface BrowserState {
  sources: SourceSummary[];
  hasMore: boolean;
  title: string;
  filterDraft: string;
  offset: number;
  loaded: boolean;
  selected: SourceSummary | null;
  versions: SourceVersionSummary[];
  versionsHasMore: boolean;
  versionsLoaded: boolean;
  versionOffset: number;
}

function emptyBrowser(): BrowserState {
  return {
    sources: [],
    hasMore: false,
    title: '',
    filterDraft: '',
    offset: 0,
    loaded: false,
    selected: null,
    versions: [],
    versionsHasMore: false,
    versionsLoaded: false,
    versionOffset: 0,
  };
}

class SourceMismatch extends Error {}

export function useKnowledge() {
  const [session, setSession] = useState<Session | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState('');
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState<RetrievalMode>('keyword');
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [source, setSource] = useState<OpenSource | null>(null);
  const [view, setView] = useState<'ask' | 'browse'>('ask');
  const [browser, setBrowser] = useState<BrowserState>(emptyBrowser);
  const [busy, setBusy] = useState<'connect' | 'ask' | 'source' | 'catalogue' | 'history' | null>(
    null,
  );
  const [error, setError] = useState('');
  const [retry, setRetry] = useState<(() => void) | null>(null);
  const pending = useRef<AbortController | null>(null);
  const generation = useRef(0);

  useEffect(
    () => () => {
      pending.current?.abort();
      generation.current++;
    },
    [],
  );

  function begin() {
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    const id = ++generation.current;
    return {
      signal: controller.signal,
      current: () => id === generation.current && !controller.signal.aborted,
    };
  }

  function clearEvidence() {
    setAnswer(null);
    setSource(null);
  }

  function disconnect(message = '') {
    begin();
    setSession(null);
    setWorkspaces([]);
    setWorkspaceId('');
    setQuestion('');
    setMode('keyword');
    clearEvidence();
    setBrowser(emptyBrowser());
    setView('ask');
    setRetry(null);
    setBusy(null);
    setError(message);
  }

  async function connect(token: string) {
    const operation = begin();
    setError('');
    setRetry(null);
    setBusy('connect');
    try {
      const user = await api.me(token, operation.signal);
      if (!operation.current()) return;
      const list = await api.workspaces(token, operation.signal);
      if (!operation.current()) return;
      setSession({ token, user });
      setWorkspaces(list.workspaces);
      setWorkspaceId(list.workspaces[0]?.id ?? '');
    } catch (failure) {
      if (operation.current()) {
        disconnect(
          failure instanceof ApiError && failure.status === 401
            ? 'Token not accepted. Check it or ask your operator for a new token.'
            : 'Could not connect. Check your connection and try again.',
        );
      }
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  function selectWorkspace(id: string) {
    begin();
    clearEvidence();
    setQuestion('');
    setWorkspaceId(id);
    setBusy(null);
    setError('');
    setRetry(null);
    setBrowser(emptyBrowser());
    if (view === 'browse' && id) void loadCatalogue('', 0, id);
  }

  function selectView(next: 'ask' | 'browse') {
    if (next === view) return;
    begin();
    setView(next);
    setSource(null);
    setBrowser(emptyBrowser());
    setBusy(null);
    setError('');
    setRetry(null);
    if (next === 'browse') void loadCatalogue('', 0);
  }

  async function handleFailure(
    failure: unknown,
    operation: ReturnType<typeof begin>,
    context: 'ask' | 'catalogue' | 'history' | 'source' = 'ask',
    scope = workspaceId,
  ): Promise<boolean> {
    if (!operation.current()) return false;
    const prefix =
      context === 'ask'
        ? ''
        : `Could not load ${
            {
              catalogue: 'the source catalogue',
              history: 'version history',
              source: 'source text',
            }[context]
          }. `;
    if (failure instanceof ApiError) {
      if (failure.status === 401) {
        disconnect('Your token may have expired or been revoked. Connect again.');
        return false;
      }
      if ((failure.status === 403 || failure.status === 404) && session) {
        clearEvidence();
        setBrowser(emptyBrowser());
        setRetry(null);
        setQuestion('');
        setError('Workspace or source is no longer accessible. Refreshing workspace access.');
        try {
          const list = await api.workspaces(session.token, operation.signal);
          if (!operation.current()) return false;
          setWorkspaces(list.workspaces);
          setWorkspaceId(
            list.workspaces.some((w) => w.id === scope) ? scope : (list.workspaces[0]?.id ?? ''),
          );
          setError(
            'Workspace or source is no longer accessible. Workspace access has been refreshed.',
          );
        } catch (refreshFailure) {
          if (!operation.current()) return false;
          if (refreshFailure instanceof ApiError && refreshFailure.status === 401) {
            disconnect('Your token may have expired or been revoked. Connect again.');
          } else {
            // Do not leave a previously authorised workspace available after a failed refresh.
            setWorkspaces([]);
            setWorkspaceId('');
            setError('Could not refresh workspace access. Disconnect and connect again to retry.');
          }
        }
        return false;
      }
      if (failure.status === 422) {
        setError(
          prefix +
            (context === 'ask'
              ? 'Check your question. Use 1–1,000 characters without NUL characters.'
              : context === 'catalogue'
                ? 'Check the title filter. Use at most 200 characters without NUL characters.'
                : 'The source request was invalid. Refresh the catalogue and try again.'),
        );
        return true;
      }
      if (failure.status === 503) {
        setError(
          prefix +
            (context !== 'ask' || mode === 'keyword'
              ? 'The service is unavailable. Try again shortly.'
              : 'This retrieval mode is unavailable. Choose keyword or try again later.'),
        );
        return true;
      }
    }
    setError(
      prefix +
        (failure instanceof SourceMismatch
          ? 'The source response did not match the requested document or version. Try again.'
          : 'The request could not complete. Check your connection and try again.'),
    );
    return true;
  }

  async function ask() {
    if (!session || !workspaceId || !question.trim()) return;
    const operation = begin();
    clearEvidence();
    setError('');
    setRetry(null);
    setBusy('ask');
    try {
      const result = await api.ask(
        session.token,
        workspaceId,
        question.trim(),
        mode,
        operation.signal,
      );
      if (operation.current()) setAnswer(result);
    } catch (failure) {
      if (await handleFailure(failure, operation)) setRetry(() => () => void ask());
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  async function openSource(citation: Citation) {
    if (!session || !workspaceId) return;
    const operation = begin();
    setSource(null);
    setError('');
    setRetry(null);
    setBusy('source');
    try {
      const version = await api.source(session.token, workspaceId, citation, operation.signal);
      if (!operation.current()) return;
      if (
        version.workspace_id !== workspaceId ||
        version.source_document_id !== citation.source_document_id ||
        version.document_version_id !== citation.document_version_id
      ) {
        setError('The source response did not match this citation. Try again.');
        return;
      }
      setSource({ version, citation });
    } catch (failure) {
      if (await handleFailure(failure, operation, 'source'))
        setRetry(() => () => void openSource(citation));
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  async function loadCatalogue(title = browser.title, offset = 0, scope = workspaceId) {
    if (!session || !scope) return;
    const operation = begin();
    const applied = title.trim();
    setSource(null);
    setBrowser({ ...emptyBrowser(), title: applied, filterDraft: applied, offset });
    setBusy('catalogue');
    setError('');
    setRetry(null);
    try {
      const result = await api.sources(session.token, scope, applied, offset, operation.signal);
      if (!operation.current()) return;
      if (result.sources.some((s) => s.workspace_id !== scope)) throw new SourceMismatch();
      setBrowser((b) => ({
        ...b,
        sources: result.sources,
        hasMore: result.has_more,
        loaded: true,
      }));
    } catch (failure) {
      if (await handleFailure(failure, operation, 'catalogue', scope))
        setRetry(() => () => void loadCatalogue(applied, offset, scope));
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  async function fetchVersion(ref: SourceRef, operation: ReturnType<typeof begin>) {
    if (!session) return;
    const version = await api.source(session.token, workspaceId, ref, operation.signal);
    if (!operation.current()) return;
    if (
      version.workspace_id !== workspaceId ||
      version.source_document_id !== ref.source_document_id ||
      version.document_version_id !== ref.document_version_id
    )
      throw new SourceMismatch();
    setSource({ version, citation: null });
  }

  async function loadHistory(selected: SourceSummary, offset = 0, openLatest = false) {
    if (!session || !workspaceId || selected.workspace_id !== workspaceId) return;
    const operation = begin();
    let context: 'history' | 'source' = 'history';
    if (openLatest) setSource(null);
    setBrowser((b) => ({
      ...b,
      selected,
      versions: [],
      versionsHasMore: false,
      versionsLoaded: false,
      versionOffset: offset,
    }));
    setBusy('history');
    setError('');
    setRetry(null);
    try {
      const result = await api.versions(
        session.token,
        workspaceId,
        selected.source_document_id,
        offset,
        operation.signal,
      );
      if (!operation.current()) return;
      if (
        result.versions.some(
          (v) =>
            v.workspace_id !== workspaceId || v.source_document_id !== selected.source_document_id,
        )
      )
        throw new SourceMismatch();
      setBrowser((b) => ({
        ...b,
        versions: result.versions,
        versionsHasMore: result.has_more,
        versionsLoaded: true,
      }));
      if (openLatest && result.versions[0]) {
        context = 'source';
        await fetchVersion(result.versions[0], operation);
      }
    } catch (failure) {
      if (await handleFailure(failure, operation, context))
        setRetry(() => () => void loadHistory(selected, offset, openLatest));
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  async function openVersion(ref: SourceRef) {
    if (!session || !workspaceId) return;
    const operation = begin();
    setSource(null);
    setBusy('source');
    setError('');
    setRetry(null);
    try {
      await fetchVersion(ref, operation);
    } catch (failure) {
      if (await handleFailure(failure, operation, 'source'))
        setRetry(() => () => void openVersion(ref));
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  return {
    user: session?.user,
    workspaces,
    workspaceId,
    question,
    setQuestion,
    mode,
    setMode,
    answer,
    source,
    busy,
    error,
    connect,
    disconnect,
    selectWorkspace,
    ask,
    openSource,
    view,
    selectView,
    browser,
    setTitleFilter: (filterDraft: string) => setBrowser((b) => ({ ...b, filterDraft })),
    loadCatalogue,
    loadHistory,
    openVersion,
    retry,
  };
}
