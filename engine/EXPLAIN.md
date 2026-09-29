# Explain instructions (for the `triage-patient` skill)

> Paste the block below into `SKILL.md` as the "Writing clinical rationale" step. Run it only when
> `spec.explain` is true. When it's false, leave every `rationale` and the `summary` as `null`.

**The LLM explains. It never decides.** The engine has already decided which alerts exist, their tiers, and
their priorities. This step adds words only.

---

### Step: Writing clinical rationale

Post the sub-status `Writing clinical rationale`. You have the engine's `TriageResult` JSON in
`result.json`. Fill in text fields only, as follows.

**For each alert, set `rationale`**: 1–2 plain-language sentences a member could understand. They should
answer *"why does this matter, and why now?"*

- Ground every statement **only** in that alert's `title`, `detail`, and `evidence`. Numbers, dates,
  medications, and trends must appear there exactly as you write them. Don't round, convert units, or
  infer values that aren't shown.
- Say what the finding is and why it matters for the therapy involved. Examples: testosterone can
  thicken the blood, GLP-1 nausea can lead to dehydration, a trend matters before it crosses a line.
- Match the tone to the tier:
  - `clinical`: calm and direct. The care team is acting today. Don't alarm.
  - `nudge`: encouraging. It's worth getting ahead of.
  - `informational`: positive or neutral.
- Don't diagnose, name new conditions, or prescribe beyond `recommendedAction`. Don't contradict
  `detail`. Don't mention other alerts. Don't add caveats about being an AI.

**Set `summary`**: one short paragraph (2–3 sentences) for the whole member.

- Lead with the most urgent item. If there's a clinical alert, name it first. Then mention the nudges,
  then the good news or FYIs in a clause.
- Mention every tier that has alerts, and only those. If there are no alerts, say that everything
  reviewed is on track.
- Use the member's first name (from `patientName`). Plain language, no jargon without a short gloss
  (for example "hematocrit (the share of blood made of red cells)").

**Hard rules. Breaking any of these is a failed triage:**

1. Never add, remove, reorder, or re-tier alerts. Never change `ruleId`, `tier`, `priority`, `title`,
   `detail`, `recommendedAction`, `evidence`, or `counts`.
2. Change only `alerts[].rationale` (string) and `summary` (string).
3. Every number or date in your text must already appear in that alert's `title`, `detail`, or
   `evidence` (for the summary: in any alert's `title` or `detail`).
4. This is synthetic demo data. Never imply it's a real person's record, and never use real PHI.

Write the updated JSON back to `result.json`, then check it before posting:

```bash
# Every alert still present, nothing re-tiered, text filled in.
jq -e '(.alerts | all(.rationale | type == "string" and length > 0)) and (.summary | type == "string")' result.json
diff <(jq -S '[.alerts[] | del(.rationale)], .counts' result.engine.json) \
     <(jq -S '[.alerts[] | del(.rationale)], .counts' result.json)
```

(Keep an untouched copy of the engine output as `result.engine.json` before this step so the `diff` can
prove nothing but text changed.) If either check fails, discard your edits, post the engine's result with
`rationale`/`summary` left `null`, and add a fault note `Explanation skipped`. Alerts from the engine are
never lost because the explanation step failed.

---

## Reference: what good looks like (SYN-001, David Park)

| Alert | Example `rationale` |
| --- | --- |
| CLIN-TRT-ERYTHROCYTOSIS | "David's hematocrit reached 54.8% on 2026-09-26, up from 52.1% and 49.5%. On testosterone therapy that means thicker blood and a higher clot risk, so his care team is reviewing his dose today." |
| NUDGE-TRT-BP-ELEVATED | "His last two blood pressure readings, 148/94 and 144/90, are both elevated while on testosterone. Catching it now makes it easier to bring back down." |
| NUDGE-GLP1-HYDRATION | "His BUN of 26 mg/dL is high relative to his creatinine (a ratio of 23.6), a pattern that usually means he isn't drinking enough. Tirzepatide nausea often causes that, and hydrating now helps protect his kidneys." |
| INFO-WEIGHT-PROGRESS | "David is down 14.0%, from 112 kg to 96.3 kg, since starting tirzepatide. That's real progress." |

**Summary:** "David needs his care team today: his hematocrit hit 54.8% on testosterone therapy. Two
things are worth getting ahead of: his blood pressure is creeping up, and his labs suggest he needs more
fluids on tirzepatide. On the bright side, he's down 14.0% body weight, and his TRT dose review is
coming up on 2026-10-02."
