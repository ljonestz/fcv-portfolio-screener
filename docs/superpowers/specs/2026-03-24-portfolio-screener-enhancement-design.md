# Design Spec: Portfolio Screener Enhancement
**Date:** 2026-03-24
**Project:** FCV Portfolio Screener
**Status:** Approved

---

## Problem Statement

Running a full portfolio screen for a large country (e.g., Ethiopia, 56 projects) consumes 2–3 Claude Code session windows. The root causes are:

1. **Oversized PAD input:** Each PAD is extracted at up to 120k characters (~17.5k tokens), but 40–50% is boilerplate irrelevant to FCV assessment (procurement, financial management, legal covenants, abbreviations).
2. **Design-only assessment:** The current screener evaluates only the PAD, missing the operational record captured in Implementation Status Reports (ISRs) and Implementation Completion Reports (ICRs). A project's actual FCV sensitivity may differ significantly from its design-time intent.

---

## Goals

1. Reduce per-project token usage by ~40–50% through targeted section filtering on PAD text — without sacrificing analytical quality.
2. Enable score adjustment based on ISR/ICR evidence, capturing how FCV sensitivity was maintained (or not) during implementation.
3. Keep the overall token budget per project roughly constant (PAD savings offset ISR additions) while substantially improving analytical depth.

---

## Non-Goals

- Do not reduce the depth or rigour of the 8-dimension FCV scoring methodology.
- Do not modify the normalization, analytics, or reporting pipeline (those remain unchanged).
- Do not change the primary data source: the PAD remains the anchor for all dimension scores.

---

## Design

### Component 1 — PAD Section Filter

**File:** `utils/pad_section_filter.py`

**Purpose:** Strip FCV-irrelevant boilerplate from PAD extracted text before it is sent to the screener. Save filtered versions to a separate subfolder so originals are always preserved.

**Sections to retain (FCV-relevant):**

| Section | PAD Location | FCV Relevance |
|---|---|---|
| Strategic Context (A, B, C) | Section I | Country context, conflict drivers, fragility indicators |
| Project Development Objectives | Section II | Targeting language, inclusion, beneficiary design |
| Project Description / Components | Section III | Delivery mechanisms, conflict-sensitive design |
| Implementation & M&E | Section IV | Adaptive management, monitoring for harm |
| Key Risks (SORT) | Section V | Political, security, social risk ratings |
| Social Safeguards | Section VI.E | Stakeholder engagement, GRM, conflict sensitivity |
| Environment Safeguards | Section VI.F | ESCP commitments |
| Results Framework | Annex 1 | What is measured — including any do-no-harm indicators |
| Implementation Arrangements | Annex 3 | Institutional roles, adaptive capacity |
| Social Safeguards Annex | Annex 7 | Detailed SEP, ESMF, GRM design |

**Sections to strip (boilerplate):**

- Front matter: title page, currency equivalents, fiscal year, abbreviations & acronyms, team roster
- Section VI.C: Financial Management
- Section VI.D: Procurement
- Section VI.A–B: Economic and Financial Analysis
- Annex 5: Economic Analysis
- Annex 6: Financial Analysis
- Legal Covenants, Compliance tables, Disbursement
- Bank Lending & Implementation Support (supervision costs)
- Borrower/Co-financier comments
- Supporting Documents list

**Section detection:** Uses regex patterns matching the standard WBG PAD template. All patterns must be applied with `re.MULTILINE` and tested against real PyMuPDF (`fitz`) output — PyMuPDF concatenates page text and section headers may have trailing whitespace or mixed case:

```python
# Level 1 — Roman numeral sections (case-insensitive, strip trailing whitespace)
r'^\s*([IVX]+)\.\s+([A-Z][A-Za-z\s]+?)\s*$'   # re.MULTILINE | re.IGNORECASE

# Level 2 — Lettered subsections
r'^\s*([A-Z])\.\s+([A-Za-z][A-Za-z\s]+?)\s*$'  # re.MULTILINE

# Annex headers
r'^\s*Annex\s+(\d+):\s+(.+?)\s*$'               # re.MULTILINE | re.IGNORECASE
```

**Validation requirement:** Before finalising patterns, run the filter against 5 real extracted texts (mix of countries and years) and confirm that ≥ 80% of expected section headers are matched. Adjust patterns if match rate is below threshold.

**Fallback behaviour:** If fewer than 5 section headers are detected across the full document (indicating pattern failure, not a short document), pass the full original text through unfiltered. Log a structured warning: `{"pid": "<PID>", "status": "filter_fallback", "headers_found": N, "reason": "below_threshold"}` — this enables tracking how often fallback fires across a portfolio run, so the pattern can be diagnosed and improved.

**Output:** Filtered texts saved to `extracted_texts_filtered/<PID>.txt` alongside the originals in `extracted_texts/`. A brief header is prepended to each filtered file noting which sections were retained:

```
[FILTERED: Retained sections I.A-C, II, III, IV, V, VI.E-F, Annex 1, 3, 7.
 Stripped: front matter, FM, procurement, economic analysis annexes, legal covenants.
 Original length: 118,432 chars → Filtered: 61,204 chars (48% reduction)]
```

**Document type handling:**
- PADs: full section filtering applied
- ICRs / ISRs / Restructuring Papers: different section structure — pass through unfiltered (these are already short; ISR extraction in Component 2 handles them separately)

---

### Component 2 — ISR/ICR Collection

**File:** Extend `data_collection.py` as a new Step 4.

**Purpose:** For each project in `screening_targets.json`, fetch any available ISRs and ICRs from the WB Documents API by project ID. Extract the key FCV-signal sections into compact summaries.

**API call:** `https://search.worldbank.org/api/v2/wds?format=json&projectid=<PID>&docty=ISR,ICR&fl=id,docdt,docty,url`

> **Note:** Confirm working parameter name before implementation. Existing data collection uses `project_id` (underscore) for some endpoints and `projectid` (no underscore) for others depending on WB API endpoint variant. Test the ISR fetch against a known project ID (e.g. P151492) and confirm non-empty results before integrating. Add confirmed parameter name to Open Questions resolution.

**ISR extraction method:** Use a **head+tail fixed-cap extraction** (consistent with existing PAD pipeline practice). Extract the first 10k characters + last 5k characters of each ISR PDF text, capped at 15k characters total. No separate LLM summarisation call — this avoids additional token cost and latency. ISRs are short enough (20–50 pages) that head+tail reliably captures the ratings tables (front) and key issues/findings (back).

**Signal content captured by head+tail:**
- Implementation Progress (IP) rating and Development Outcome (DO) rating
- Overall Risk Rating and any changes from previous ISR
- Key issues section (flagged problems, bottlenecks, risks)
- Any text referencing conflict, security, displacement, fragility, adaptive management, or grievance mechanisms
- Ratings trend table if present

**Output:** One file per ISR/ICR saved to `extracted_texts_isr/<PID>_<doctype>_<YYYY-MM>.txt`, ordered chronologically.

**If no ISRs exist** for a project: no files created; downstream screener receives PAD only (identical to current behaviour).

---

### Component 3 — Combined Screening Prompt

**Purpose:** Update the screener prompt to accept supplementary ISR/ICR summaries alongside the primary PAD text, and instruct Claude to adjust scores where ISR evidence warrants it.

**Prompt structure:**

```
PRIMARY DOCUMENT (PAD — use for all dimension baseline scores):
[filtered PAD text]

SUPPLEMENTARY DOCUMENTS ([N] ISRs/ICRs, chronological order):
[ISR 2020-06 summary]
[ISR 2022-03 summary]
...

INSTRUCTIONS:
1. Score all 8 dimensions using the PAD as primary evidence.
2. Review each supplementary document in chronological order.
3. For any dimension where ISR/ICR evidence materially changes the assessment
   (e.g., documented security deterioration with no adaptive response, or
   demonstrated course correction improving FCV sensitivity), adjust that
   dimension's score and record the reason.
4. Output the adjusted final score with a trajectory note.
```

**Updated output JSON schema (additions only):**

```json
{
  "isr_count": 3,
  "score_adjusted": true,
  "trajectory": "2–3 sentence narrative of what ISRs revealed about implementation-phase FCV sensitivity",
  "dimensions": [
    {
      "id": 6,
      "name": "Implementation & Adaptive Management",
      "numeric_score": 3.0,
      "pad_score": 5.0,
      "adjustment_reason": "ISR 2021-09 flagged security deterioration in Tigray with no documented adaptive management response"
    }
  ]
}
```

**Backward compatibility:** All existing fields remain unchanged. New fields (`isr_count`, `score_adjusted`, `trajectory`, `pad_score`, `adjustment_reason`) are additive. The normalization script handles missing fields gracefully with these explicit defaults:
- `isr_count`: `0`
- `score_adjusted`: `false`
- `trajectory`: `null`
- `pad_score` (per-dimension): `null` — explicitly `null`, NOT copied from `numeric_score`. A `null` value means no ISR adjustment was made for that dimension; it does not mean the pad score equals the final score. This prevents a normalization bug where all dimensions appear adjusted.

**If no ISRs exist:** Prompt structure is identical to current (PAD only); new fields default as above.

---

## Token Budget

| | Current | After enhancement |
|---|---|---|
| PAD tokens/project | ~17.5k input | ~9k input |
| ISR tokens/project | 0 | ~8k input (avg 3 ISRs × ~3k) |
| Output tokens/project | ~8k | ~9k (trajectory note adds ~1k) |
| **Total per project** | **~25.5k** | **~26k** |
| **Total for Ethiopia (56)** | **~1.43M** | **~1.46M** |

Net token cost is essentially unchanged. PAD section filtering savings fully offset the ISR additions.

**Key benefit:** For countries where ISRs are unavailable (e.g., newer portfolios), the section filter alone delivers a ~40% token reduction with no other changes.

---

## File Structure Changes

```
FCV-Portfolio-Screener/
├── utils/
│   └── pad_section_filter.py          # NEW — Component 1
├── <country>/
│   ├── extracted_texts/               # UNCHANGED — original PDFs
│   ├── extracted_texts_filtered/      # NEW — filtered PAD texts
│   ├── extracted_texts_isr/           # NEW — ISR/ICR summaries
│   └── <date>_<country>_data_collection.py  # UPDATED — adds Step 4 (ISR fetch)
└── docs/superpowers/specs/
    └── 2026-03-24-portfolio-screener-enhancement-design.md  # THIS FILE
```

---

## Implementation Order

1. Build and test `pad_section_filter.py` on a sample of 5–10 documents across all three countries; validate section detection accuracy (≥ 80% header match rate)
2. Extend `data_collection.py` with ISR fetch step; confirm API parameter name against known project ID
3. Update screener prompt with combined PAD + ISR instructions
4. Update `normalize_results.py` to handle new schema fields (must happen before testing, not after)
5. Run end-to-end test on Djibouti (smallest portfolio, 22 projects) before Ethiopia

---

## Open Questions

- WB Documents API ISR availability: needs testing to confirm ISRs are consistently accessible by project ID (SSL certificate handling already in place via `ssl.CERT_NONE`).
- ISR text quality: ISRs may have less structured formatting than PADs — the light extraction approach (keyword search rather than section parsing) may be more reliable than regex-based section detection.
