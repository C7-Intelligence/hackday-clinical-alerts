import { Component, DestroyRef, OnInit, computed, inject, signal, viewChild } from '@angular/core';
import { DatePipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { FilterTableUtils, SearchableDatatableComponent, SearchableDatatableModule } from '@duplocloud-internal/ng-common-lib';
import { AlertTriage, AlertTriageService, REMOTE_UserSession } from '../alert-triage.service';
import { StatusBadgeComponent } from '../shared/status-badge.component';
import { SyntheticBannerComponent } from '../shared/synthetic-banner.component';
import { TierChipsComponent } from '../shared/tier-chips.component';
import { findPatient } from '../shared/tiers';

/** A list row with the patient's display name resolved (result first, then the baked-in member list). */
interface Row extends AlertTriage {
  patientName: string;
  patientId: string;
}

@Component({
  selector: 'ca-list',
  imports: [SearchableDatatableModule, StatusBadgeComponent, SyntheticBannerComponent, TierChipsComponent, DatePipe],
  styles: [`
    .pt-name { font-weight: 600; color: #111827; cursor: pointer; }
    .pt-name:hover { color: var(--primary, #7367F0); }
    .pt-id { display: block; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.75rem; color: #6B7280; }
    .when { color: #4B5563; font-size: 0.85rem; }
  `],
  template: `
    <ca-synthetic-banner />
    <div class="card datatable-card">
      <searchable-datatable
        [showAdd]="true"
        addLabel="New triage"
        (add)="add()"
        [rows]="rows()"
        (filter)="filterUpdate()"
        columnMode="force">

        <ngx-datatable-column [width]="50" [sortable]="false" [canAutoResize]="false" cellClass="actions">
          <ng-template ngx-datatable-cell-template let-row="row">
            <div ngbDropdown container="body">
              <button class="btn btn-sm hide-arrow" ngbDropdownToggle>
                <i data-feather="more-vertical"></i>
              </button>
              <div ngbDropdownMenu>
                <a ngbDropdownItem (click)="view(row)">
                  <i data-feather="eye" class="mr-50"></i><span>View alerts</span>
                </a>
                <a ngbDropdownItem (click)="track(row)">
                  <i data-feather="activity" class="mr-50"></i><span>Open agent ticket</span>
                </a>
              </div>
            </div>
          </ng-template>
        </ngx-datatable-column>

        <ngx-datatable-column name="Patient" prop="patientName" [flexGrow]="190">
          <ng-template ngx-datatable-cell-template let-row="row">
            <a class="pt-name" (click)="view(row)">{{ row.patientName }}</a>
            <span class="pt-id">{{ row.patientId }}</span>
          </ng-template>
        </ngx-datatable-column>

        <ngx-datatable-column name="Alerts" [flexGrow]="230" [sortable]="false">
          <ng-template ngx-datatable-cell-template let-row="row">
            @if (row.result?.counts) {
              <ca-tier-chips [counts]="row.result.counts" />
            } @else {
              <span class="text-muted">{{ row.status === 'Failed' ? '—' : 'Triaging…' }}</span>
            }
          </ng-template>
        </ngx-datatable-column>

        <ngx-datatable-column name="Status" [flexGrow]="110" [maxWidth]="160">
          <ng-template ngx-datatable-cell-template let-row="row">
            <app-status-badge [status]="row.status"></app-status-badge>
          </ng-template>
        </ngx-datatable-column>

        <ngx-datatable-column name="Run" prop="createdAt" [flexGrow]="140">
          <ng-template ngx-datatable-cell-template let-row="row">
            <span class="when">{{ row.createdAt | date:'MMM d, h:mm a' }}</span>
          </ng-template>
        </ngx-datatable-column>

      </searchable-datatable>
    </div>
  `,
})
export class ListAlertTriageComponent implements OnInit {
  private readonly svc = inject(AlertTriageService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly session = inject<any>(REMOTE_UserSession as any);
  private readonly destroyRef = inject(DestroyRef);

  private readonly table = viewChild(SearchableDatatableComponent);

  private readonly allRows = signal<Row[]>([]);
  private readonly filterTerm = signal('');

  private readonly searchFields = ['patientName', 'patientId', 'status', 'name'];

  protected readonly rows = computed(() => {
    const term = this.filterTerm();
    const all = this.allRows();
    return term ? all.filter(r => FilterTableUtils.searchByFields(r, this.searchFields, term)) : all;
  });

  ngOnInit(): void {
    this.session.getTenantRefreshTimer(true)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(([, tenantChanged]: [any, boolean]) => this.refresh(!!tenantChanged));
  }

  private refresh(tenantChanged: boolean): void {
    if (tenantChanged) {
      this.table()?.startLoading();
    }
    this.svc.list().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: rows => {
        const mapped = (rows ?? []).map(r => {
          const id = r.result?.patientId || r.spec?.patientId || '';
          return { ...r, patientId: id, patientName: r.result?.patientName || findPatient(id)?.name || id || '—' };
        });
        // Newest run first.
        mapped.sort((a, b) => (b.createdAt ?? '').localeCompare(a.createdAt ?? ''));
        this.allRows.set(mapped);
        this.table()?.refresh();
      },
      error: () => {
        this.allRows.set([]);
        this.table()?.stopLoading();
      },
    });
  }

  protected filterUpdate(): void {
    this.filterTerm.set(this.table()?.searchTerm?.toLowerCase()?.trim() ?? '');
  }

  protected add(): void {
    this.router.navigate(['add'], { relativeTo: this.route });
  }

  protected view(r: AlertTriage): void {
    this.router.navigate(['view', r.id], { relativeTo: this.route });
  }

  protected track(r: AlertTriage): void {
    this.svc.ticketName(r.id).subscribe(name => {
      if (!name) {
        return;
      }
      this.router.navigate(['/ai/service-desk', this.svc.workspaceId(), 'tickets', 'chat', name]);
    });
  }
}
