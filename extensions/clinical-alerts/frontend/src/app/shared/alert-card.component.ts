import { Component, computed, input, signal } from '@angular/core';
import { TriageAlert } from '../alert-triage.service';
import { shortDate, tierDef } from './tiers';

/** One alert: tier-coloured edge, title, detail, AI rationale, recommended action, collapsible evidence. */
@Component({
  selector: 'ca-alert-card',
  styles: [`
    :host { display: block; }
    .card-a {
      position: relative; background: #fff; border: 1px solid #E5E7EB; border-radius: 0.6rem;
      padding: 0.9rem 1rem 0.8rem 1.15rem; overflow: hidden;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }
    .edge { position: absolute; left: 0; top: 0; bottom: 0; width: 4px; }
    .top { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; }
    h4 { margin: 0; font-size: 1rem; font-weight: 600; color: #111827; line-height: 1.35; }
    .rule { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.72rem; color: #6B7280; white-space: nowrap; }
    .detail { margin: 0.35rem 0 0; color: #374151; font-size: 0.9rem; }
    .why {
      margin-top: 0.65rem; padding: 0.55rem 0.7rem; border-radius: 0.45rem;
      background: #F5F3FF; color: #3B2F74; font-size: 0.87rem;
    }
    .why .lbl, .act .lbl { display: block; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 0.1rem; }
    .why .lbl { color: #6D5BD0; }
    .why.pending { background: #F9FAFB; color: #6B7280; font-style: italic; }
    .act { margin-top: 0.6rem; font-size: 0.88rem; color: #111827; }
    .act .lbl { color: #6B7280; }
    .toggle {
      margin-top: 0.6rem; background: none; border: 0; padding: 0; cursor: pointer;
      font-size: 0.8rem; font-weight: 600; color: #4B5563;
    }
    .toggle:hover { color: #111827; }
    .caret { display: inline-block; transition: transform 0.15s; margin-right: 0.25rem; }
    .caret.open { transform: rotate(90deg); }
    .ev { overflow-x: auto; margin-top: 0.45rem; }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    th { text-align: left; font-weight: 600; color: #6B7280; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.03em; padding: 0.3rem 0.5rem; border-bottom: 1px solid #E5E7EB; }
    td { padding: 0.35rem 0.5rem; border-bottom: 1px solid #F3F4F6; color: #1F2937; vertical-align: top; }
    td.num { font-variant-numeric: tabular-nums; white-space: nowrap; font-weight: 600; }
    td.dt { white-space: nowrap; color: #4B5563; }
    .kind { display: inline-block; padding: 0 0.4rem; border-radius: 0.3rem; background: #F3F4F6; color: #4B5563; font-size: 0.72rem; text-transform: capitalize; }
  `],
  template: `
    @let a = alert();
    <div class="card-a">
      <span class="edge" [style.background]="tier().color"></span>
      <div class="top">
        <h4>{{ a.title }}</h4>
        <span class="rule">{{ a.ruleId }}</span>
      </div>
      <p class="detail">{{ a.detail }}</p>

      @if (a.rationale) {
        <div class="why"><span class="lbl">Why it matters · AI explanation</span>{{ a.rationale }}</div>
      } @else if (explainPending()) {
        <div class="why pending">Plain-language rationale pending…</div>
      }

      @if (a.recommendedAction) {
        <div class="act"><span class="lbl">Recommended action</span>{{ a.recommendedAction }}</div>
      }

      @if (a.evidence?.length) {
        <button type="button" class="toggle" (click)="open.set(!open())" [attr.aria-expanded]="open()">
          <span class="caret" [class.open]="open()">▸</span>Evidence ({{ a.evidence.length }})
        </button>
        @if (open()) {
          <div class="ev">
            <table>
              <thead><tr><th>Kind</th><th>Item</th><th>Value</th><th>Date</th></tr></thead>
              <tbody>
                @for (e of a.evidence; track $index) {
                  <tr>
                    <td><span class="kind">{{ e.kind }}</span></td>
                    <td>{{ e.display }}</td>
                    <td class="num">{{ e.value ?? '—' }}@if (e.value != null && e.unit) {<span> {{ e.unit }}</span>}</td>
                    <td class="dt">{{ fmt(e.date) }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      }
    </div>
  `,
})
export class AlertCardComponent {
  readonly alert = input.required<TriageAlert>();
  /** True while the agent may still write a rationale (explain on, triage not finished). */
  readonly explainPending = input(false);

  protected readonly tier = computed(() => tierDef(this.alert().tier));
  protected readonly open = signal(false);
  protected readonly fmt = shortDate;
}
