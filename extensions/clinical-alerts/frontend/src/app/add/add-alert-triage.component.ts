import { Component, OnInit, computed, inject, signal, viewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormGroupErrorsComponent, SharedFormsModule } from '@duplocloud-internal/ng-common-lib';
import { AlertTriageService, GRAPH_SCOPE_NAME, WorkspaceScope } from '../alert-triage.service';
import { PATIENTS } from '../patients.generated';
import { SyntheticBannerComponent } from '../shared/synthetic-banner.component';
import { findPatient, monthYear, patientLabel } from '../shared/tiers';

// "New triage": pick a synthetic member, choose options, run. The resource name is generated, and the
// Neo4j scope is attached automatically when the workspace has it, so there is nothing to fumble on stage.
// There is no edit route: a triage is a point-in-time run; re-running means creating a new one.
@Component({
  selector: 'ca-add',
  imports: [SharedFormsModule, SyntheticBannerComponent],
  styles: [`
    :host { display: block; }
    .panel-form-accordion { background: #fff; padding: 1.25rem 0 1rem 1.5rem; }
    .panel-content-title { width: 265px; min-width: 265px; }
    .panel-content-title-sub-text { max-width: 220px; }
    .panel-content-form { max-width: 768px; flex: 1 1 auto; margin: 0 1rem; padding: 0 1rem; }
    .panel-content-sidenav { width: 265px; min-width: 265px; margin-left: 2rem; }
    .panel-content-sidenav .help-item { padding-bottom: 1rem; }
    .panel-content-sidenav .help-item-title { margin: 0; font-weight: 600; font-size: 0.9rem; }
    .member {
      margin-top: 0.5rem; padding: 0.6rem 0.8rem; border-radius: 0.5rem;
      background: #F9FAFB; border: 1px solid #EEF0F3; font-size: 0.85rem; color: #374151;
    }
    .member strong { color: #111827; }
    .opt { display: flex; gap: 0.75rem; align-items: flex-start; padding: 0.6rem 0; }
    .opt input { margin-top: 0.25rem; width: 1rem; height: 1rem; flex: none; }
    .opt .t { font-weight: 600; color: #111827; }
    .opt small { display: block; color: #6B7280; }
    .graph {
      display: flex; align-items: center; gap: 0.6rem; padding: 0.6rem 0.8rem; border-radius: 0.5rem;
      font-size: 0.85rem; border: 1px solid #E5E7EB;
    }
    .graph.on { background: #ECFDF5; border-color: #A7F3D0; color: #065F46; }
    .graph.off { background: #F9FAFB; color: #6B7280; }
    .graph .dot { width: 0.55rem; height: 0.55rem; border-radius: 50%; flex: none; }
    .graph.on .dot { background: #10B981; }
    .graph.off .dot { background: #D1D5DB; }
    code { font-size: 0.8rem; }
  `],
  template: `
    <ca-synthetic-banner />
    <div class="card panel-form-accordion">
      <div class="d-flex justify-content-between">

        <div class="panel-content-title">
          <h4 class="font-weight-bolder">New alert triage</h4>
          <p class="panel-content-title-sub-text text-muted">
            Run the clinical alert rules for one member. Rules decide which alerts fire, the knowledge graph
            connects them across the club, and the AI explains them in plain language.
          </p>
        </div>

        <div class="panel-content-form">
          <form name="AddTriageForm" #f="ngForm" class="form form-vertical" (ngSubmit)="f.valid && submit()">
            <div class="form-container" form-group-errors #formGroupErrors showDetailsWhen="submitted">
              <form-field>
                <label class="element-label">Member *</label>
                <select class="form-control" name="patientId" required validation-state validation-errors
                        [ngModel]="patientId()" (ngModelChange)="patientId.set($event)">
                  <option value="" disabled>Select a synthetic member…</option>
                  @for (p of patients; track p.id) {
                    <option [value]="p.id">{{ label(p) }}</option>
                  }
                </select>
                @if (selected(); as p) {
                  <div class="member">
                    <strong>{{ p.name }}</strong> · {{ p.age }} {{ p.sex }} ·
                    All-Inclusive member since {{ since(p.memberSince) }}
                  </div>
                }
              </form-field>

              <label class="opt">
                <input type="checkbox" name="includeInformational"
                       [ngModel]="includeInformational()" (ngModelChange)="includeInformational.set($event)" />
                <span><span class="t">Include informational updates</span>
                  <small>Weight progress, upcoming visits and new normal results, alongside clinical alerts and nudges.</small></span>
              </label>

              <label class="opt">
                <input type="checkbox" name="explain"
                       [ngModel]="explain()" (ngModelChange)="explain.set($event)" />
                <span><span class="t">Plain-language explanations</span>
                  <small>The AI writes a short rationale per alert and a patient summary. It never adds, removes or re-tiers an alert.</small></span>
              </label>

              <div class="graph mt-50" [class.on]="graphScope()" [class.off]="!graphScope()">
                <span class="dot"></span>
                @if (scopesLoading()) {
                  <span>Checking knowledge graph connection…</span>
                } @else if (graphScope()) {
                  <span><strong>Knowledge graph connected</strong>: results are written to Neo4j via <code>{{ graphScopeName }}</code>.</span>
                } @else {
                  <span><strong>Knowledge graph not attached</strong>: <code>{{ graphScopeName }}</code> isn't on this workspace, so the graph step will be skipped.</span>
                }
              </div>

              <div class="d-flex justify-content-end mt-2">
                <button type="button" class="btn btn-outline-secondary mr-1" (click)="back()">Cancel</button>
                <button type="submit" class="btn btn-primary" [disabled]="saving()">
                  {{ saving() ? 'Starting…' : 'Run triage' }}
                </button>
              </div>
            </div>
          </form>
        </div>

        <div class="panel-content-sidenav">
          <div class="help-item">
            <p class="help-item-title">Three tiers, like MSP severities</p>
            <small class="text-muted"><strong style="color:#C62828">Clinical</strong>: act today.
              <strong style="color:#EF6C00">Nudge</strong>: get ahead of it.
              <strong style="color:#1565C0">Informational</strong>: keep the member informed.</small>
          </div>
          <div class="help-item">
            <p class="help-item-title">Deterministic</p>
            <small class="text-muted">Alerts come from tested rules evaluated as of the demo date. The same member always yields the same alerts.</small>
          </div>
          <div class="help-item">
            <p class="help-item-title">Synthetic members only</p>
            <small class="text-muted">All seven members are fictional. No real patient data is used anywhere.</small>
          </div>
        </div>

      </div>
    </div>
  `,
})
export class AddAlertTriageComponent implements OnInit {
  private readonly svc = inject(AlertTriageService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected readonly patients = PATIENTS;
  protected readonly graphScopeName = GRAPH_SCOPE_NAME;
  protected readonly label = patientLabel;
  protected readonly since = monthYear;

  protected readonly patientId = signal('');
  protected readonly includeInformational = signal(true);
  protected readonly explain = signal(true);
  protected readonly saving = signal(false);
  protected readonly scopesLoading = signal(true);
  private readonly scopes = signal<WorkspaceScope[]>([]);

  protected readonly selected = computed(() => findPatient(this.patientId()));
  protected readonly graphScope = computed(() => this.scopes().find(s => s.name === GRAPH_SCOPE_NAME));

  private readonly formErrors = viewChild(FormGroupErrorsComponent);

  ngOnInit(): void {
    this.svc.listScopes().subscribe(s => {
      this.scopes.set(s);
      this.scopesLoading.set(false);
    });
  }

  protected submit(): void {
    const id = this.patientId();
    const scope = this.graphScope();
    this.saving.set(true);
    this.svc.create(this.resourceName(id), {
      patientId: id,
      includeInformational: this.includeInformational(),
      explain: this.explain(),
      scopeIds: scope ? [scope.id] : [],
    }).subscribe({
      next: created => created?.id
        ? this.router.navigate(['..', 'view', created.id], { relativeTo: this.route })
        : this.back(),
      error: err => {
        this.saving.set(false);
        this.formErrors()?.reportError(err);
      },
    });
  }

  protected back(): void {
    this.router.navigate(['..'], { relativeTo: this.route });
  }

  /** e.g. syn-001-20260929-143012: unique per run, valid resource name. */
  private resourceName(patientId: string): string {
    const d = new Date();
    const p = (n: number) => String(n).padStart(2, '0');
    const stamp = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
    return `${patientId.toLowerCase()}-${stamp}`;
  }
}
