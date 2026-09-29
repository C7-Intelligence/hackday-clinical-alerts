import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

// Host-provided string DI tokens. REMOTE_DuploHttpClient exposes get/post/patch/delete returning
// Observables; REMOTE_UserSession carries the current workspace (.tenant.TenantId).
export const REMOTE_DuploHttpClient = 'REMOTE_DuploHttpClient';
export const REMOTE_UserSession = 'REMOTE_UserSession';

const ORIGIN_TYPE = 'AlertTriage';
const SUB_TYPE = 'alert-triage';
// MUST equal manifest resources[].restSegment and the controller [Route] (reference/00-naming.md).
const REST_SEGMENT = 'extensions/alerttriages';

/** The scope that carries the Neo4j MCP tools; attached automatically when the workspace has it. */
export const GRAPH_SCOPE_NAME = 'neo4j-mcp-scope';

export type Tier = 'clinical' | 'nudge' | 'informational';

// TriageResult: team-plan/CONTRACT.md §3.
export interface TriageEvidence {
  kind: string;
  code?: string;
  display: string;
  value?: number | null;
  unit?: string | null;
  date?: string | null;
}

export interface TriageAlert {
  id: string;
  ruleId: string;
  tier: Tier;
  priority: number;
  title: string;
  detail: string;
  recommendedAction?: string | null;
  evidence: TriageEvidence[];
  rationale?: string | null;
}

export interface TriageCounts { clinical: number; nudge: number; informational: number; }

export interface TriageResult {
  patientId?: string;
  patientName?: string;
  age?: number;
  sex?: string;
  memberSince?: string;
  asOf?: string;
  engineVersion?: string;
  synthetic?: boolean;
  counts?: TriageCounts;
  alerts?: TriageAlert[];
  summary?: string | null;
  graphStatus?: string | null;
  /** BaseResult: the platform stores status-callback faults here. */
  faults?: string[] | null;
}

export interface AlertTriageSpec {
  patientId: string;
  includeInformational: boolean;
  explain: boolean;
  scopeIds?: string[];
}

export interface AlertTriage {
  id: string;
  name: string;
  status: string;
  subStatus?: string;
  blockedReason?: string;
  faults?: string[];
  createdAt?: string;
  updatedAt?: string;
  spec?: Partial<AlertTriageSpec>;
  result?: TriageResult;
}

export interface WorkspaceScope { id: string; name: string; }

@Injectable({ providedIn: 'root' })
export class AlertTriageService {
  private readonly http = inject<any>(REMOTE_DuploHttpClient as any);
  private readonly session = inject<any>(REMOTE_UserSession as any);

  workspaceId(): string {
    return this.session?.tenant?.TenantId ?? '';
  }

  private base(): string {
    return `/v1/aiservicedesk/user/data/workspaces/${this.workspaceId()}/environment/${REST_SEGMENT}`;
  }

  // user/data endpoints return {data: …}; tickets/* return bare bodies. Normalize both.
  private unwrap = (r: any) => (r && r.data !== undefined ? r.data : r);

  list(): Observable<AlertTriage[]> {
    return this.http.get(this.base()).pipe(map((r: any) => {
      const d = this.unwrap(r);
      return (d?.items ?? d ?? []) as AlertTriage[];
    }));
  }

  get(id: string): Observable<AlertTriage> {
    return this.http.get(`${this.base()}/${id}`).pipe(map((r: any) => this.unwrap(r)));
  }

  create(name: string, spec: AlertTriageSpec): Observable<AlertTriage> {
    return this.http.post(this.base(), { name, spec }).pipe(map((r: any) => this.unwrap(r)));
  }

  /** Hard delete: only allowed in a terminal status that never provisioned (New / Failed / DeProvisioned). */
  delete(id: string): Observable<any> {
    return this.http.delete(`${this.base()}/${id}`);
  }

  /** Orchestrated teardown: the skill posts DeProvisioned and the platform removes the row. */
  deprovision(id: string): Observable<any> {
    return this.http.post(`${this.base()}/${id}/deprovision`, {});
  }

  /** Scopes attached to the current workspace (used to find neo4j-mcp-scope). Never errors. */
  listScopes(): Observable<WorkspaceScope[]> {
    const url = `/v1/aiservicedesk/user/data/workspaces/${this.workspaceId()}/scopes`;
    return this.http.get(url).pipe(
      map((r: any) => {
        const d = this.unwrap(r);
        return ((d?.items ?? d ?? []) as any[]).map(s => ({ id: s.id, name: s.name }));
      }),
      catchError(() => of([])),
    );
  }

  /** Resolve the provisioning ticket (its `name` is the chat URL segment). */
  ticketName(id: string): Observable<string | null> {
    const url = `/v1/aiservicedesk/tickets/${this.workspaceId()}/origin-context`
      + `?type=${ORIGIN_TYPE}&id=${id}&subType=${SUB_TYPE}`;
    return this.http.get(url).pipe(map((r: any) => this.unwrap(r)?.name ?? null));
  }
}
