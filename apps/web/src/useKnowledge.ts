import { useEffect, useRef, useState } from 'react';
import {
  api,
  ApiError,
  type Answer,
  type Citation,
  type RetrievalMode,
  type SourceVersion,
  type User,
  type Workspace,
} from './api';

interface Session {
  token: string;
  user: User;
}
export interface OpenSource {
  version: SourceVersion;
  citation: Citation;
}

export function useKnowledge() {
  const [session, setSession] = useState<Session | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState('');
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState<RetrievalMode>('keyword');
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [source, setSource] = useState<OpenSource | null>(null);
  const [busy, setBusy] = useState<'connect' | 'ask' | 'source' | null>(null);
  const [error, setError] = useState('');
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
    setBusy(null);
    setError(message);
  }

  async function connect(token: string) {
    const operation = begin();
    setError('');
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
  }

  async function handleFailure(failure: unknown, operation: ReturnType<typeof begin>) {
    if (!operation.current()) return;
    if (failure instanceof ApiError) {
      if (failure.status === 401) {
        disconnect('Your token may have expired or been revoked. Connect again.');
        return;
      }
      if ((failure.status === 403 || failure.status === 404) && session) {
        clearEvidence();
        setQuestion('');
        setError('Workspace or source is no longer accessible. Refreshing workspace access.');
        try {
          const list = await api.workspaces(session.token, operation.signal);
          if (!operation.current()) return;
          setWorkspaces(list.workspaces);
          setWorkspaceId(
            list.workspaces.some((w) => w.id === workspaceId)
              ? workspaceId
              : (list.workspaces[0]?.id ?? ''),
          );
          setError(
            'Workspace or source is no longer accessible. Workspace access has been refreshed.',
          );
        } catch (refreshFailure) {
          if (!operation.current()) return;
          if (refreshFailure instanceof ApiError && refreshFailure.status === 401) {
            disconnect('Your token may have expired or been revoked. Connect again.');
          } else {
            // Do not leave a previously authorised workspace available after a failed refresh.
            setWorkspaces([]);
            setWorkspaceId('');
            setError('Could not refresh workspace access. Disconnect and connect again to retry.');
          }
        }
        return;
      }
      if (failure.status === 422) {
        setError('Check your question. Use 1–1,000 characters without NUL characters.');
        return;
      }
      if (failure.status === 503) {
        setError(
          mode === 'keyword'
            ? 'The service is unavailable. Try again shortly.'
            : 'This retrieval mode is unavailable. Choose keyword or try again later.',
        );
        return;
      }
    }
    setError('The request could not complete. Check your connection and try again.');
  }

  async function ask() {
    if (!session || !workspaceId || !question.trim()) return;
    const operation = begin();
    clearEvidence();
    setError('');
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
      await handleFailure(failure, operation);
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  async function openSource(citation: Citation) {
    if (!session || !workspaceId) return;
    const operation = begin();
    setSource(null);
    setError('');
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
      await handleFailure(failure, operation);
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
  };
}
