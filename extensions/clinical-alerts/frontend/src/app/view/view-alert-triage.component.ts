import { Component, DestroyRef, LOCALE_ID, OnInit, computed, inject, signal } from '@angular/core';
import { JsonPipe, formatDate } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { CommonLibComponentsModule } from '@duplocloud-internal/ng-common-lib';
import { AlertTriage, AlertTriageService, Tier } from '../alert-triage.service';
import { AlertCardComponent } from '../shared/alert-card.component';
import { StatusBadgeComponent } from '../shared/status-badge.component';
import { SyntheticBannerComponent } from '../shared/synthetic-banner.component';
import { TierChipsComponent } from '../shared/tier-chips.component';
import { LifecyclePhase, LifecycleRailComponent, RailFact } from '../shared/lifecycle-rail.component';
import { TIERS, alertsByTier, findPatient, monthYear, shortDate } from '../shared/tiers';

// Detail page on the Template-G shell (reference/19-detail-page.md): header, Spec | Result, lifecycle rail.
// The Result's Overview is the product view: summary banner, then Clinical / Nudge / Informational alert cards.

/** CONTRACT §5 sub-steps → the rail phase they belong to. */
const PHASE_OF: Record<string, number> = {
  'Loading patient': 1,
  'Running alert rules': 1,
  'Updating knowledge graph': 2,
  'Graph unavailable — skipped': 2,
  'Writing clinical rationale': 3,
  'Saving results': 4,
};
const GRAPH_SKIPPED = 'Graph unavailable — skipped';

@Component({
  selector: 'ca-view',
  imports: [CommonLibComponentsModule, StatusBadgeComponent, LifecycleRailComponent, SyntheticBannerComponent,
    TierChipsComponent, AlertCardComponent, JsonPipe],
  styleUrl: '../shared/detail-page.scss',
  styles: [`
    .member-line { color: #4B5563; }
    .member-line strong { color: #111827; font-weight: 600; }
    .summary {
      display: flex; gap: 1rem; align-items: flex-start; justify-content: space-between; flex-wrap: wrap;
      padding: 1rem 1.1rem; border-radius: 0.6rem; margin-bottom: 1.25rem;
      background: linear-gradient(135deg, #F8FAFF 0%, #F5F3FF 100%); border: 1px solid #E6E8F5;
    }
    .summary .txt { flex: 1 1 22rem; }
    .summary .lbl { display: block; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; color: #6D5BD0; margin-bottom: 0.2rem; }
    .summary p { margin: 0; color: #1F2937; font-size: 0.95rem; line-height: 1.5; }
    .summary .meta { margin-top: 0.4rem; font-size: 0.78rem; color: #6B7280; }
    .graph-note { margin-top: 0.4rem; font-size: 0.78rem; color: #92400E; }
    .tier { margin-bottom: 1.4rem; }
    .tier-h { display: flex; align-items: baseline; gap: 0.6rem; margin-bottom: 0.6rem; padding-bottom: 0.35rem; border-bottom: 2px solid; }
    .tier-h h3 { margin: 0; font-size: 1rem; font-weight: 700; }
    .tier-h .n { font-size: 0.8rem; font-weight: 700; padding: 0 0.45rem; border-radius: 999px; color: #fff; }
    .tier-h .blurb { font-size: 0.8rem; color: #6B7280; }
    .cards { display: grid; gap: 0.7rem; }
    .empty { padding: 0.7rem 0.9rem; border-radius: 0.5rem; background: #F9FAFB; border: 1px dashed #E5E7EB; color: #6B7280; font-size: 0.87rem; }
    .empty .ok { color: #10B981; font-weight: 700; margin-right: 0.3rem; }
    .pending { padding: 2rem 1rem; text-align: center; color: #6B7280; }
    pre.raw { background: #0F172A; color: #E2E8F0; padding: 1rem; border-radius: 0.5rem; font-size: 0.78rem; max-height: 32rem; overflow: auto; }
  `],
  template: `
    <ca-synthetic-banner />
    @if (item(); as it) {
      <div class="ext-detail-page">

        <header class="g-head">
          <span class="g-tile-ic"><i data-feather="activity" size="26"></i></span>
          <div class="g-head-main">
            <div class="g-head-t">
              <h1>{{ patientName() }}</h1>
              <app-status-badge [status]="it.status"></app-status-badge>
              @if (working()) {
                <span class="dots-loader text-warning"><span></span><span></span><span></span></span>
              }
            </div>
            <div class="g-meta member-line">
              <span class="g-meta-item mono">{{ patientId() }}</span>
              @if (ageSex()) { <span class="sep">·</span><span class="g-meta-item">{{ ageSex() }}</span> }
              <span class="sep">·</span>
              <span class="g-meta-item"><strong>All-Inclusive member since {{ memberSince() }}</strong></span>
              @if (it.result?.asOf) {
                <span class="sep">·</span>
                <span class="g-meta-item"><span class="k">As of</span> {{ day(it.result?.asOf) }}</span>
              }
            </div>
          </div>
          <div class="g-actions">
            <div class="seg" role="group" aria-label="View">
              <button type="button" [class.active]="view() === 'spec'" (click)="view.set('spec')">Spec</button>
              <button type="button" [class.active]="view() === 'result'" (click)="view.set('result')">Result</button>
            </div>
            <button type="button" class="btn btn-sm btn-primary" [disabled]="tracking()" (click)="track()">
              <i data-feather="terminal" class="mr-50"></i>Agent ticket
            </button>
            <div ngbDropdown container="body" placement="bottom-right">
              <button type="button" class="btn btn-sm hide-arrow" aria-label="More actions" ngbDropdownToggle>
                <i data-feather="more-vertical"></i>
              </button>
              <div ngbDropdownMenu>
                <a ngbDropdownItem (click)="runAgain()"><i data-feather="refresh-cw" class="mr-50"></i> New triage</a>
                <a ngbDropdownItem class="text-danger" (click)="remove()"><i data-feather="trash-2" class="mr-50"></i> Delete</a>
              </div>
            </div>
          </div>
        </header>

        <div class="g-cols">
          <section class="g-card g-main">
            @if (view() === 'spec') {
              <div class="g-sec pt-1">
                <div class="g-sec-h"><h3>Requested triage</h3></div>
                <div class="g-tiles c3">
                  @for (t of specTiles(); track t.label) {
                    <div class="g-tile">
                      <div class="g-tl">{{ t.label }}</div>
                      <span class="g-tv">{{ t.value }}</span>
                    </div>
                  }
                </div>
              </div>
            } @else {
              <scrollable-nav-tab>
                <ul ngbNav #resultNav="ngbNav" class="nav nav-tabs flat-tabs g-tabs" [(activeId)]="activeTab">
                  <li [ngbNavItem]="'overview'">
                    <a ngbNavLink>Alerts</a>
                    <ng-template ngbNavContent>
                      @if (it.faults?.length) {
                        <div class="alert alert-danger py-1 px-2 mb-1">
                          @for (f of it.faults; track f) { <div>{{ f }}</div> }
                        </div>
                      }
                      @if (it.result?.alerts) {
                        <div class="summary">
                          <div class="txt">
                            <span class="lbl">{{ it.result?.summary ? 'Patient summary · AI explanation' : 'Triage summary' }}</span>
                            <p>{{ summary() }}</p>
                            <div class="meta">Engine {{ it.result?.engineVersion || '—' }} · rules decide, the graph connects, the AI explains.</div>
                            @if (graphSkipped()) {
                              <div class="graph-note">Knowledge graph unavailable: this triage wasn't written to Neo4j.</div>
                            }
                          </div>
                          <ca-tier-chips [counts]="it.result?.counts" />
                        </div>

                        @for (t of tiers; track t.key) {
                          <div class="tier">
                            <div class="tier-h" [style.border-color]="t.color">
                              <h3 [style.color]="t.color">{{ t.label }}</h3>
                              <span class="n" [style.background]="t.color">{{ grouped()[t.key].length }}</span>
                              <span class="blurb">{{ t.blurb }}</span>
                            </div>
                            @if (grouped()[t.key].length) {
                              <div class="cards">
                                @for (a of grouped()[t.key]; track a.id) {
                                  <ca-alert-card [alert]="a" [explainPending]="explainPending()" />
                                }
                              </div>
                            } @else {
                              <div class="empty">
                                <span class="ok">✓</span>{{ t.empty }}
                                @if (t.key === 'informational' && it.spec?.includeInformational === false) { (not requested for this run) }
                              </div>
                            }
                          </div>
                        }
                      } @else {
                        <div class="pending">
                          @if (it.status === 'Failed') {
                            Triage failed before any alerts were produced.
                          } @else {
                            {{ it.subStatus || 'Starting triage' }}…
                          }
                        </div>
                      }
                    </ng-template>
                  </li>
                  <li [ngbNavItem]="'raw'">
                    <a ngbNavLink>Raw result</a>
                    <ng-template ngbNavContent>
                      <pre class="raw">{{ it.result | json }}</pre>
                    </ng-template>
                  </li>
                </ul>
              </scrollable-nav-tab>
              <div [ngbNavOutlet]="resultNav" class="mt-50"></div>
            }
          </section>

          <ext-lifecycle-rail
            [phases]="phases()"
            [attached]="attached()"
            [trackable]="true"
            [trackBusy]="tracking()"
            trackLabel="Open agent ticket"
            (track)="track()" />
        </div>
      </div>
    } @else {
      <div class="text-muted p-2">Loading…</div>
    }
  `,
})
export class ViewAlertTriageComponent implements OnInit {
  private static readonly WAITING = ['Blocked', 'WaitingForApproval'];
  private static readonly READY = ['Complete', 'Updated'];
  private static readonly TEARDOWN = ['DeProvisioning', 'DeprovisionInitiated', 'DeProvisioned', 'DeprovisionFailed'];
  private static readonly DELETABLE = ['New', 'Failed', 'DeProvisioned'];

  private readonly svc = inject(AlertTriageService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly locale = inject(LOCALE_ID);

  protected readonly item = signal<AlertTriage | undefined>(undefined);
  protected readonly view = signal<'spec' | 'result'>('result');
  protected readonly tracking = signal(false);
  /** Set once a poll sees the "Graph unavailable" beat, so the rail keeps the warning after it passes. */
  private readonly graphSkipSeen = signal(false);
  /** Highest phase index seen while working (sub-steps only move forward). */
  private readonly maxPhase = signal(1);
  protected activeTab = 'overview';

  protected readonly tiers = TIERS;
  protected readonly day = shortDate;

  private poll?: Subscription;

  protected readonly working = computed(() => {
    const s = this.item()?.status ?? '';
    return !!s && !ViewAlertTriageComponent.WAITING.includes(s) && !ViewAlertTriageComponent.READY.includes(s)
      && s !== 'Failed' && !ViewAlertTriageComponent.TEARDOWN.includes(s);
  });

  protected readonly patientId = computed(() => this.item()?.result?.patientId || this.item()?.spec?.patientId || '—');
  private readonly patient = computed(() => findPatient(this.patientId()));
  protected readonly patientName = computed(() => this.item()?.result?.patientName || this.patient()?.name || this.patientId());
  protected readonly ageSex = computed(() => {
    const r = this.item()?.result;
    const age = r?.age ?? this.patient()?.age;
    const sex = r?.sex ?? this.patient()?.sex;
    return age != null ? `${age} ${sex ?? ''}`.trim() : '';
  });
  protected readonly memberSince = computed(() => monthYear(this.item()?.result?.memberSince || this.patient()?.memberSince));

  protected readonly graphSkipped = computed(() =>
    this.item()?.result?.graphStatus === 'skipped' || this.graphSkipSeen());

  protected readonly explainPending = computed(() => !!this.item()?.spec?.explain && this.working());

  protected readonly summary = computed(() => {
    const r = this.item()?.result;
    if (r?.summary) {
      return r.summary;
    }
    const c = r?.counts ?? { clinical: 0, nudge: 0, informational: 0 };
    const n = (k: number, one: string, many: string) => `${k} ${k === 1 ? one : many}`;
    const lead = c.clinical ? `needs attention today` : c.nudge ? `has items to get ahead of` : `is on track`;
    return `${this.patientName()} ${lead}: ${n(c.clinical, 'clinical alert', 'clinical alerts')}, `
      + `${n(c.nudge, 'nudge', 'nudges')} and ${n(c.informational, 'informational update', 'informational updates')}.`;
  });

  protected readonly grouped = computed(() => {
    const r = this.item()?.result;
    return Object.fromEntries(TIERS.map(t => [t.key, alertsByTier(r, t.key)])) as Record<Tier, ReturnType<typeof alertsByTier>>;
  });

  /** The triage's own ladder, driven by the CONTRACT §5 sub-steps. */
  protected readonly phases = computed<LifecyclePhase[]>(() => {
    const it = this.item();
    if (!it) {
      return [];
    }
    const s = it.status;
    const ready = ViewAlertTriageComponent.READY.includes(s);
    const failed = s === 'Failed';
    const waiting = ViewAlertTriageComponent.WAITING.includes(s);
    const working = this.working();
    const cur = this.maxPhase();
    const explain = it.spec?.explain !== false;

    const state = (i: number): LifecyclePhase['state'] => {
      if (ready) return 'done';
      if (failed) return i < cur ? 'done' : i === cur ? 'fail' : 'todo';
      if (working || waiting) return i < cur ? 'done' : i === cur ? 'now' : 'todo';
      return 'todo';
    };
    const live = (i: number, idle: string) =>
      (working && i === cur) ? (it.subStatus || idle) : (failed && i === cur) ? (it.faults?.[0] || it.subStatus || 'Failed') : idle;

    const graphState = this.graphSkipped() && (ready || cur > 2) ? 'warn' : state(2);

    const phases: LifecyclePhase[] = [
      { label: 'Requested', subtitle: this.fmt(it.createdAt), state: 'done' },
      { label: 'Rules engine', subtitle: live(1, 'Deterministic alert rules'), state: state(1) },
      { label: 'Knowledge graph', subtitle: graphState === 'warn' ? 'Graph unavailable — skipped' : live(2, 'Member + alerts written to Neo4j'), state: graphState },
      { label: 'Clinical rationale', subtitle: explain ? live(3, 'AI explains each alert in plain language') : 'Skipped (not requested)', state: state(3) },
      { label: 'Results ready', subtitle: ready ? this.fmt(it.updatedAt) : live(4, 'Alert cards posted'), state: state(4) },
    ];
    if (waiting) {
      phases.splice(cur + 1, 0, {
        label: 'Needs your input',
        subtitle: s === 'WaitingForApproval' ? 'Approval pending' : (it.blockedReason || 'Question pending'),
        state: 'now',
        action: { label: 'Review', run: () => this.track() },
      });
    }
    return phases;
  });

  protected readonly specTiles = computed(() => {
    const it = this.item();
    const p = this.patient();
    return [
      { label: 'Member', value: p ? `${p.id} — ${p.name}` : (it?.spec?.patientId || '—') },
      { label: 'Informational updates', value: it?.spec?.includeInformational === false ? 'Excluded' : 'Included' },
      { label: 'AI explanations', value: it?.spec?.explain === false ? 'Off' : 'On' },
      { label: 'Knowledge graph scope', value: it?.spec?.scopeIds?.length ? 'neo4j-mcp-scope' : 'Not attached' },
      { label: 'Run started', value: this.fmt(it?.createdAt) },
      { label: 'Resource', value: it?.name || '—' },
    ];
  });

  protected readonly attached = computed<RailFact[]>(() => {
    const it = this.item();
    return [
      { label: 'Engine', value: it?.result?.engineVersion || '—' },
      { label: 'Alerts', value: it?.result?.alerts?.length ?? '—' },
      { label: 'Updated', value: this.fmt(it?.updatedAt) },
    ];
  });

  ngOnInit(): void {
    this.refresh();
    this.destroyRef.onDestroy(() => this.poll?.unsubscribe());
  }

  /** GET + a 2s poll while the agent is working, so the rail moves with each sub-step. */
  private refresh(): void {
    const id = this.route.snapshot.params['id'];
    this.svc.get(id).subscribe(i => {
      this.item.set(i);
      const ph = PHASE_OF[i?.subStatus ?? ''];
      if (ph && ph > this.maxPhase()) {
        this.maxPhase.set(ph);
      }
      if (i?.subStatus === GRAPH_SKIPPED) {
        this.graphSkipSeen.set(true);
      }
      if (this.working() && !this.poll) {
        this.poll = interval(2000).subscribe(() => this.refresh());
      }
      if (!this.working() && this.poll) {
        this.poll.unsubscribe();
        this.poll = undefined;
      }
    });
  }

  protected fmt(v?: string): string {
    return v ? formatDate(v, 'medium', this.locale) : '—';
  }

  protected runAgain(): void {
    this.router.navigate(['../..', 'add'], { relativeTo: this.route });
  }

  /** Terminal-never-provisioned rows are hard-deleted; completed ones go through deprovision (the skill acks). */
  protected remove(): void {
    const it = this.item();
    if (!it || !window.confirm(`Delete this triage for ${this.patientName()}?`)) {
      return;
    }
    const call = ViewAlertTriageComponent.DELETABLE.includes(it.status) ? this.svc.delete(it.id) : this.svc.deprovision(it.id);
    call.subscribe({ next: () => this.router.navigate(['../..'], { relativeTo: this.route }) });
  }

  protected track(): void {
    const it = this.item();
    if (!it) {
      return;
    }
    this.tracking.set(true);
    this.svc.ticketName(it.id).subscribe({
      next: name => {
        this.tracking.set(false);
        if (!name) {
          return;
        }
        const url = `/ai/service-desk/${this.svc.workspaceId()}/tickets/chat/${name}`;
        this.router.navigateByUrl(url).then(ok => { if (!ok) window.location.assign(url); })
          .catch(() => window.location.assign(url));
      },
      error: () => this.tracking.set(false),
    });
  }
}
