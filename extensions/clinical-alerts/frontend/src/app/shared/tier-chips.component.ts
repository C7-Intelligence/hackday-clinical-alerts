import { Component, input } from '@angular/core';
import { TriageCounts } from '../alert-triage.service';
import { TIERS } from './tiers';

/** Three coloured count chips: clinical / nudge / informational. Zero counts render muted. */
@Component({
  selector: 'ca-tier-chips',
  styles: [`
    :host { display: inline-flex; gap: 0.35rem; flex-wrap: wrap; }
    .chip {
      display: inline-flex; align-items: center; gap: 0.3rem;
      padding: 0.1rem 0.55rem; border-radius: 999px;
      font-size: 0.78rem; font-weight: 600; line-height: 1.4;
      border: 1px solid transparent; white-space: nowrap;
    }
    .chip .n { font-variant-numeric: tabular-nums; }
    .chip.zero { background: #F3F4F6 !important; color: #9CA3AF !important; border-color: #E5E7EB !important; }
  `],
  template: `
    @if (counts(); as c) {
      @for (t of tiers; track t.key) {
        <span class="chip" [class.zero]="!c[t.key]" [title]="t.label"
              [style.background]="t.tint" [style.color]="t.color" [style.border-color]="t.color + '33'">
          <span class="n">{{ c[t.key] }}</span> {{ t.short }}
        </span>
      }
    } @else {
      <span class="text-muted">—</span>
    }
  `,
})
export class TierChipsComponent {
  readonly counts = input<TriageCounts | undefined>(undefined);
  protected readonly tiers = TIERS;
}
