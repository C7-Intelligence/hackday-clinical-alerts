import { Tier, TriageAlert, TriageResult } from '../alert-triage.service';
import { PATIENTS, SyntheticPatient } from '../patients.generated';

// Tier colours and labels: team-plan/CONTRACT.md §3.
export interface TierDef {
  key: Tier;
  label: string;
  short: string;
  blurb: string;
  empty: string;
  color: string;
  tint: string;
}

export const TIERS: TierDef[] = [
  { key: 'clinical', label: 'Clinical', short: 'Clinical', blurb: 'Act now: care team review today',
    empty: 'No clinical alerts', color: '#C62828', tint: 'rgba(198, 40, 40, 0.08)' },
  { key: 'nudge', label: 'Nudge', short: 'Nudge', blurb: 'Get ahead of it: outreach this week',
    empty: 'No nudges', color: '#EF6C00', tint: 'rgba(239, 108, 0, 0.08)' },
  { key: 'informational', label: 'Informational', short: 'Info', blurb: 'Keep the member informed',
    empty: 'No informational updates', color: '#1565C0', tint: 'rgba(21, 101, 192, 0.08)' },
];

export function tierDef(t: string | undefined): TierDef {
  return TIERS.find(d => d.key === t) ?? TIERS[2];
}

export function alertsByTier(r: TriageResult | undefined, t: Tier): TriageAlert[] {
  return (r?.alerts ?? []).filter(a => a.tier === t);
}

export function findPatient(id: string | undefined): SyntheticPatient | undefined {
  return PATIENTS.find(p => p.id === id);
}

export function sexShort(sex: string | undefined): string {
  return sex ? sex.charAt(0).toUpperCase() : '';
}

/** "SYN-001 — David Park, 51 M" */
export function patientLabel(p: SyntheticPatient): string {
  return `${p.id} — ${p.name}, ${p.age} ${sexShort(p.sex)}`;
}

/** "2024-05-01" → "May 2024" (no timezone shifting: the date is a calendar date). */
export function monthYear(iso: string | undefined): string {
  const m = /^(\d{4})-(\d{2})/.exec(iso ?? '');
  if (!m) {
    return '—';
  }
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[+m[2] - 1]} ${m[1]}`;
}

/** "2026-09-26" → "Sep 26, 2026" (calendar date, no timezone shifting). */
export function shortDate(iso: string | null | undefined): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? '');
  if (!m) {
    return iso ?? '—';
  }
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[+m[2] - 1]} ${+m[3]}, ${m[1]}`;
}
