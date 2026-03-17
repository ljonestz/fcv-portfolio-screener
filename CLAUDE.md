# CLAUDE.md — FCV Portfolio Screener
## Replication Guide for Country Portfolio Analysis

This repo contains the workflow for running **World Bank FCV Sensitivity and Responsiveness portfolio analyses** at the country level.

Each country's analysis lives in its own subfolder: `<country>/`

Current countries:
- `somalia/` — completed 2026-03-14 (40 projects, 2015–2024); report redesigned 2026-03-16
- `djibouti/` — completed 2026-03-16 (22 projects, 2015–2024)
- `ethiopia/` — scripts created 2026-03-16; data collection and screening pending

---

## What This Analysis Does

This workflow takes a World Bank country portfolio, identifies the most policy-relevant project document for each operation, extracts text from the PDF, and applies the **FCV Sensitivity and Responsiveness Screener** skill to every document. It then generates 8 analytical charts and assembles a full HTML report.

The result is a portfolio-level FCV assessment covering:
- How well the portfolio understands FCV context (Sensitivity)
- How well the portfolio adapts operationally to that context (Responsiveness)
- 8 sub-dimensions scored 1–10
- 5 red flags (e.g. elite capture, do-no-harm gaps)
- A 2×2 Gap Matrix classification for every project

---

## Prerequisites

### Python packages
```
pip install requests PyMuPDF pandas matplotlib seaborn numpy
```
- **PyMuPDF (`fitz`)** — use this for PDF extraction, NOT `pdfplumber` (fails on WB PDFs)
- Version tested: PyMuPDF 1.27.2

### Claude Code skills
The FCV skill is installed globally at:
```
C:\Users\wb559324\.claude\fcv-sensitivity-and-responsiveness-screener.skill
```
Install via Claude Code: `/skills install <path_to_skill>`

### Network
- All WB API calls require `ssl_verify=False` (corporate proxy SSL intercept)
- Use `urllib` with a custom SSL context — `httpx` does not work directly in this environment

---

## Step-by-Step Workflow

### Step 1 — Fetch the portfolio from the WB Projects API

**API endpoint:**
```
https://search.worldbank.org/api/v2/projects?format=json&countrycode=SO&rows=100&source=IBRD&fl=id,project_name,status,boardapprovaldate,closingdate,lendinginstr,lendinginstrtype,sector1,sector2,theme1,totalcommamt,url,regionname,countryname
```

Change `countrycode=SO` to the target country ISO2 code (e.g. `KE` for Kenya, `YE` for Yemen).

**What to do:**
1. Fetch all projects — paginate if needed (`os` and `start` params)
2. Save raw output as `raw_all_<country>_projects.json` (not committed — archive locally)
3. Filter to keep only projects with `boardapprovaldate` in your target window (we used 2015–2024)
4. Exclude grants, guarantee instruments if desired — we kept IPF and DPF
5. Save filtered list as `filtered_<country>_portfolio.json`

**Result for Somalia:** 43 projects, approval years 2015–2024.

---

### Step 2 — Fetch project documents from the WB Documents API

**API endpoint per project:**
```
https://search.worldbank.org/api/v2/wds?format=json&project_id=<PID>&rows=10&fl=id,docty,docdt,display_title,pdfurl,lang,seccl,disclstat,abstracts,url
```

**Document type priority (in order of preference):**
1. `Project Appraisal Document` (PAD) — for IPF projects — best source
2. `Program Document` (PD) — for DPF projects — best source
3. `Implementation Completion Report` (ICR) — for closed projects when PAD unavailable
4. `Project Paper` — for restructuring/additional financing operations
5. `Concept Note` — lowest priority, use only if nothing else available

**Logic:**
- For each project, retrieve available documents and select the highest-priority type that has a `pdfurl`
- If no `pdfurl` is available for any document type, exclude the project (we excluded 3: P152379, P173637, P178887)
- Save the selection as `screening_targets.json`

**Result for Somalia:** 40 projects with valid PDF URLs.

---

### Step 3 — Extract text from PDFs

**Head+tail approach (recommended for large portfolios, e.g. Ethiopia):**

```python
def extract_pdf_text(url: str, head_chars: int = 50_000, tail_chars: int = 20_000) -> str:
    """Extract first head_chars + last tail_chars from a WB PDF.

    Head captures: cover, SORT risk table, country context, PDO, theory of change.
    Tail captures: results framework, risk annexes, safeguards.
    Short docs (<= head+tail chars) returned in full.
    """
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=90) as r:
        pdf_bytes = r.read()
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    max_needed = head_chars + tail_chars
    text = ''
    for page in doc:
        text += page.get_text()
        if len(text) >= max_needed:
            break
    doc.close()
    if len(text) <= head_chars:
        return text
    head = text[:head_chars]
    tail = text[max(head_chars, len(text) - tail_chars):]
    sep = '\n\n[... procurement/fiduciary sections omitted ...]\n\n'
    return head + sep + tail
```

**Flat 120k approach (used for Somalia/Djibouti):** Cap at 120,000 characters — covers ~80–100 pages.

**Key decisions:**
- Prefer head+tail for portfolios >40 projects — saves ~42% of tokens per project vs flat 120k
- Save each extracted text as a `.txt` file in `extracted_texts/<PID>.txt` (not committed — archive locally)
- Use `fitz`, not `pdfplumber` — WB PDFs have complex layouts that break pdfplumber

---

### Step 4 — FCV Screening (the main analytical step)

**Recommended approach: 1 project per background agent** (introduced for Ethiopia; supersedes batch-of-8)

Each agent receives only: skill instructions (~5k tokens) + one project's extracted text (~17.5k tokens) = ~23k tokens per agent. Compare to batch-of-8 which accumulates ~267k tokens by project 8.

**Agent prompt template (per project):**
```
Screen this single project using the FCV screener skill.
Project ID: <PID> | Name: <project_name>
Document type: <doc_type> | Instrument: <instrument_category> | Year: <approval_year>

Output format constraints (strictly enforced):
- key_quote: max 250 chars per dimension
- rationale per dimension: max 3 sentences / 200 words
- key_finding: max 2 sentences / 100 words
- Output: a single JSON object only. No preamble before the JSON.

Save result to: <country>/screening_results_<PID>.json

[extracted text below]
<text>
```

**Session management for large portfolios (>40 projects):**

Launch agents in groups across multiple sessions to avoid main-session context accumulation. Never read or paste extracted text into the main session.

| Session | Action |
|---|---|
| A | Steps 1–3: Run data collection script |
| B | Launch screening agents for projects 1–20 (all as background) |
| C | Launch screening agents for projects 21–40 |
| D | Launch screening agents for projects 41–60 |
| E+ | Remaining projects; then check all results saved |

After launching each group, you can `/clear` or close the session — the background agents run independently and save their results as files.

**Legacy batch-of-8 approach (Somalia/Djibouti):** Divide projects into batches of ~8, launch one agent per batch, pass a JSON array of projects+texts. Still valid for small portfolios (<25 projects) to reduce session overhead.

**Output per project (target schema):**
```json
{
  "project_id": "P151492",
  "project_name": "...",
  "doc_type": "Project Appraisal Document",
  "instrument_category": "IPF",
  "approval_year": 2015,
  "composites": {
    "sensitivity": {"numeric_score": 6.17, "rating": "Substantially Addressed", "rationale": "..."},
    "responsiveness": {"numeric_score": 4.80, "rating": "Partially Addressed", "rationale": "..."}
  },
  "dimensions": [...8 dimensions...],
  "red_flags": {"RF1": false, "RF2": false, "RF3": false, "RF4": true, "RF5": false},
  "gap_matrix_cell": "Responsive but underanalysed",
  "key_finding": "..."
}
```

**Important:** Different agents may produce slightly different JSON schemas. Run `normalize_results.py` after all results are saved.

---

### Step 5 — Normalize and merge results

Run `normalize_results.py` — this script:
1. **1-per-agent approach:** globs `screening_results_P*.json` files (one per project)
2. **Batch approach:** merges all `screening_results_batch_N.json` files
3. Normalises scores, ratings, and dimension lists into one canonical schema
4. Saves `<date>_<country>_screening_results_normalized.json`

---

### Step 6 — Generate charts

Run `<date>_<country>_fcv_analysis.py`

Outputs (8 PNG charts, 150 dpi):
| File | Description |
|---|---|
| `chart1_portfolio_timeline.png` | Stacked bar: projects approved per year by instrument |
| `chart2_sensitivity_over_time.png` | Line chart: average sensitivity score by year |
| `chart3_responsiveness_over_time.png` | Line chart: average responsiveness score by year |
| `chart4_sensitivity_vs_responsiveness.png` | Scatter/quadrant plot |
| `chart5_dimension_heatmap.png` | Heatmap: all 8 dimensions × all projects |
| `chart6_red_flags.png` | Bar chart: red flag frequency across portfolio |
| `chart7_dimension_radar.png` | Radar: average score per dimension (IPF vs DPF) |
| `chart8_score_distribution.png` | Box plots: score distribution by instrument type |

---

### Step 7 — Generate HTML report

Run `generate_report.py` from inside the country subfolder:

```bash
cd somalia
python generate_report.py
```

Output: `<date>_<country>-fcv-portfolio-report.html` — ~500 KB self-contained HTML, written to the same directory as the script.

Open directly in any browser — no server needed. Keep HTML and PNGs in the same folder.

**Report design (2026-03-16 revision):** The report uses a blog-style narrative layout — no styled callout boxes, one consistent paragraph font throughout, chart narratives frontloaded above each chart with the key finding stated first, and an expandable project table (click any row) replacing the separate portfolio table and Annex collapsibles. `generate_report.py` uses `Path(__file__).parent` for all file I/O so it works correctly from any location without hardcoded paths.

---

## FCV Scoring Framework

### Dimensions and composites

| # | Dimension | Composite |
|---|---|---|
| D1 | FCV Context and Diagnostics | Sensitivity |
| D2 | Do No Harm and Conflict Risk | Sensitivity |
| D3 | Stakeholder and Political Economy | Sensitivity |
| D4 | Objectives and Theory of Change | Responsiveness |
| D5 | Design and Targeting | Responsiveness |
| D6 | Implementation and Operational Flexibility | Responsiveness |
| D7 | Results Framework and Adaptive Management | Responsiveness |
| D8 | One WBG Integration (IFC/MIGA) | Responsiveness |

**Sensitivity score** = average of D1, D2, D3
**Responsiveness score** = average of D4, D5, D6, D7, D8

Each dimension scored 1–10. Red flags apply a deduction to the relevant composite.

### Rating thresholds

| Score | Rating |
|---|---|
| 7–10 | Substantially Addressed |
| 4–6.9 | Partially Addressed |
| 1–3.9 | Not Addressed |

### Red flags (RF)

| Flag | Description |
|---|---|
| RF1 | Do-no-harm violation — design could exacerbate conflict |
| RF2 | Elite capture — benefits systematically diverted |
| RF3 | Exclusion — marginalised groups structurally excluded |
| RF4 | Harm pathway named but not mitigated in design |
| RF5 | Results framework has no FCV-adjusted indicators |

### Gap Matrix (2×2)

|  | Low Responsiveness | High Responsiveness |
|---|---|---|
| **High Sensitivity** | Implementation gap | High FCV integration |
| **Low Sensitivity** | Low FCV integration | Responsive but underanalysed |

Threshold: Sensitivity ≥ 6.0 = "High", Responsiveness ≥ 5.5 = "High"

---

## Report Narrative Guidelines

### FCS classification — verify before labelling
Do **not** assume a country is on the WBG's Harmonized List of Fragile and Conflict-Affected Situations (FCS List). Before generating any report narrative, verify the country's current status against the latest FCS list published at:
- https://www.worldbank.org/en/topic/fragilityconflictviolence/brief/harmonized-list-of-fragile-situations

If the country **is** on the current FCS list, it can be referred to as an FCS country. If it is **not** on the list (e.g. Djibouti as of FY25), describe it as "affected by drivers of fragility, conflict, and violence" or "FCV-affected" — do not call it an FCS or FCAS country. This distinction matters for institutional credibility.

### Sensitivity–responsiveness gap — do not overplay small differences
The gap between portfolio-average sensitivity and responsiveness scores is a useful analytical signal, but on a 1–10 scale with inherent measurement uncertainty, differences of less than ~1 point should not be overstated. Specifically:
- Do **not** call a sub-1-point gap "the central finding" of an assessment
- Do **not** describe it as "widening" or "closing" unless the trend data clearly supports that claim across cohorts
- **Do** note the direction of the gap (sensitivity > responsiveness is the typical pattern) and contextualise it as consistent with broader FCV portfolio patterns
- **Do** focus narrative weight on the **trend** (are the composites converging or diverging over time?) rather than the **level** of the gap at a single point in time
- Where the gap is modest (<1 point), acknowledge measurement uncertainty explicitly

---

## Adapting for Another Country

1. **Create a new subfolder:** `Documents\GitHub\fcv-portfolio-screener\<country>\`

2. **Change the country code** in the WB API call (Step 1)
   - Find ISO2 codes at: https://datahelpdesk.worldbank.org/knowledgebase/articles/906519

3. **Adjust the date filter** if needed (we used 2015–2024 for Somalia)

4. **Update all file path variables** in the Python scripts — search for `somalia` and replace with your country slug

5. **Run steps 1–3** (data collection + extraction) before launching screening agents

6. **Batch size:** 8 projects per agent worked well. For smaller portfolios (<20 projects), use 2–3 batches. For larger portfolios (>60), consider 8 batches of 8.

7. **Rate limits:** If Claude Code hits API rate limits during screening, wait for reset (resets at midnight Europe/Paris) and relaunch only the failed batches.

8. **What to commit:** Scripts, normalized results, charts, HTML report. Gitignore raw API dumps, batch intermediates, `extracted_texts/`.

---

## What's Not in This Repo (Archive Locally)

These files are gitignored but kept locally in `Claude_Outputs/20260314_somalia-fcv-portfolio-analysis/`:
- `raw_all_somalia_projects.json` — raw WB API output
- `project_documents.json` / `project_documents_v2.json` — document metadata
- `batch_*_targets.json` — batch subdivision files
- `screening_results_batch_*.json` — raw batch screening outputs
- `20260314_somalia_screening_results.json` — merged pre-normalisation file
- `extracted_texts/` — full text extracted from each PDF
- `extraction_results.json` — extraction status log

These are backed up via OneDrive sync.

---

## Known Issues and Workarounds

| Issue | Workaround |
|---|---|
| SSL certificate errors on WB API | Use `urllib` with `ssl.CERT_NONE` context |
| `pdfplumber` fails on WB PDFs | Use `fitz` (PyMuPDF) instead |
| Agents produce inconsistent JSON schemas | Always run `normalize_results.py` before analysis |
| Some projects have no PDF URL | Exclude them and note in report methodology |
| `matplotlib` boxplot deprecation warning (`labels` → `tick_labels`) | Cosmetic only, does not affect output |
| Agent hits rate limit mid-batch | Results for completed projects still saved; relaunch remaining only |
| `totalcommamt` stored as string in portfolio JSON | Cast to `float()` before arithmetic |
| Old `generate_report.py` wrote to hardcoded `Claude_Outputs` path | Fixed 2026-03-16: now uses `Path(__file__).parent` — script writes to its own directory |
| WB Documents API returns >200 PADs for large countries (e.g. Ethiopia) | Script paginates up to 800 docs per document type |
| Head+tail separator causes minor discontinuity in extracted text | Separator `[... procurement/fiduciary sections omitted ...]` is visible to screener — agents handle it correctly |

---

## Git Workflow

All changes to this repo should follow the branch-first convention:

```bash
git checkout -b <type>/<short-description>   # e.g. feat/kenya-analysis
# make changes, then:
git add <files>
git commit -m "<type>: <description>"
git push -u origin <branch>
# merge to main when ready
```

Never commit directly to `main` for non-trivial changes.

---

*Last updated: 2026-03-16 — Ethiopia scripts added; 1-per-agent screening approach documented; head+tail extraction documented*
