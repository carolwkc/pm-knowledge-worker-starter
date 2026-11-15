import { useEffect, useRef, useState } from 'react';
import {
  api,
  ApiError,
  type Answer,
  type FeedbackCreate,
  type FeedbackFilter,
  type Citation,
  type Evidence,
  type IngestReceipt,
  type UploadSourceInput,
  type ProposalFilter,
  type ReviewAction,
  type RetrievalMode,
  type SourceVersion,
  type SourceRef,
  type SourceSummary,
  type SourceVersionSummary,
  type User,
  type Workspace,
} from './api';
import {
  emptyDecisions,
  validComment,
  verifiedRecord,
  type KnowledgeRecord,
  type WorkspaceView,
} from './decisionState';
import { emptyFeedback, validReceipt, type FeedbackSubmission } from './feedbackState';
import type { FeedbackDraft } from './FeedbackForm';

interface Session {
  token: string;
  user: User;
}
export interface OpenSource {
  version: SourceVersion;
  citation: Evidence | null;
  context?: 'answer' | 'proposal' | 'decision' | 'feedback';
}

export interface BrowserState {
  sources: SourceSummary[];
  hasMore: boolean;
  title: string;
  filterDraft: string;
  offset: number;
  loaded: boolean;
  selected: SourceSelection | null;
  versions: SourceVersionSummary[];
  versionsHasMore: boolean;
  versionsLoaded: boolean;
  versionOffset: number;
}

export type SourceSelection = Pick<SourceSummary, 'workspace_id' | 'source_document_id' | 'title'>;

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
  const [answerContext, setAnswerContext] = useState<{
    question: string;
    mode: RetrievalMode;
    submission_id: string;
  } | null>(null);
  const [feedbackSubmission, setFeedbackSubmission] = useState<FeedbackSubmission | null>(null);
  const [feedback, setFeedback] = useState(emptyFeedback);
  const [source, setSource] = useState<OpenSource | null>(null);
  const [view, setView] = useState<WorkspaceView>('ask');
  const [decisions, setDecisions] = useState(emptyDecisions);
  const [generated, setGenerated] = useState('');
  const [browser, setBrowser] = useState<BrowserState>(emptyBrowser);
  const [uploadTarget, setUploadTarget] = useState<{ source: SourceSelection | null } | null>(null);
  const [uploadReceipt, setUploadReceipt] = useState<IngestReceipt | null>(null);
  const [uploadUncertain, setUploadUncertain] = useState(false);
  const [busy, setBusy] = useState<
    | 'connect'
    | 'ask'
    | 'source'
    | 'catalogue'
    | 'history'
    | 'records'
    | 'detail'
    | 'generate'
    | 'review'
    | 'upload'
    | 'feedback'
    | null
  >(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState<(() => void) | null>(null);
  const pending = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const writing = useRef(false);
  const role = workspaces.find((w) => w.id === workspaceId)?.role;

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
    clearUpload();
    setAnswer(null);
    setAnswerContext(null);
    setFeedbackSubmission(null);
    setFeedback(emptyFeedback());
    setSource(null);
    setDecisions(emptyDecisions());
    setGenerated('');
  }

  function clearUpload() {
    setUploadTarget(null);
    setUploadReceipt(null);
    setUploadUncertain(false);
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
    const next =
      view === 'feedback' && workspaces.find((w) => w.id === id)?.role !== 'owner'
        ? 'ask'
        : view === 'proposals' && workspaces.find((w) => w.id === id)?.role === 'reader'
          ? 'decisions'
          : view;
    setView(next);
    if ((next === 'decisions' || next === 'proposals') && id)
      void loadRecords('pending', 0, false, next, id);
    if (next === 'feedback' && id) void loadFeedback('all', 0, id);
  }

  function selectView(next: WorkspaceView) {
    if (next === 'feedback' && role !== 'owner') return;
    if (next === 'proposals' && role !== 'editor' && role !== 'owner') return;
    if (next === view) return;
    begin();
    clearUpload();
    setView(next);
    setSource(null);
    setBrowser(emptyBrowser());
    setDecisions(emptyDecisions());
    setFeedback(emptyFeedback());
    // A request can commit after navigation. Its frozen submission remains retryable.
    setFeedbackSubmission((s) => (s?.status === 'pending' ? { ...s, status: 'uncertain' } : s));
    setGenerated('');
    setBusy(null);
    setError('');
    setRetry(null);
    if (next === 'browse') void loadCatalogue('', 0);
    if (next === 'feedback') void loadFeedback('all', 0);
    if (next === 'decisions' || next === 'proposals') void loadRecords('pending', 0, false, next);
  }

  async function handleFailure(
    failure: unknown,
    operation: ReturnType<typeof begin>,
    context:
      | 'ask'
      | 'catalogue'
      | 'history'
      | 'source'
      | 'records'
      | 'detail'
      | 'generate'
      | 'review' = 'ask',
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
              records: 'the knowledge catalogue',
              detail: 'the selected record and evidence',
              generate: 'proposal generation results',
              review: 'the review result',
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
          const selected = list.workspaces.find((w) => w.id === scope) ?? list.workspaces[0];
          // Initial navigation starts its read from the previous render's view.
          // Route the active view, rather than that stale closure, after access refresh.
          setView((current) => {
            if (current === 'feedback' && selected?.role !== 'owner') return 'ask';
            if (
              current === 'proposals' &&
              selected?.role !== 'editor' &&
              selected?.role !== 'owner'
            )
              return 'decisions';
            return current;
          });
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
                : context === 'review'
                  ? 'Check the review comment. Use at most 1,000 characters without NUL characters.'
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
      if (operation.current()) {
        setAnswer(result);
        setAnswerContext({ question: question.trim(), mode, submission_id: crypto.randomUUID() });
      }
    } catch (failure) {
      if (await handleFailure(failure, operation)) setRetry(() => () => void ask());
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  async function openSource(citation: Citation, context: 'answer' | 'feedback' = 'answer') {
    if (!session || !workspaceId) return;
    if (writing.current) return;
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
      setSource({ version, citation, context });
    } catch (failure) {
      if (await handleFailure(failure, operation, 'source'))
        setRetry(() => () => void openSource(citation, context));
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  async function loadCatalogue(title = browser.title, offset = 0, scope = workspaceId) {
    if (!session || !scope) return;
    const operation = begin();
    clearUpload();
    const applied = title.trim();
    setSource(null);
    setGenerated('');
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

  async function loadHistory(selected: SourceSelection, offset = 0, openLatest = false) {
    if (!session || !workspaceId || selected.workspace_id !== workspaceId) return;
    const operation = begin();
    clearUpload();
    setGenerated('');
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
    clearUpload();
    setGenerated('');
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

  async function fetchRecords(
    next: 'decisions' | 'proposals',
    status: ProposalFilter,
    offset: number,
    operation: ReturnType<typeof begin>,
    scope: string,
    backtrack = false,
  ) {
    if (!session) return;
    let page = offset;
    let records: KnowledgeRecord[];
    do {
      const result =
        next === 'decisions'
          ? (await api.decisions(session.token, scope, page, operation.signal)).decisions
          : (await api.proposals(session.token, scope, status, page, operation.signal)).proposals;
      if (!operation.current()) return;
      if (result.some((r) => r.workspace_id !== scope)) throw new SourceMismatch();
      records = result;
      if (!backtrack || records.length || page === 0) break;
      page = Math.max(0, page - 20);
    } while (operation.current());
    if (operation.current())
      setDecisions((d) => ({
        ...d,
        records: records.slice(0, 20),
        offset: page,
        hasMore: records.length > 20,
        loaded: true,
      }));
  }

  async function loadRecords(
    status: ProposalFilter = decisions.status,
    offset = 0,
    preserve = false,
    next: 'decisions' | 'proposals' = view === 'proposals' ? 'proposals' : 'decisions',
    scope = workspaceId,
  ) {
    if (!session || !scope) return;
    const operation = begin();
    if (!preserve) {
      setSource(null);
      setDecisions({ ...emptyDecisions(), status, offset });
    } else setDecisions((d) => ({ ...d, records: [], loaded: false }));
    setBusy('records');
    setError('');
    setRetry(null);
    try {
      await fetchRecords(next, status, offset, operation, scope, preserve);
    } catch (failure) {
      if (await handleFailure(failure, operation, 'records', scope))
        setRetry(() => () => void loadRecords(status, offset, preserve, next, scope));
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  async function fetchRecord(
    id: string,
    next: 'decisions' | 'proposals',
    operation: ReturnType<typeof begin>,
  ) {
    if (!session) return;
    const record =
      next === 'decisions'
        ? await api.decision(session.token, workspaceId, id, operation.signal)
        : await api.proposal(session.token, workspaceId, id, operation.signal);
    if (!operation.current()) return;
    if (record.workspace_id !== workspaceId || record.id !== id) throw new SourceMismatch();
    setDecisions((d) => ({ ...d, selected: record }));
    const version = await api.source(session.token, workspaceId, record.evidence, operation.signal);
    if (!operation.current()) return;
    if (
      version.workspace_id !== workspaceId ||
      version.source_document_id !== record.evidence.source_document_id ||
      version.document_version_id !== record.evidence.document_version_id
    )
      throw new SourceMismatch();
    setSource({
      version,
      citation: record.evidence,
      context: next === 'decisions' ? 'decision' : 'proposal',
    });
    setDecisions((d) => ({ ...d, unresolved: false }));
  }

  async function openRecord(
    id: string,
    next: 'decisions' | 'proposals' = view === 'proposals' ? 'proposals' : 'decisions',
    refill = false,
  ) {
    if (!session || !workspaceId) return;
    const operation = begin();
    setView(next);
    setSource(null);
    setBusy('detail');
    setError('');
    setRetry(null);
    setDecisions((d) => ({
      ...(next === view ? d : emptyDecisions()),
      selected: null,
      comment: '',
      confirmation: null,
      notice: '',
      unresolved: true,
    }));
    try {
      if (next !== view) await fetchRecords(next, 'pending', 0, operation, workspaceId);
      if (operation.current()) await fetchRecord(id, next, operation);
      if (refill && operation.current()) await refillReviewQueue(operation);
    } catch (failure) {
      if (await handleFailure(failure, operation, 'detail'))
        setRetry(() => () => void openRecord(id, next, refill));
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  const selectedProposal =
    decisions.selected && 'status' in decisions.selected ? decisions.selected : null;
  const canReview =
    role === 'owner' && selectedProposal?.status === 'pending' && !decisions.unresolved;
  const canApprove =
    !!canReview &&
    !!selectedProposal &&
    verifiedRecord(selectedProposal, source?.version) &&
    source?.version.source_is_latest === true;

  function prepareReview(action: ReviewAction) {
    if (
      !canReview ||
      (action === 'approve' && !canApprove) ||
      busy ||
      !validComment(decisions.comment)
    )
      return;
    setDecisions((d) => ({ ...d, confirmation: action }));
  }

  async function refillReviewQueue(operation: ReturnType<typeof begin>) {
    try {
      await fetchRecords(
        'proposals',
        decisions.status,
        decisions.offset,
        operation,
        workspaceId,
        true,
      );
    } catch (failure) {
      if (await handleFailure(failure, operation, 'records'))
        setRetry(
          () => () => void loadRecords(decisions.status, decisions.offset, true, 'proposals'),
        );
    }
  }

  async function submitReview() {
    const action = decisions.confirmation;
    if (
      !session ||
      !selectedProposal ||
      !action ||
      !canReview ||
      writing.current ||
      busy ||
      (action === 'approve' && !canApprove) ||
      !validComment(decisions.comment)
    )
      return;
    const operation = begin();
    writing.current = true;
    setBusy('review');
    setError('');
    setRetry(null);
    setDecisions((d) => ({ ...d, confirmation: null, notice: '' }));
    try {
      const comment = decisions.comment.trim();
      const result = await api.review(
        session.token,
        workspaceId,
        selectedProposal.id,
        { action, ...(comment ? { comment } : {}) },
        operation.signal,
      );
      if (!operation.current()) return;
      if (result.workspace_id !== workspaceId || result.id !== selectedProposal.id)
        throw new SourceMismatch();
      setDecisions((d) => ({
        ...d,
        selected: result,
        comment: '',
        notice: `Review recorded: ${result.status}.`,
      }));
      await refillReviewQueue(operation);
    } catch (failure) {
      if (!operation.current()) return;
      if (failure instanceof ApiError && [401, 403, 404, 422].includes(failure.status)) {
        await handleFailure(failure, operation, 'review');
      } else {
        const conflict = failure instanceof ApiError && failure.status === 409;
        setSource(null);
        setDecisions((d) => ({
          ...d,
          unresolved: true,
          comment: '',
          confirmation: null,
          notice: conflict
            ? 'Review conflict. Reloading the proposal and its evidence.'
            : 'Review outcome uncertain. Reloading the recorded proposal before any further review.',
        }));
        try {
          await fetchRecord(selectedProposal.id, 'proposals', operation);
          if (operation.current()) await refillReviewQueue(operation);
        } catch (readFailure) {
          if (await handleFailure(readFailure, operation, 'detail'))
            setRetry(() => () => void openRecord(selectedProposal.id, 'proposals', true));
        }
      }
    } finally {
      writing.current = false;
      if (operation.current()) setBusy(null);
    }
  }

  async function generate() {
    if (
      !session ||
      !source ||
      view !== 'browse' ||
      role === 'reader' ||
      !role ||
      !source.version.source_is_latest ||
      busy ||
      writing.current
    )
      return;
    const operation = begin();
    writing.current = true;
    const ref = source.version;
    setBusy('generate');
    setError('');
    setRetry(null);
    setGenerated('');
    try {
      const result = await api.generate(session.token, workspaceId, ref, operation.signal);
      if (!operation.current()) return;
      if (
        result.proposals.some(
          (p) =>
            p.workspace_id !== workspaceId ||
            p.evidence.source_document_id !== ref.source_document_id ||
            p.evidence.document_version_id !== ref.document_version_id,
        )
      )
        throw new SourceMismatch();
      const count = result.proposals.length;
      setGenerated(
        !count
          ? 'No decision proposals matched this source.'
          : `Created ${result.created_count} new ${result.created_count === 1 ? 'proposal' : 'proposals'}; ${count} ${count === 1 ? 'proposal' : 'proposals'} returned.${result.created_count === 0 ? ' Existing proposals and review history were preserved.' : ''}`,
      );
    } catch (failure) {
      if (!operation.current()) return;
      if (failure instanceof ApiError && failure.status === 409) {
        setSource({ ...source, version: { ...source.version, source_is_latest: false } });
        setError(
          'This source has a newer version. Refresh the catalogue and open its latest version to generate proposals.',
        );
        setRetry(() => () => void loadCatalogue(browser.title, 0));
      } else if (await handleFailure(failure, operation, 'generate'))
        setRetry(() => () => void generate());
    } finally {
      writing.current = false;
      if (operation.current()) setBusy(null);
    }
  }

  const canUpload = view === 'browse' && (role === 'editor' || role === 'owner');

  function openUpload(target: SourceSelection | null) {
    if (!canUpload || busy || writing.current || (target && target.workspace_id !== workspaceId))
      return;
    clearUpload();
    setError('');
    setRetry(null);
    setUploadTarget({ source: target });
  }

  // A receipt is a committed write. Failures below can only retry reads.
  async function readUploaded(
    receipt: IngestReceipt,
    selected: SourceSelection,
    operation: ReturnType<typeof begin>,
  ) {
    if (!session) return;
    let context: 'source' | 'catalogue' | 'history' = 'source';
    try {
      const version = await api.source(session.token, workspaceId, receipt, operation.signal);
      if (!operation.current()) return;
      if (
        version.workspace_id !== workspaceId ||
        version.source_document_id !== receipt.source_document_id ||
        version.document_version_id !== receipt.document_version_id ||
        version.sha256 !== receipt.sha256 ||
        version.version_number !== receipt.version_number
      )
        throw new SourceMismatch();
      setSource({ version, citation: null });
      setBrowser((b) => ({ ...b, selected: { ...selected, title: version.title } }));
      context = 'catalogue';
      const catalogue = await api.sources(session.token, workspaceId, '', 0, operation.signal);
      if (!operation.current()) return;
      if (catalogue.sources.some((s) => s.workspace_id !== workspaceId)) throw new SourceMismatch();
      setBrowser((b) => ({
        ...b,
        sources: catalogue.sources,
        hasMore: catalogue.has_more,
        loaded: true,
      }));
      context = 'history';
      const history = await api.versions(
        session.token,
        workspaceId,
        receipt.source_document_id,
        0,
        operation.signal,
      );
      if (!operation.current()) return;
      if (
        history.versions.some(
          (v) =>
            v.workspace_id !== workspaceId || v.source_document_id !== receipt.source_document_id,
        )
      )
        throw new SourceMismatch();
      setBrowser((b) => ({
        ...b,
        versions: history.versions,
        versionsHasMore: history.has_more,
        versionsLoaded: true,
      }));
    } catch (failure) {
      if (await handleFailure(failure, operation, context))
        setRetry(() => () => void refreshUploaded(receipt, selected));
    }
  }

  async function refreshUploaded(receipt: IngestReceipt, selected: SourceSelection) {
    if (!session || receipt.workspace_id !== workspaceId || view !== 'browse') return;
    const operation = begin();
    setBusy('upload');
    setError('');
    setRetry(null);
    try {
      await readUploaded(receipt, selected, operation);
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  async function submitUpload(input: UploadSourceInput) {
    if (!session || !workspaceId || !canUpload || !uploadTarget || busy || writing.current) return;
    const target = uploadTarget.source;
    if (target && target.workspace_id !== workspaceId) return;
    const operation = begin();
    writing.current = true;
    setBusy('upload');
    setError('');
    setRetry(null);
    setUploadUncertain(false);
    try {
      const receipt = target
        ? await api.uploadVersion(
            session.token,
            workspaceId,
            target.source_document_id,
            input.file,
            operation.signal,
          )
        : await api.uploadSource(session.token, workspaceId, input, operation.signal);
      if (!operation.current()) return;
      if (
        !receipt ||
        receipt.workspace_id !== workspaceId ||
        !receipt.source_document_id ||
        typeof receipt.source_document_id !== 'string' ||
        !receipt.document_version_id ||
        typeof receipt.document_version_id !== 'string' ||
        (target && receipt.source_document_id !== target.source_document_id) ||
        !Number.isInteger(receipt.version_number) ||
        receipt.version_number < 1 ||
        typeof receipt.sha256 !== 'string' ||
        !/^[a-f0-9]{64}$/.test(receipt.sha256) ||
        !Number.isInteger(receipt.chunk_count) ||
        receipt.chunk_count < 1 ||
        typeof receipt.duplicate !== 'boolean'
      )
        throw new SourceMismatch();
      setUploadReceipt(receipt);
      setUploadTarget(null);
      setSource(null);
      setGenerated('');
      const selected = {
        workspace_id: workspaceId,
        source_document_id: receipt.source_document_id,
        title: target?.title ?? input.title,
      };
      setBrowser({ ...emptyBrowser(), selected });
      await readUploaded(receipt, selected, operation);
    } catch (failure) {
      if (!operation.current()) return;
      if (failure instanceof ApiError && [401, 403, 404].includes(failure.status))
        await handleFailure(failure, operation, 'source');
      else if (failure instanceof ApiError && [413, 415, 422].includes(failure.status)) {
        setError(
          failure.status === 413
            ? 'The file must be at most 1 MiB (1,048,576 bytes).'
            : failure.status === 415
              ? 'Choose a Markdown (.md/.markdown) or plain-text (.txt) file.'
              : 'Check the title and source URI limits. The file must contain nonblank UTF-8 text without NUL characters.',
        );
      } else {
        setUploadUncertain(true);
        setError(
          'Upload outcome uncertain. The server may have saved the file. Inspect the source catalogue before manually submitting again. Another new-source submission can create a separate document; versions deduplicate content within their source.',
        );
      }
    } finally {
      writing.current = false;
      if (operation.current()) setBusy(null);
    }
  }

  async function submitFeedback(draft?: FeedbackDraft) {
    if (!session || !workspaceId || !answer || !answerContext || writing.current || busy) return;
    const body: FeedbackCreate | undefined = draft
      ? { ...answerContext, answer, ...draft }
      : feedbackSubmission?.status === 'uncertain'
        ? feedbackSubmission.body
        : undefined;
    if (
      !body ||
      feedbackSubmission?.status === 'saved' ||
      feedbackSubmission?.status === 'conflict'
    )
      return;
    const operation = begin();
    writing.current = true;
    setBusy('feedback');
    setError('');
    setRetry(null);
    setFeedbackSubmission({ body, status: 'pending' });
    try {
      const receipt = await api.submitFeedback(session.token, workspaceId, body, operation.signal);
      if (!operation.current()) return;
      if (!validReceipt(receipt, workspaceId, body.submission_id)) throw new SourceMismatch();
      setFeedbackSubmission({ body, status: 'saved', receipt });
    } catch (failure) {
      if (!operation.current()) return;
      if (failure instanceof ApiError && [401, 403, 404].includes(failure.status)) {
        await handleFailure(failure, operation);
      } else if (failure instanceof ApiError && failure.status === 422) {
        setFeedbackSubmission(null);
        setError('Feedback was not saved. Check the comment and reported answer context.');
      } else {
        const conflict = failure instanceof ApiError && failure.status === 409;
        setFeedbackSubmission({ body, status: conflict ? 'conflict' : 'uncertain' });
        setError(
          conflict
            ? 'Feedback submission conflicts with an existing record.'
            : 'Feedback outcome uncertain. Retry only the preserved submission.',
        );
      }
    } finally {
      writing.current = false;
      if (operation.current()) setBusy(null);
    }
  }

  async function loadFeedback(
    rating: FeedbackFilter = feedback.rating,
    offset = 0,
    scope = workspaceId,
  ) {
    if (!session || !scope || workspaces.find((w) => w.id === scope)?.role !== 'owner') return;
    const operation = begin();
    setBusy('records');
    setError('');
    setRetry(null);
    setSource(null);
    setFeedback({ ...emptyFeedback(), rating, offset });
    try {
      const result = await api.feedback(session.token, scope, rating, offset, operation.signal);
      if (!operation.current()) return;
      if (
        !Array.isArray(result.feedback) ||
        result.feedback.length > 20 ||
        typeof result.has_more !== 'boolean' ||
        result.feedback.some((r) => r.workspace_id !== scope)
      )
        throw new SourceMismatch();
      setFeedback({
        records: result.feedback,
        selected: null,
        rating,
        offset,
        hasMore: result.has_more,
        loaded: true,
      });
    } catch (failure) {
      if (await handleFailure(failure, operation, 'records', scope))
        setRetry(() => () => void loadFeedback(rating, offset, scope));
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  async function openFeedback(id: string) {
    if (!session || !workspaceId || role !== 'owner') return;
    const operation = begin();
    setBusy('detail');
    setError('');
    setRetry(null);
    setSource(null);
    setFeedback((f) => ({ ...f, selected: null }));
    try {
      const record = await api.feedbackDetail(session.token, workspaceId, id, operation.signal);
      if (!operation.current()) return;
      if (
        record.workspace_id !== workspaceId ||
        record.id !== id ||
        !record.answer ||
        !Array.isArray(record.answer.sources)
      )
        throw new SourceMismatch();
      setFeedback((f) => ({ ...f, selected: record }));
    } catch (failure) {
      if (await handleFailure(failure, operation, 'detail'))
        setRetry(() => () => void openFeedback(id));
    } finally {
      if (operation.current()) setBusy(null);
    }
  }

  return {
    answerContext,
    feedbackSubmission,
    submitFeedback,
    feedback,
    loadFeedback,
    openFeedback,
    openFeedbackSource: (citation: Citation) => openSource(citation, 'feedback'),
    canUpload,
    uploadTarget,
    uploadReceipt,
    uploadUncertain,
    openUpload,
    cancelUpload: () => {
      if (!busy) {
        clearUpload();
        setError('');
        setRetry(null);
      }
    },
    submitUpload,
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
    decisions,
    generated,
    loadRecords,
    openRecord,
    generate,
    canReview,
    canApprove,
    prepareReview,
    submitReview,
    setReviewComment: (comment: string) =>
      setDecisions((d) => ({ ...d, comment, confirmation: null })),
    cancelReview: () => setDecisions((d) => ({ ...d, confirmation: null })),
  };
}
