import { Component } from '@angular/core';

/** Shown on every screen of the extension (team-plan/README.md §7, §8). */
@Component({
  selector: 'ca-synthetic-banner',
  styles: [`
    :host { display: block; margin-bottom: 1rem; }
    .banner {
      display: flex; align-items: center; gap: 0.6rem;
      padding: 0.55rem 0.9rem; border-radius: 0.5rem;
      background: #FFF8E1; border: 1px solid #FFE082; color: #6D4C00;
      font-size: 0.85rem;
    }
    .dot { width: 0.5rem; height: 0.5rem; border-radius: 50%; background: #F9A825; flex: none; }
    strong { font-weight: 600; }
  `],
  template: `
    <div class="banner" role="note">
      <span class="dot" aria-hidden="true"></span>
      <span><strong>Synthetic data — not for clinical use.</strong>
        Fictional members; alert thresholds are illustrative for a demo, not clinical guidance.</span>
    </div>
  `,
})
export class SyntheticBannerComponent {}
