// Habeas Protocol — TypeScript client.
//
// Browser- and Node-compatible (uses `fetch`). No runtime dependencies.
// Mirrors the Python client one-to-one; same method names, same shapes.
//
// Usage in a browser:
//   import { HabeasClient } from './habeas';
//   const c = new HabeasClient();
//   const h = await c.health();
//
// Usage in Node ≥18 (which has global fetch):
//   import { HabeasClient } from './habeas.js';
//   const c = new HabeasClient();
//
// The full endpoint list is documented at api/openapi.yaml.

export type Tribunal = 'DIFC' | 'ADGM' | 'SICC';
export type ForumCode = Tribunal | 'FOREIGN_ARBITRAL_TRIBUNAL' | 'HONG_KONG_HIGH_COURT' | 'ANY';
export type Role = 'gate' | 'arithmetic' | 'disposition' | 'interpretation';
export type CertificationState = 'draft' | 'submitted' | 'reviewed' | 'certified' | 'deprecated';

export interface Health {
  status: { ok: boolean; judgments: number };
}

export interface Judgment {
  case_no: string;
  url?: string | null;
  tribunal: 'DIFC Courts' | 'ADGM Courts' | 'Singapore International Commercial Court';
  division?: string | null;
  date_issued?: string | null;
  parties: { claimant: string; defendant: string };
  judge?: string | null;
  claim_type?: string | null;
  outcome?: string | null;
  operative_amount_aed?: number | null;
  rules_cited?: string[];
  primitive_scores_v02?: Record<string, number>;
  coding?: { coder: string; coded_on: string; gold_set: boolean; notes?: string };
  // additional fields per the registry shape
  [k: string]: unknown;
}

export interface RuleModule {
  module: string;
  scope: string;
  file: string;
  schema: string;
}

export interface RuleRunOptions {
  source_label?: string;
}

export interface ValidateResult {
  ok: boolean;
  stage?: 'typecheck' | 'interpret';
  errors?: string;
  interpret_output?: string;
}

export interface ConflictRouteRequest {
  forum: ForumCode;
  claim_type?: string;
  originating_forum?: ForumCode | null;
  governing_law?: string | null;
}

export interface RuleRef {
  module: string;
  scope: string;
  role?: Role;
  role_class?: Role | null;
  tribunal?: string;
  primary_jurisdiction?: string;
  applies_in?: string[];
  public_policy_gate?: boolean;
  is_recognition_gate?: boolean;
  applied_via?: string;
  when?: string;
  reason?: string;
}

export interface ConflictRouteResponse {
  forum: ForumCode;
  originating_forum?: ForumCode | null;
  claim_type?: string;
  governing_law?: string | null;
  forum_posture?: Record<string, unknown>;
  cross_border_path?: Record<string, unknown> | null;
  recognition_chain: RuleRef[];
  applicable_rules: RuleRef[];
  public_policy_overrides: RuleRef[];
  narrative: string[];
}

// ---- errors ----

export class HabeasError extends Error {
  status?: number;
  payload?: unknown;
  constructor(message: string, opts: { status?: number; payload?: unknown } = {}) {
    super(message);
    this.name = 'HabeasError';
    this.status = opts.status;
    this.payload = opts.payload;
  }
}

export class ValidationError extends HabeasError {
  constructor(message: string, payload: unknown) {
    super(message, { payload });
    this.name = 'ValidationError';
  }
}

export class AdminModeRequired extends HabeasError {
  constructor(message: string) {
    super(message);
    this.name = 'AdminModeRequired';
  }
}

// ---- client ----

export interface HabeasClientOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  userAgent?: string;
}

export class HabeasClient {
  readonly baseUrl: string;
  private fetchImpl: typeof fetch;
  private userAgent: string;

  constructor(opts: HabeasClientOptions = {}) {
    this.baseUrl = (opts.baseUrl ?? 'http://127.0.0.1:5544').replace(/\/$/, '');
    this.fetchImpl = opts.fetchImpl ?? globalThis.fetch.bind(globalThis);
    this.userAgent = opts.userAgent ?? 'habeas-typescript/0.1.0';
  }

  // --- internal HTTP helpers ---

  private async request<T = unknown>(
    method: 'GET' | 'POST',
    path: string,
    opts: { params?: Record<string, unknown>; body?: unknown } = {},
  ): Promise<T> {
    let url = this.baseUrl + path;
    if (opts.params) {
      const qs = new URLSearchParams();
      for (const [k, v] of Object.entries(opts.params)) {
        if (v == null) continue;
        qs.set(k, String(v));
      }
      const s = qs.toString();
      if (s) url += url.includes('?') ? '&' + s : '?' + s;
    }
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (typeof process !== 'undefined' && process.versions?.node) {
      // The User-Agent header is reserved in browsers; only set in Node.
      headers['User-Agent'] = this.userAgent;
    }
    const body = opts.body !== undefined ? JSON.stringify(opts.body) : undefined;
    if (body !== undefined) headers['Content-Type'] = 'application/json';

    let res: Response;
    try {
      res = await this.fetchImpl(url, { method, headers, body });
    } catch (e) {
      throw new HabeasError(`could not reach ${url}: ${(e as Error).message}`);
    }
    let payload: unknown = null;
    const text = await res.text();
    if (text) {
      try { payload = JSON.parse(text); } catch { payload = { error: text }; }
    }
    if (!res.ok) {
      const errMsg = (payload && typeof payload === 'object' && 'error' in payload)
        ? String((payload as { error: unknown }).error)
        : `HTTP ${res.status}`;
      if (res.status === 500 && errMsg.includes('save-back is disabled')) {
        throw new AdminModeRequired(errMsg);
      }
      throw new HabeasError(`HTTP ${res.status}: ${errMsg}`, { status: res.status, payload });
    }
    return payload as T;
  }

  private get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    return this.request<T>('GET', path, { params });
  }
  private post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>('POST', path, { body });
  }

  // --- corpus ---

  health(): Promise<Health> {
    return this.get<Health>('/api/health');
  }

  judgments(opts: { tribunal?: Tribunal; limit?: number } = {}): Promise<Judgment[]> {
    return this.get<Judgment[]>('/api/judgments', { tribunal: opts.tribunal, limit: opts.limit ?? 500 });
  }

  rules(opts: { limit?: number } = {}): Promise<unknown[]> {
    return this.get<unknown[]>('/api/rules', { limit: opts.limit ?? 20 });
  }

  tribunalMeans(): Promise<unknown[]> {
    return this.get<unknown[]>('/api/tribunal_means');
  }

  search(q: string, opts: { limit?: number } = {}): Promise<unknown[]> {
    return this.get<unknown[]>('/api/search', { q, limit: opts.limit ?? 10 });
  }

  // --- rule library + routing ---

  ruleModules(): Promise<RuleModule[]> {
    return this.get<RuleModule[]>('/api/rule_modules');
  }

  claims(): Promise<unknown> {
    return this.get<unknown>('/api/claims');
  }

  jurisdictions(): Promise<unknown> {
    return this.get<unknown>('/api/jurisdictions');
  }

  certificationStates(): Promise<Record<string, { module_name: string; certification: { state: CertificationState }; [k: string]: unknown }>> {
    return this.get('/api/certification_states');
  }

  certificationSpec(): Promise<{ yaml: string }> {
    return this.get<{ yaml: string }>('/api/certification_spec');
  }

  // --- audit ---

  runsRecent(opts: { limit?: number } = {}): Promise<unknown[]> {
    return this.get<unknown[]>('/api/runs/recent', { limit: opts.limit ?? 50 });
  }

  runsStats(): Promise<unknown[]> {
    return this.get<unknown[]>('/api/runs/stats');
  }

  // --- rule execution ---

  ruleRun<T = unknown>(
    module: string,
    scope: string,
    inputs: Record<string, unknown>,
    opts: RuleRunOptions = {},
  ): Promise<T> {
    const body: Record<string, unknown> = { module, scope, inputs };
    if (opts.source_label !== undefined) body.source_label = opts.source_label;
    return this.post<T>('/api/rule_run', body);
  }

  /** Throws ValidationError on ok=false; use ruleValidateRaw for raw access. */
  async ruleValidate(source: string): Promise<ValidateResult> {
    const res = await this.ruleValidateRaw(source);
    if (!res.ok) {
      throw new ValidationError(
        `validation failed (stage=${res.stage ?? 'unknown'}): ${res.errors ?? ''}`,
        res,
      );
    }
    return res;
  }

  ruleValidateRaw(source: string): Promise<ValidateResult> {
    return this.post<ValidateResult>('/api/rule_validate', { source });
  }

  /** Admin-mode-only. Throws AdminModeRequired if HABEAS_ADMIN_MODE is unset. */
  ruleSave(filename: string, source: string): Promise<{ saved: boolean; path?: string; overwrote_existing?: boolean }> {
    return this.post('/api/rule_save', { filename, source });
  }

  // --- ingestion + conflict-of-laws ---

  ingest(text: string): Promise<unknown> {
    return this.post('/api/ingest', { text });
  }

  conflictRoute(req: ConflictRouteRequest): Promise<ConflictRouteResponse> {
    const body: Record<string, unknown> = { forum: req.forum };
    if (req.claim_type !== undefined) body.claim_type = req.claim_type;
    if (req.originating_forum !== undefined) body.originating_forum = req.originating_forum;
    if (req.governing_law !== undefined) body.governing_law = req.governing_law;
    return this.post<ConflictRouteResponse>('/api/conflict_route', body);
  }
}
