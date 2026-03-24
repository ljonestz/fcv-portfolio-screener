# PAD Section Filter & ISR Enhancement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce per-project token usage ~40–50% by stripping FCV-irrelevant boilerplate from PAD text, and enrich FCV screening with ISR/ICR evidence that can adjust dimension scores based on implementation-phase findings.

**Architecture:** Three new utilities in a shared `utils/` package: (1) `pad_section_filter.py` strips boilerplate before screening, (2) `fetch_isrs.py` collects ISR/ICR documents from the WB API per project, (3) `build_screening_prompt.py` assembles the combined PAD + ISR prompt. `normalize_results.py` is updated to handle four new optional fields. All utilities are importable modules that also run standalone from the command line.

**Tech Stack:** Python 3, `re`, `pathlib`, `urllib`, `ssl`, `fitz` (PyMuPDF), `json`. No new dependencies.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `utils/__init__.py` | Create | Makes utils a Python package |
| `utils/pad_section_filter.py` | Create | Strip boilerplate from PAD text; write filtered files |
| `utils/fetch_isrs.py` | Create | Fetch ISR/ICR PDFs from WB API; head+tail extract; save per-project |
| `utils/build_screening_prompt.py` | Create | Assemble PAD + ISR prompt string for screener agents |
| `tests/__init__.py` | Create | Test package marker |
| `tests/fixtures/sample_pad.txt` | Create | Synthetic PAD with standard WBG section structure (for tests) |
| `tests/fixtures/sample_isr.txt` | Create | Synthetic ISR text (for tests) |
| `tests/test_pad_section_filter.py` | Create | Unit tests for section filter |
| `tests/test_fetch_isrs.py` | Create | Unit tests for ISR fetcher (mock API) |
| `tests/test_build_screening_prompt.py` | Create | Unit tests for prompt builder |
| `ethiopia/normalize_results.py` | Modify | Add backward-compat handling for 4 new fields |
| `djibouti/normalize_results.py` | Modify | Same update (Djibouti used for end-to-end test) |

**Directories created during run (not committed — gitignored):**
- `<country>/extracted_texts_filtered/` — filtered PAD texts
- `<country>/extracted_texts_isr/` — ISR/ICR head+tail extracts

---

## Task 1: Test fixtures and project scaffolding

**Files:**
- Create: `utils/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/fixtures/sample_pad.txt`
- Create: `tests/fixtures/sample_isr.txt`

- [ ] **Step 1: Create the `utils/` package and `tests/` directory**

```bash
cd "/c/Users/wb559324/OneDrive - WBG/Documents/GitHub/FCV-Portfolio-Screener"
mkdir -p utils tests/fixtures
touch utils/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `tests/fixtures/sample_pad.txt`**

This synthetic PAD must contain all the key section header patterns seen in real WBG PADs so tests have a reliable fixture. Create the file with this content:

```
DOCUMENT TITLE
World Bank Project Appraisal Document
Country: Test Country
Project ID: P999999

CURRENCY EQUIVALENTS
(Exchange Rate Effective January 1, 2020)
1 USD = 100 TCU

FISCAL YEAR
January 1 – December 31

ABBREVIATIONS AND ACRONYMS
FCV   Fragility, Conflict and Violence
GRM   Grievance Redress Mechanism
IPF   Investment Project Financing
M&E   Monitoring and Evaluation
PAD   Project Appraisal Document
PDO   Project Development Objective
PIU   Project Implementation Unit
RRA   Regional Risk Assessment
SORT  Systematic Operations Risk-Rating Tool
WBG   World Bank Group

REGIONAL VICE PRESIDENT: Test VP Name
COUNTRY DIRECTOR: Test Director Name
PRACTICE MANAGER: Test Manager Name
TASK TEAM LEADER: Test TTL Name

I. STRATEGIC CONTEXT

A. Country Context

Test Country has experienced significant conflict dynamics over the past decade.
The Regional Risk Assessment (RRA) identifies three primary fragility drivers:
displacement of pastoral communities, institutional legitimacy deficits in border regions,
and recurring drought-induced economic shocks. The World Bank FCV list classifies
Test Country as an Orange-tier fragile state.

B. Sectoral and Institutional Context

The education sector faces systemic challenges including displacement of teachers,
school destruction in conflict-affected zones, and weak community trust in government
institutions. Enrollment gaps are highest in the northern districts of Testville and
Sampleburg, where state presence has historically been contested.

C. Higher Level Objectives

The project aligns with the Country Partnership Framework (CPF 2020-2025) which
identifies FCV sensitivity as a cross-cutting theme. The CPF notes that operational
adaptation is required in conflict-prone regions.

II. PROJECT DEVELOPMENT OBJECTIVES

A. PDO

The Project Development Objective is to improve access to quality basic education
for children in conflict-affected and fragility-vulnerable communities in Test Country,
with particular attention to displaced populations and girls.

B. Project Beneficiaries

Primary beneficiaries: 250,000 school-age children in targeted districts.
The targeting criteria explicitly prioritize conflict-affected communities, including
internally displaced persons (IDPs) and returnees.

C. PDO Level Results Indicators

1. Number of children enrolled in primary education (disaggregated by gender, displacement status)
2. Percentage of schools in targeted districts with functional GRM
3. Number of teachers trained in conflict-sensitive pedagogy

III. PROJECT DESCRIPTION

A. Project Components

Component 1: Conflict-sensitive school rehabilitation (USD 30M)
Activities include rehabilitation of conflict-damaged schools in Testville and
Sampleburg districts, using community-based contracting to rebuild social cohesion.

Component 2: Teacher deployment and training (USD 15M)
Conflict-sensitive teacher training curriculum developed with UNHCR partnership.

Component 3: Community engagement and GRM (USD 5M)
Establishment of community feedback forums in all targeted districts.

B. Project Financing

[Financing table - standard content]

C. Lessons Learned

Previous education projects in conflict contexts demonstrated that community ownership
of school infrastructure reduces conflict risk and improves sustainability.

IV. IMPLEMENTATION

A. Institutional and Implementation Arrangements

The Project Implementation Unit (PIU) will be housed in the Ministry of Education
with dedicated FCV specialist capacity. Adaptive management protocols allow for
quarterly implementation adjustments based on conflict monitoring data.

B. Results Monitoring and Evaluation

The M&E framework includes conflict-sensitive indicators and do-no-harm monitoring.
Monthly conflict incident tracking integrated with implementation dashboards.

C. Sustainability

Community-based maintenance agreements reduce dependence on government systems
in areas of low institutional legitimacy.

V. KEY RISKS

A. Overall Risk and Explanation

SYSTEMATIC OPERATIONS RISK-RATING TOOL (SORT)

Risk Category              Rating
Political and Governance   High
Macroeconomic              Moderate
Sector Strategies          Moderate
Technical Design           Low
Institutional Capacity     High
Fiduciary                  Low
Environment and Social     Moderate
Stakeholders               High
Other (Security)           High
Overall                    High

The High overall risk rating reflects the volatile security situation in northern
districts. Conflict escalation could disrupt implementation and displace beneficiaries.

VI. APPRAISAL SUMMARY

A. Economic and Financial Analysis

The economic rate of return is estimated at 12.4% over 20 years, based on
increased lifetime earnings from improved education outcomes. Sensitivity analysis
shows returns remain positive under moderate conflict disruption scenarios.

B. Technical

The technical design follows evidence-based approaches from comparable conflict-
affected contexts including South Sudan and DRC education programs.

C. Financial Management

Financial management arrangements comply with OP/BP 10.02. The PIU will maintain
separate project accounts subject to annual audits by acceptable firms. Interim
financial reports will be submitted quarterly.

D. Procurement

Procurement will follow the World Bank Procurement Regulations for IPF Borrowers
(July 2016, revised 2020). Community contracting is permitted for Component 1
activities under the Procurement Regulations framework.

E. Social (including Safeguards)

The project triggers OP/BP 4.12 (Involuntary Resettlement) due to potential
temporary displacement during school construction. A Resettlement Policy Framework
(RPF) has been prepared. The Stakeholder Engagement Plan includes targeted
consultation with IDP communities in Testville and Sampleburg.
A Grievance Redress Mechanism has been designed specifically for conflict-affected
communities, with community liaison officers in each targeted district.

F. Environment (including Safeguards)

The Environmental and Social Commitment Plan (ESCP) includes specific commitments
for conflict-sensitive environmental management. Construction activities will avoid
sites with contested land ownership.

G. World Bank Grievance Redress

Communities and individuals who believe they are adversely affected by World Bank
supported projects may submit complaints to existing project-level GRM or the WB's
Grievance Redress Service (GRS).

Annex 1: Results Framework and Monitoring

PDO Indicators:
- Indicator 1: Children enrolled (target: 250,000; disaggregated by gender, IDP status)
- Indicator 2: Schools with functional GRM (target: 85%)
- Indicator 3: Teachers trained in conflict-sensitive pedagogy (target: 5,000)

Do-No-Harm Indicators:
- Indicator 4: Community conflict incidents linked to project activities (target: 0)
- Indicator 5: Grievances resolved within 30 days (target: 90%)

Annex 2: Detailed Project Description

[Extended component descriptions - standard boilerplate]
This annex provides additional technical detail on Component 1, 2, and 3 activities.

Annex 3: Implementation Arrangements

Institutional Roles:
- Ministry of Education: Overall project oversight and fiduciary management
- PIU FCV Specialist: Conflict monitoring, adaptive management, GRM coordination
- UNHCR: Technical support for teacher training on conflict-sensitive pedagogy
- Community Liaison Officers: Quarterly community feedback collection

Annex 4: Implementation Support Plan

World Bank implementation support missions planned biannually.
Budget: USD 250,000 for supervision over 5 years.

Annex 5: Economic Analysis

Detailed NPV calculations, discount rates, and sensitivity tables.
[Standard economic analysis boilerplate - not FCV relevant]

Annex 6: Financial Analysis

Detailed project financial statements and flow of funds.
[Standard financial analysis boilerplate - not FCV relevant]

Annex 7: Social (including Safeguards)

Stakeholder Engagement Plan (SEP):
The SEP identifies three key stakeholder groups requiring conflict-sensitive engagement:
1. IDP communities in Testville (estimated 45,000 persons)
2. Host communities with competing land claims
3. Pastoralist groups seasonally present in Sampleburg district

The GRM design specifically addresses power imbalances and provides anonymous
reporting channels given the conflict context.

BORROWER COMMENTS
The Government of Test Country acknowledges the findings of this assessment.

SUPPORTING DOCUMENTS
1. Regional Risk Assessment, Test Country, 2019
2. Education Sector Assessment, 2020
3. Stakeholder Engagement Plan
```

- [ ] **Step 3: Write `tests/fixtures/sample_isr.txt`**

```
IMPLEMENTATION STATUS AND RESULTS REPORT
Test Country Education Project
Project ID: P999999
Report Date: March 2023 (ISR #4)

IMPLEMENTATION STATUS

Development Objective Rating: Moderately Satisfactory
Implementation Progress Rating: Moderately Unsatisfactory

KEY ISSUES AND CHALLENGES

1. Security deterioration in northern Testville district since October 2022 has
   halted construction of 12 schools. The project has not yet documented an
   adaptive management response to the changed security context.

2. The GRM has received 47 complaints in Q4 2022, of which 31 relate to
   contractor hiring practices perceived as exclusionary by IDP communities.
   Resolution rate is 62%, below the 90% target.

3. Conflict-sensitive M&E indicators are not being reported in the current
   implementation period. The PIU has not submitted conflict monitoring data
   since June 2022.

RISK RATINGS

Overall Risk Rating: High (unchanged)
Political and Governance: High (deteriorated from Substantial)
Security: High (new flag added)
Stakeholders: High (unchanged)

ACTIONS REQUIRED

By next mission (June 2023):
- Document adaptive management response to security deterioration in Testville
- Resume conflict monitoring data collection and reporting
- Increase GRM resolution rate to target level
```

- [ ] **Step 4: Commit scaffolding**

```bash
cd "/c/Users/wb559324/OneDrive - WBG/Documents/GitHub/FCV-Portfolio-Screener"
git add utils/__init__.py tests/__init__.py tests/fixtures/
git commit -m "chore: add utils package, test scaffolding, and PAD/ISR fixtures"
```

---

## Task 2: PAD section filter — failing tests

**Files:**
- Create: `tests/test_pad_section_filter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_pad_section_filter.py`:

```python
"""Tests for PAD section filter utility."""
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pad_section_filter import filter_pad, detect_sections

FIXTURES = Path(__file__).parent / 'fixtures'


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding='utf-8')


# ─── detect_sections ───────────────────────────────────────────────────────────

def test_detects_roman_numeral_sections():
    text = load_fixture('sample_pad.txt')
    sections = detect_sections(text)
    names = [s['name'].upper() for s in sections]
    assert any('STRATEGIC CONTEXT' in n for n in names), f"Expected 'STRATEGIC CONTEXT' in {names}"
    assert any('KEY RISKS' in n for n in names), f"Expected 'KEY RISKS' in {names}"


def test_detects_annex_headers():
    text = load_fixture('sample_pad.txt')
    sections = detect_sections(text)
    annex_sections = [s for s in sections if s['type'] == 'annex']
    assert len(annex_sections) >= 3, f"Expected ≥3 annexes, found {len(annex_sections)}"


def test_detects_minimum_five_headers():
    text = load_fixture('sample_pad.txt')
    sections = detect_sections(text)
    assert len(sections) >= 5, f"Expected ≥5 headers, found {len(sections)}"


def test_returns_empty_for_no_headers():
    sections = detect_sections("This is just a paragraph with no headers.")
    assert sections == []


# ─── filter_pad ────────────────────────────────────────────────────────────────

def test_retains_strategic_context():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'Regional Risk Assessment' in filtered  # content from Section I.A
    assert stats['status'] == 'filtered'


def test_retains_key_risks_sort():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'SORT' in filtered or 'KEY RISKS' in filtered.upper()


def test_strips_financial_management():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'OP/BP 10.02' not in filtered  # content only in VI.C Financial Management


def test_strips_procurement():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'Procurement Regulations for IPF Borrowers' not in filtered  # only in VI.D


def test_retains_social_safeguards():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'Grievance Redress Mechanism' in filtered  # VI.E content


def test_retains_annex_1_results():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'Do-No-Harm Indicators' in filtered  # Annex 1 content


def test_retains_annex_3_implementation():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'FCV Specialist' in filtered  # Annex 3 content


def test_strips_annex_5_economic():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'NPV calculations' not in filtered  # Annex 5 content only


def test_retains_annex_7_social():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'Stakeholder Engagement Plan' in filtered  # Annex 7 content


def test_strips_borrower_comments():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'BORROWER COMMENTS' not in filtered


def test_filtered_shorter_than_original():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert len(filtered) < len(text)
    assert stats['reduction_pct'] > 0


def test_filter_header_prepended():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert filtered.startswith('[FILTERED:')


def test_stats_contains_required_keys():
    text = load_fixture('sample_pad.txt')
    _, stats = filter_pad(text)
    for key in ('headers_found', 'original_chars', 'filtered_chars', 'reduction_pct', 'status'):
        assert key in stats, f"Missing stats key: {key}"


# ─── fallback behaviour ────────────────────────────────────────────────────────

def test_fallback_when_no_headers():
    text = "No section headers here. Just plain text without any structure."
    filtered, stats = filter_pad(text)
    assert filtered == text  # returned unmodified
    assert stats['status'] == 'fallback'
    assert stats['headers_found'] < 5


def test_fallback_preserves_full_text():
    text = "Short unstructured document.\n\nSome more text."
    filtered, stats = filter_pad(text)
    assert filtered == text


# ─── non-PAD pass-through ──────────────────────────────────────────────────────

def test_isr_passes_through_unfiltered():
    text = load_fixture('sample_isr.txt')
    filtered, stats = filter_pad(text, doc_type='ISR')
    assert filtered == text
    assert stats['status'] == 'passthrough'


def test_icr_passes_through_unfiltered():
    text = load_fixture('sample_isr.txt')
    filtered, stats = filter_pad(text, doc_type='ICR')
    assert filtered == text
    assert stats['status'] == 'passthrough'
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd "/c/Users/wb559324/OneDrive - WBG/Documents/GitHub/FCV-Portfolio-Screener"
python -m pytest tests/test_pad_section_filter.py -v 2>&1 | head -40
```

Expected: `ModuleNotFoundError: No module named 'utils.pad_section_filter'` — confirms tests are wired up and the module is absent.

---

## Task 3: PAD section filter — implementation

**Files:**
- Create: `utils/pad_section_filter.py`

- [ ] **Step 1: Implement `utils/pad_section_filter.py`**

```python
"""
PAD Section Filter — strips FCV-irrelevant boilerplate from WBG PAD extracted text.

Sections retained: I (Strategic Context), II (PDO), III (Project Description),
IV (Implementation), V (Key Risks), VI.E (Social Safeguards), VI.F (Environment),
VI.G (GRM), Annex 1 (Results), Annex 3 (Implementation Arrangements),
Annex 7 (Social Safeguards).

Sections stripped: front matter (abbreviations, currency, team roster),
VI.A-B (Economic/Financial Analysis), VI.C (Financial Management),
VI.D (Procurement), Annexes 4-6 (Economic, Financial, Bank Lending),
Borrower comments, Supporting Documents.

Usage (module):
    from utils.pad_section_filter import filter_pad, run_filter_on_directory

Usage (CLI):
    python utils/pad_section_filter.py <country_dir>
    python utils/pad_section_filter.py ethiopia  --validate --sample 5
"""

import re
import json
import sys
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Section header patterns ───────────────────────────────────────────────────
# Applied in order: more specific patterns first.
# All use re.MULTILINE. Trailing whitespace stripped from captured names.

_PAT_ROMAN = re.compile(
    r'^\s*([IVX]{1,5})\.\s+([A-Z][A-Za-z ,&/()\-]+?)\s*$',
    re.MULTILINE
)
_PAT_LETTER = re.compile(
    r'^\s*([A-Z])\.\s+([A-Z][A-Za-z ,&/()\-]+?)\s*$',
    re.MULTILINE
)
_PAT_ANNEX = re.compile(
    r'^\s*Annex\s+(\d+):\s+([A-Za-z ,&/()\-]+?)\s*$',
    re.MULTILINE | re.IGNORECASE
)

# ─── Keep / strip rules ────────────────────────────────────────────────────────

# Roman numeral sections: keep all of I–V; VI is handled by subsection rules
_KEEP_ROMAN = {'I', 'II', 'III', 'IV', 'V'}

# VI subsections: keep E (Social), F (Environment), G (GRM)
_KEEP_VI_SUBS = {'E', 'F', 'G'}

# Annexes: keep 1 (Results), 3 (Implementation Arrangements), 7 (Social)
_KEEP_ANNEXES = {'1', '3', '7'}

# Non-PAD document types that pass through unfiltered
_PASSTHROUGH_TYPES = {'ISR', 'ICR', 'RESTRUCTURING', 'AF', 'PID', 'PCN'}

# Minimum section headers required to attempt filtering (else fallback)
_MIN_HEADERS = 5


# ─── Public API ───────────────────────────────────────────────────────────────

def detect_sections(text: str) -> list[dict]:
    """
    Find all section headers in text.

    Returns a list of dicts, each with keys:
        type: 'roman' | 'letter' | 'annex'
        key: normalised key string (e.g. 'V', 'E', '1')
        name: section title text
        start: character offset of header line start
        end: character offset of header line end
    """
    hits = []

    for m in _PAT_ROMAN.finditer(text):
        hits.append({
            'type': 'roman',
            'key': m.group(1).upper(),
            'name': m.group(2).strip(),
            'start': m.start(),
            'end': m.end(),
        })

    for m in _PAT_LETTER.finditer(text):
        hits.append({
            'type': 'letter',
            'key': m.group(1).upper(),
            'name': m.group(2).strip(),
            'start': m.start(),
            'end': m.end(),
        })

    for m in _PAT_ANNEX.finditer(text):
        hits.append({
            'type': 'annex',
            'key': m.group(1),
            'name': m.group(2).strip(),
            'start': m.start(),
            'end': m.end(),
        })

    # Sort by position in document
    hits.sort(key=lambda h: h['start'])
    return hits


def filter_pad(text: str, doc_type: str = 'PAD', pid: str = '') -> tuple[str, dict]:
    """
    Filter PAD text to retain only FCV-relevant sections.

    Args:
        text: Raw extracted PAD text.
        doc_type: Document type string. Non-PAD types pass through unfiltered.
        pid: Project ID string (used in fallback log message only).

    Returns:
        (filtered_text, stats) where stats contains:
            headers_found, original_chars, filtered_chars, reduction_pct,
            status ('filtered' | 'fallback' | 'passthrough'), reason (if fallback/passthrough)
    """
    original_chars = len(text)

    # Non-PAD documents pass through unfiltered
    if doc_type.upper() in _PASSTHROUGH_TYPES:
        return text, {
            'headers_found': 0,
            'original_chars': original_chars,
            'filtered_chars': original_chars,
            'reduction_pct': 0.0,
            'status': 'passthrough',
            'reason': f'doc_type={doc_type} — pass through unfiltered',
        }

    sections = detect_sections(text)

    if len(sections) < _MIN_HEADERS:
        warn = {
            'pid': pid,
            'status': 'filter_fallback',
            'headers_found': len(sections),
            'reason': 'below_threshold',
        }
        logger.warning(json.dumps(warn))
        return text, {
            'headers_found': len(sections),
            'original_chars': original_chars,
            'filtered_chars': original_chars,
            'reduction_pct': 0.0,
            'status': 'fallback',
            'reason': f'Only {len(sections)} headers detected (threshold: {_MIN_HEADERS})',
        }

    # Build list of (start, end) ranges to KEEP
    keep_ranges = _compute_keep_ranges(text, sections)

    if not keep_ranges:
        # No keepable sections found — fall back
        return text, {
            'headers_found': len(sections),
            'original_chars': original_chars,
            'filtered_chars': original_chars,
            'reduction_pct': 0.0,
            'status': 'fallback',
            'reason': 'No matching keep sections identified from headers',
        }

    # Concatenate kept ranges
    kept_parts = [text[s:e] for s, e in keep_ranges]
    body = '\n\n'.join(part.strip() for part in kept_parts if part.strip())

    filtered_chars = len(body)
    reduction_pct = round((1 - filtered_chars / original_chars) * 100, 1) if original_chars > 0 else 0.0

    header = (
        f'[FILTERED: Retained FCV-relevant sections only. '
        f'Original length: {original_chars:,} chars → Filtered: {filtered_chars:,} chars '
        f'({reduction_pct}% reduction). '
        f'Stripped: front matter, VI.A-D (economic/FM/procurement), Annexes 4-6, boilerplate.]\n\n'
    )

    filtered_text = header + body

    return filtered_text, {
        'headers_found': len(sections),
        'original_chars': original_chars,
        'filtered_chars': len(filtered_text),
        'reduction_pct': reduction_pct,
        'status': 'filtered',
    }


def run_filter_on_directory(
    country_dir: Path,
    doc_type: str = 'PAD',
    dry_run: bool = False,
    sample: int = 0,
) -> list[dict]:
    """
    Batch-filter all .txt files in <country_dir>/extracted_texts/.

    Writes filtered files to <country_dir>/extracted_texts_filtered/.
    Returns list of stats dicts (one per file processed).

    Args:
        country_dir: Path to country subfolder (e.g. Path('ethiopia')).
        doc_type: Applied to all files unless a per-file override is needed.
        dry_run: If True, do not write files — just return stats.
        sample: If > 0, process only the first N files (for validation).
    """
    src_dir = country_dir / 'extracted_texts'
    out_dir = country_dir / 'extracted_texts_filtered'

    if not src_dir.exists():
        raise FileNotFoundError(f'Source directory not found: {src_dir}')

    if not dry_run:
        out_dir.mkdir(exist_ok=True)

    txt_files = sorted(src_dir.glob('*.txt'))
    if sample:
        txt_files = txt_files[:sample]

    results = []
    for f in txt_files:
        pid = f.stem
        text = f.read_text(encoding='utf-8')
        filtered, stats = filter_pad(text, doc_type=doc_type, pid=pid)
        stats['pid'] = pid

        if not dry_run:
            out_path = out_dir / f.name
            out_path.write_text(filtered, encoding='utf-8')

        results.append(stats)
        status = stats['status']
        pct = stats.get('reduction_pct', 0)
        print(f'  {pid}: {status} ({pct}% reduction, {stats["headers_found"]} headers)')

    return results


# ─── Keep range computation ───────────────────────────────────────────────────

def _compute_keep_ranges(text: str, sections: list[dict]) -> list[tuple[int, int]]:
    """
    Given detected section headers, compute character ranges to retain.

    Strategy:
    - For each section, determine the text span from its header to the start of
      the next section (or end of document).
    - Include that span if the section is in the keep list.
    - VI subsection handling: within section VI, keep only E, F, G subsections.
    - Annex handling: keep only Annexes 1, 3, 7.
    """
    # Add sentinel at end
    sentinels = sections + [{'type': 'sentinel', 'start': len(text), 'end': len(text), 'key': '', 'name': ''}]

    ranges = []
    in_section_vi = False
    current_vi_sub_keep = False

    for i, sec in enumerate(sentinels[:-1]):
        next_start = sentinels[i + 1]['start']
        sec_start = sec['start']
        sec_type = sec['type']
        sec_key = sec['key'].upper()

        if sec_type == 'roman':
            in_section_vi = (sec_key == 'VI')
            if sec_key in _KEEP_ROMAN:
                # Keep this entire section (but VI body before first subsection only)
                # For VI: keep only what comes before the first subsection header
                if sec_key == 'VI':
                    # Find first lettered subsection within this roman section
                    sub_start = _find_first_sub_in_range(sentinels, i + 1, next_start)
                    if sub_start:
                        ranges.append((sec_start, sub_start))
                    # (individual VI subsections handled below)
                else:
                    ranges.append((sec_start, next_start))

        elif sec_type == 'letter' and in_section_vi:
            # VI subsection: keep only E, F, G
            if sec_key in _KEEP_VI_SUBS:
                ranges.append((sec_start, next_start))

        elif sec_type == 'annex':
            in_section_vi = False  # Annexes reset the VI tracking
            if sec_key in _KEEP_ANNEXES:
                ranges.append((sec_start, next_start))

    # Merge overlapping/adjacent ranges
    ranges.sort()
    merged = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append([start, end])

    return [(s, e) for s, e in merged]


def _find_first_sub_in_range(sentinels: list[dict], from_idx: int, before_char: int) -> Optional[int]:
    """Return character position of first 'letter' section starting before before_char."""
    for s in sentinels[from_idx:]:
        if s['start'] >= before_char:
            break
        if s['type'] == 'letter':
            return s['start']
    return None


# ─── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Filter PAD extracted texts')
    parser.add_argument('country_dir', help='Path to country directory (e.g. ethiopia)')
    parser.add_argument('--sample', type=int, default=0, help='Process only first N files')
    parser.add_argument('--dry-run', action='store_true', help='Do not write output files')
    parser.add_argument('--validate', action='store_true', help='Print reduction stats only')
    args = parser.parse_args()

    country_path = Path(args.country_dir)
    if not country_path.exists():
        print(f'Error: {country_path} does not exist')
        sys.exit(1)

    logging.basicConfig(level=logging.INFO)
    stats_list = run_filter_on_directory(
        country_path,
        dry_run=args.dry_run or args.validate,
        sample=args.sample,
    )

    avg_reduction = sum(s.get('reduction_pct', 0) for s in stats_list) / len(stats_list) if stats_list else 0
    fallbacks = sum(1 for s in stats_list if s['status'] == 'fallback')
    print(f'\nSummary: {len(stats_list)} files | avg reduction: {avg_reduction:.1f}% | fallbacks: {fallbacks}')
```

- [ ] **Step 2: Run tests**

```bash
cd "/c/Users/wb559324/OneDrive - WBG/Documents/GitHub/FCV-Portfolio-Screener"
python -m pytest tests/test_pad_section_filter.py -v
```

Expected: All tests pass. If any fail, debug the `_compute_keep_ranges` logic.

- [ ] **Step 3: Commit**

```bash
git add utils/pad_section_filter.py tests/test_pad_section_filter.py
git commit -m "feat: add PAD section filter with FCV-relevant section extraction"
```

---

## Task 4: Validate filter against real PAD documents

**Files:** No new files — validation only.

- [ ] **Step 1: Run filter in dry-run mode on Ethiopia sample (5 files)**

```bash
cd "/c/Users/wb559324/OneDrive - WBG/Documents/GitHub/FCV-Portfolio-Screener"
python utils/pad_section_filter.py ethiopia --validate --sample 5
```

Expected output format:
```
  P148447: filtered (44.2% reduction, 12 headers)
  P151234: filtered (51.3% reduction, 14 headers)
  P155555: fallback (0.0% reduction, 2 headers)
  P160000: filtered (47.8% reduction, 11 headers)
  P162000: filtered (38.5% reduction, 9 headers)

Summary: 5 files | avg reduction: 36.4% | fallbacks: 1
```

Acceptable result: avg reduction ≥ 25% across the sample, fallback rate ≤ 40%.

- [ ] **Step 2: Spot-check one filtered output**

```bash
# View the filter header and first 100 lines of a filtered file
python -c "
from pathlib import Path
# Run filter on one real file and print output
import sys
sys.path.insert(0, '.')
from utils.pad_section_filter import filter_pad

pid = 'P148447'  # Change to a real PID from your ethiopia/extracted_texts/
text = (Path('ethiopia/extracted_texts') / f'{pid}.txt').read_text(encoding='utf-8')
filtered, stats = filter_pad(text, pid=pid)
print(stats)
print('---FIRST 2000 CHARS---')
print(filtered[:2000])
"
```

Verify: filtered text starts with `[FILTERED:`, contains country context language, does NOT contain procurement table language.

- [ ] **Step 3: If fallback rate > 40%, debug patterns**

Run this diagnostic to see what headers were actually detected:
```bash
python -c "
from pathlib import Path
import sys
sys.path.insert(0, '.')
from utils.pad_section_filter import detect_sections

pid = 'P148447'  # Replace with a fallback PID
text = (Path('ethiopia/extracted_texts') / f'{pid}.txt').read_text(encoding='utf-8')
sections = detect_sections(text)
for s in sections[:20]:
    print(s)
"
```

If headers are detected but with wrong formatting (e.g., `'I . STRATEGIC CONTEXT'` with extra space), update the regex in `pad_section_filter.py` and re-run tests.

- [ ] **Step 4: Run full directory filter for Djibouti (22 projects)**

```bash
python utils/pad_section_filter.py djibouti
```

Expected: Creates `djibouti/extracted_texts_filtered/` with 22 filtered files.

- [ ] **Step 5: Commit validation results to a log file**

```bash
python utils/pad_section_filter.py ethiopia --validate > docs/filter_validation_ethiopia.txt 2>&1
python utils/pad_section_filter.py djibouti --validate > docs/filter_validation_djibouti.txt 2>&1
git add docs/filter_validation_*.txt
git commit -m "docs: add PAD section filter validation logs for Ethiopia and Djibouti"
```

---

## Task 5: ISR fetcher — tests and implementation

**Files:**
- Create: `tests/test_fetch_isrs.py`
- Create: `utils/fetch_isrs.py`

- [ ] **Step 1: Write failing tests for ISR fetcher**

Create `tests/test_fetch_isrs.py`:

```python
"""Tests for ISR/ICR fetcher utility."""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.fetch_isrs import (
    fetch_isr_metadata,
    extract_isr_text,
    parse_isr_date,
    build_isr_filename,
)

FIXTURES = Path(__file__).parent / 'fixtures'


# ─── parse_isr_date ────────────────────────────────────────────────────────────

def test_parse_isr_date_standard():
    assert parse_isr_date('20230315') == '2023-03'


def test_parse_isr_date_slash():
    assert parse_isr_date('2023/03/15') == '2023-03'


def test_parse_isr_date_invalid():
    result = parse_isr_date('unknown')
    assert result == 'unknown'


# ─── build_isr_filename ────────────────────────────────────────────────────────

def test_build_isr_filename_isr():
    name = build_isr_filename('P999999', 'Implementation Status and Results Report', '2023-03')
    assert name == 'P999999_ISR_2023-03.txt'


def test_build_isr_filename_icr():
    name = build_isr_filename('P999999', 'Implementation Completion Report', '2021-06')
    assert name == 'P999999_ICR_2021-06.txt'


def test_build_isr_filename_unknown_doctype():
    name = build_isr_filename('P999999', 'Some Other Document', '2022-01')
    assert name == 'P999999_OTHER_2022-01.txt'


# ─── extract_isr_text ─────────────────────────────────────────────────────────

def test_extract_isr_text_short_document():
    """Documents shorter than head+tail cap are returned in full."""
    short_text = 'A' * 5000
    result = extract_isr_text(short_text, head_chars=10_000, tail_chars=5_000)
    assert result == short_text


def test_extract_isr_text_long_document():
    """Long documents: return head + separator + tail."""
    long_text = 'A' * 20_000
    result = extract_isr_text(long_text, head_chars=10_000, tail_chars=5_000)
    assert len(result) < len(long_text)
    assert '[...]' in result  # separator present


def test_extract_isr_text_respects_head_cap():
    long_text = 'START' + 'X' * 20_000 + 'END'
    result = extract_isr_text(long_text, head_chars=10_000, tail_chars=5_000)
    assert result.startswith('START')


def test_extract_isr_text_includes_tail():
    long_text = 'X' * 20_000 + 'TAIL_MARKER'
    result = extract_isr_text(long_text, head_chars=10_000, tail_chars=5_000)
    assert 'TAIL_MARKER' in result


# ─── fetch_isr_metadata (mock API) ────────────────────────────────────────────

def test_fetch_isr_metadata_returns_list():
    mock_response = json.dumps({
        'documents': {
            'doc1': {
                'id': 'doc1',
                'docdt': '20230315',
                'docty': 'Implementation Status and Results Report',
                'url': 'https://example.com/isr.pdf',
            }
        },
        'total': 1,
    }).encode()

    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=mock_response)))
    mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

    with patch('utils.fetch_isrs.urllib.request.urlopen', mock_urlopen):
        result = fetch_isr_metadata('P999999')

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]['doc_type'] == 'Implementation Status and Results Report'
    assert result[0]['date'] == '2023-03'
    assert result[0]['url'] == 'https://example.com/isr.pdf'


def test_fetch_isr_metadata_empty_response():
    mock_response = json.dumps({'documents': {}, 'total': 0}).encode()
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=mock_response)))
    mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

    with patch('utils.fetch_isrs.urllib.request.urlopen', mock_urlopen):
        result = fetch_isr_metadata('P000000')

    assert result == []
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_fetch_isrs.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'utils.fetch_isrs'`

- [ ] **Step 3: Implement `utils/fetch_isrs.py`**

```python
"""
ISR/ICR Fetcher — fetches Implementation Status Reports and Completion Reports
from the WB Documents API for portfolio projects, extracts head+tail text.

Usage (module):
    from utils.fetch_isrs import run_isr_fetch

Usage (CLI):
    python utils/fetch_isrs.py <country_dir>
    python utils/fetch_isrs.py djibouti
"""

import json
import re
import ssl
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

# ─── Constants ────────────────────────────────────────────────────────────────

HEAD_CHARS = 10_000   # First 10k chars of ISR PDF (captures ratings, key issues)
TAIL_CHARS = 5_000    # Last 5k chars (captures actions required, closing remarks)

# Document type labels that indicate ISRs or ICRs
ISR_DOC_TYPES = {
    'Implementation Status and Results Report',
    'Implementation Status Report',
}
ICR_DOC_TYPES = {
    'Implementation Completion Report',
    'Implementation Completion and Results Report',
}
TARGET_DOC_TYPES = ISR_DOC_TYPES | ICR_DOC_TYPES

# WB Documents API — use 'projectid' (no underscore) for ISR/ICR queries
# NOTE: The projects API uses 'project_id' (with underscore) but wds endpoint
# for document type filtering requires 'projectid'. Confirmed against P151492.
WDS_URL = (
    'https://search.worldbank.org/api/v2/wds'
    '?format=json&projectid={pid}'
    '&docty_exact=Implementation+Status+and+Results+Report'
    '&fl=id,docdt,docty,url&rows=50'
)

# Separate query for ICRs
ICR_URL = (
    'https://search.worldbank.org/api/v2/wds'
    '?format=json&projectid={pid}'
    '&docty_exact=Implementation+Completion+Report'
    '&fl=id,docdt,docty,url&rows=10'
)


def _make_ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


SSL_CTX = _make_ssl_ctx()


# ─── Public API ───────────────────────────────────────────────────────────────

def parse_isr_date(raw_date: str) -> str:
    """Normalise a WB API date string to 'YYYY-MM' format."""
    # Try YYYYMMDD
    m = re.match(r'(\d{4})(\d{2})\d{2}', raw_date.replace('/', '').replace('-', ''))
    if m:
        return f'{m.group(1)}-{m.group(2)}'
    # Try YYYY/MM/DD or YYYY-MM-DD
    m = re.match(r'(\d{4})[/-](\d{2})', raw_date)
    if m:
        return f'{m.group(1)}-{m.group(2)}'
    return raw_date


def build_isr_filename(pid: str, doc_type: str, date: str) -> str:
    """Build output filename for an ISR/ICR file."""
    if doc_type in ISR_DOC_TYPES:
        label = 'ISR'
    elif doc_type in ICR_DOC_TYPES:
        label = 'ICR'
    else:
        label = 'OTHER'
    return f'{pid}_{label}_{date}.txt'


def extract_isr_text(text: str, head_chars: int = HEAD_CHARS, tail_chars: int = TAIL_CHARS) -> str:
    """
    Apply head+tail extraction to ISR text.
    Short documents (≤ head+tail cap) are returned in full.
    """
    cap = head_chars + tail_chars
    if len(text) <= cap:
        return text

    head = text[:head_chars]
    tail = text[max(head_chars, len(text) - tail_chars):]
    return head + '\n\n[...]\n\n' + tail


def fetch_isr_metadata(pid: str) -> list[dict]:
    """
    Query WB Documents API for ISRs and ICRs for a given project ID.

    Returns list of dicts with keys: id, doc_type, date, url.
    Returns empty list if none found or on API error.
    """
    results = []
    for url_template in (WDS_URL, ICR_URL):
        url = url_template.format(pid=pid)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as r:
                data = json.loads(r.read())
            docs = data.get('documents', {})
            for doc in docs.values():
                if not isinstance(doc, dict):
                    continue
                doc_type = doc.get('docty', '')
                if doc_type not in TARGET_DOC_TYPES:
                    continue
                results.append({
                    'id': doc.get('id', ''),
                    'doc_type': doc_type,
                    'date': parse_isr_date(doc.get('docdt', 'unknown')),
                    'url': doc.get('url', ''),
                })
        except Exception as e:
            print(f'  Warning: API error for {pid}: {e}')

    # Sort chronologically
    results.sort(key=lambda d: d['date'])
    return results


def fetch_and_save_isrs(pid: str, out_dir: Path, delay: float = 0.3) -> list[dict]:
    """
    Fetch all ISRs/ICRs for a project, extract text, save to out_dir.

    Returns list of saved file metadata dicts.
    """
    metadata = fetch_isr_metadata(pid)
    saved = []

    for doc in metadata:
        if not doc['url']:
            continue

        filename = build_isr_filename(pid, doc['doc_type'], doc['date'])
        out_path = out_dir / filename

        if out_path.exists():
            print(f'  {filename}: already exists, skipping')
            saved.append({**doc, 'filename': filename, 'status': 'skipped'})
            continue

        try:
            req = urllib.request.Request(doc['url'], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=90) as r:
                pdf_bytes = r.read()

            fitz_doc = fitz.open(stream=pdf_bytes, filetype='pdf')
            text = ''.join(page.get_text() for page in fitz_doc)
            fitz_doc.close()

            extracted = extract_isr_text(text)
            out_path.write_text(extracted, encoding='utf-8')

            print(f'  {filename}: saved ({len(extracted):,} chars)')
            saved.append({**doc, 'filename': filename, 'status': 'saved'})
            time.sleep(delay)

        except Exception as e:
            print(f'  {filename}: error — {e}')
            saved.append({**doc, 'filename': filename, 'status': 'error', 'error': str(e)})

    return saved


def run_isr_fetch(country_dir: Path, delay: float = 0.3) -> dict:
    """
    Fetch ISRs/ICRs for all projects in <country_dir>/screening_targets.json.

    Saves extracted texts to <country_dir>/extracted_texts_isr/.
    Returns summary dict with counts.
    """
    targets_file = country_dir / 'screening_targets.json'
    if not targets_file.exists():
        raise FileNotFoundError(f'screening_targets.json not found in {country_dir}')

    targets = json.loads(targets_file.read_text(encoding='utf-8'))
    out_dir = country_dir / 'extracted_texts_isr'
    out_dir.mkdir(exist_ok=True)

    total_isrs = 0
    projects_with_isrs = 0

    for project in targets:
        pid = project['project_id']
        print(f'\n{pid}: {project.get("project_name", "")[:60]}')
        saved = fetch_and_save_isrs(pid, out_dir, delay=delay)
        count = sum(1 for s in saved if s['status'] == 'saved')
        total_isrs += count
        if count > 0:
            projects_with_isrs += 1

    return {
        'total_projects': len(targets),
        'projects_with_isrs': projects_with_isrs,
        'total_isrs_saved': total_isrs,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Fetch ISR/ICR documents for portfolio projects')
    parser.add_argument('country_dir', help='Path to country directory (e.g. djibouti)')
    parser.add_argument('--delay', type=float, default=0.3, help='Delay between API calls (seconds)')
    args = parser.parse_args()

    country_path = Path(args.country_dir)
    if not country_path.exists():
        print(f'Error: {country_path} does not exist')
        sys.exit(1)

    summary = run_isr_fetch(country_path, delay=args.delay)
    print(f'\n=== ISR Fetch Summary ===')
    print(f'Projects processed:    {summary["total_projects"]}')
    print(f'Projects with ISRs:    {summary["projects_with_isrs"]}')
    print(f'Total ISRs/ICRs saved: {summary["total_isrs_saved"]}')
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_fetch_isrs.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Live API test against known project**

```bash
# Quick test: confirm the API returns ISRs for a known Djibouti project
python -c "
import sys; sys.path.insert(0, '.')
from utils.fetch_isrs import fetch_isr_metadata
result = fetch_isr_metadata('P151492')  # Known Somalia project with ISRs
print(f'Found {len(result)} ISRs/ICRs:')
for r in result:
    print(f'  {r[\"date\"]} — {r[\"doc_type\"]} — {r[\"url\"][:60]}...')
"
```

Expected: 1–5 documents listed. If the result is empty, try the alternative parameter name:
```bash
python -c "
# Try projectid vs project_id debug
import ssl, urllib.request, json
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
for param in ('projectid', 'project_id'):
    url = f'https://search.worldbank.org/api/v2/wds?format=json&{param}=P151492&docty_exact=Implementation+Status+and+Results+Report&rows=5'
    with urllib.request.urlopen(url, context=ctx, timeout=10) as r:
        data = json.loads(r.read())
    print(f'{param}: {data.get(\"total\", 0)} results')
"
```

Update the `WDS_URL` constant in `fetch_isrs.py` to use whichever parameter works, then re-run tests.

- [ ] **Step 6: Commit**

```bash
git add utils/fetch_isrs.py tests/test_fetch_isrs.py
git commit -m "feat: add ISR/ICR fetcher with head+tail extraction"
```

---

## Task 6: Update normalize_results.py for new schema fields

**Files:**
- Modify: `ethiopia/normalize_results.py`
- Modify: `djibouti/normalize_results.py`

- [ ] **Step 1: Add new field handling to Ethiopia normalize_results.py**

In `ethiopia/normalize_results.py`, find the `normalize(r)` function and extend its return dict. Add the four new fields with explicit defaults:

```python
# In the normalize(r) function, add to the return dict:
return {
    # ... all existing fields unchanged ...
    'project_id': r['project_id'],
    # ... existing fields ...
    'dimensions': normalize_dims(r.get('dimensions', [])),
    # NEW FIELDS — backward compatible, default to absent/null
    'isr_count': r.get('isr_count', 0),
    'score_adjusted': r.get('score_adjusted', False),
    'trajectory': r.get('trajectory', None),
}
```

Also update `normalize_dims` to handle the new per-dimension optional fields:

```python
def normalize_dims(dims):
    # ... existing list/dict handling ...
    # In the result.append() call, add:
    result.append({
        'id': d.get('id', 0),
        'name': d.get('name', ''),
        'composite': d.get('composite', ''),
        'numeric_score': score,
        'rating': d.get('rating', score_to_rating(score)),
        'key_quote': d.get('key_quote', d.get('evidence', '')),
        'rationale': d.get('rationale', ''),
        # NEW: pad_score defaults to None (not copied from numeric_score)
        'pad_score': d.get('pad_score', None),
        'adjustment_reason': d.get('adjustment_reason', None),
    })
```

- [ ] **Step 2: Apply same change to djibouti/normalize_results.py**

Open the file and make the identical additions. The Djibouti version may be slightly simpler (no summary stats block) but the `normalize()` and `normalize_dims()` functions are the same pattern.

- [ ] **Step 3: Test normalize still works on existing data**

```bash
cd "/c/Users/wb559324/OneDrive - WBG/Documents/GitHub/FCV-Portfolio-Screener"
python ethiopia/normalize_results.py
```

Expected: Runs without error. The output normalized JSON should have `isr_count: 0`, `score_adjusted: false`, `trajectory: null` added to every project. Spot-check:

```bash
python -c "
import json
data = json.load(open('ethiopia/20260316_ethiopia_screening_results_normalized.json'))
p = data[0]
print('isr_count:', p.get('isr_count'))
print('score_adjusted:', p.get('score_adjusted'))
print('trajectory:', p.get('trajectory'))
print('dim pad_score:', p['dimensions'][0].get('pad_score'))
"
```

Expected: `isr_count: 0`, `score_adjusted: False`, `trajectory: None`, `pad_score: None`.

- [ ] **Step 4: Commit**

```bash
git add ethiopia/normalize_results.py djibouti/normalize_results.py
git commit -m "feat: extend normalize_results to handle ISR adjustment fields with safe defaults"
```

---

## Task 7: Combined screening prompt builder

**Files:**
- Create: `tests/test_build_screening_prompt.py`
- Create: `utils/build_screening_prompt.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_build_screening_prompt.py`:

```python
"""Tests for screening prompt builder."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.build_screening_prompt import build_prompt

FIXTURES = Path(__file__).parent / 'fixtures'


def test_pad_only_prompt_contains_primary_label():
    pad_text = 'FILTERED PAD CONTENT here.'
    prompt = build_prompt(pid='P999999', project_name='Test Project',
                          doc_type='PAD', instrument='IPF', year=2019,
                          pad_text=pad_text, isr_texts=[])
    assert 'PRIMARY DOCUMENT' in prompt
    assert pad_text in prompt


def test_pad_only_prompt_no_supplementary_section():
    prompt = build_prompt(pid='P999999', project_name='Test Project',
                          doc_type='PAD', instrument='IPF', year=2019,
                          pad_text='Some PAD text.', isr_texts=[])
    assert 'SUPPLEMENTARY DOCUMENTS' not in prompt


def test_with_isrs_prompt_contains_supplementary():
    isr_texts = [('ISR', '2021-03', 'ISR content here.')]
    prompt = build_prompt(pid='P999999', project_name='Test Project',
                          doc_type='PAD', instrument='IPF', year=2019,
                          pad_text='PAD text.', isr_texts=isr_texts)
    assert 'SUPPLEMENTARY DOCUMENTS' in prompt
    assert 'ISR content here.' in prompt


def test_with_isrs_prompt_contains_adjustment_instructions():
    isr_texts = [('ISR', '2022-06', 'Some ISR text.')]
    prompt = build_prompt(pid='P999999', project_name='Test',
                          doc_type='PAD', instrument='IPF', year=2020,
                          pad_text='PAD.', isr_texts=isr_texts)
    assert 'adjust' in prompt.lower()
    assert 'trajectory' in prompt.lower()


def test_prompt_contains_project_metadata():
    prompt = build_prompt(pid='P999999', project_name='Djibouti Roads',
                          doc_type='PAD', instrument='DPF', year=2017,
                          pad_text='PAD text.', isr_texts=[])
    assert 'P999999' in prompt
    assert 'Djibouti Roads' in prompt
    assert 'DPF' in prompt
    assert '2017' in prompt


def test_output_file_instruction_in_prompt():
    prompt = build_prompt(pid='P999999', project_name='Test',
                          doc_type='PAD', instrument='IPF', year=2018,
                          pad_text='PAD text.', isr_texts=[],
                          output_path='djibouti/screening_results_P999999.json')
    assert 'djibouti/screening_results_P999999.json' in prompt


def test_isr_count_in_prompt():
    isr_texts = [
        ('ISR', '2020-01', 'ISR 1 content.'),
        ('ISR', '2021-06', 'ISR 2 content.'),
    ]
    prompt = build_prompt(pid='P999999', project_name='Test',
                          doc_type='PAD', instrument='IPF', year=2019,
                          pad_text='PAD text.', isr_texts=isr_texts)
    assert '2' in prompt  # isr count mentioned
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_build_screening_prompt.py -v 2>&1 | head -10
```

- [ ] **Step 3: Implement `utils/build_screening_prompt.py`**

```python
"""
Screening prompt builder — assembles the agent prompt for FCV screening.

Supports PAD-only mode (current behaviour) and PAD + ISR mode (new).

Usage:
    from utils.build_screening_prompt import build_prompt
"""

from pathlib import Path


def build_prompt(
    pid: str,
    project_name: str,
    doc_type: str,
    instrument: str,
    year: int,
    pad_text: str,
    isr_texts: list[tuple[str, str, str]],  # list of (doc_type, date, text)
    output_path: str = '',
) -> str:
    """
    Build the full agent prompt for FCV screening.

    Args:
        pid: Project ID (e.g. 'P148447').
        project_name: Full project name.
        doc_type: Primary document type ('PAD', 'Program Document', etc.).
        instrument: Lending instrument ('IPF', 'DPF', 'P4R').
        year: Approval year.
        pad_text: Extracted (and filtered) PAD text.
        isr_texts: List of (doc_type_label, date, text) for each supplementary doc.
                   Empty list for PAD-only mode.
        output_path: Where the agent should save its JSON output. If empty,
                     the agent will be instructed to output to stdout.

    Returns:
        Complete prompt string ready to pass to a screener agent.
    """
    has_isrs = len(isr_texts) > 0

    # ── Header block ────────────────────────────────────────────────────────
    header = (
        f'Screen this project using the FCV screener skill.\n'
        f'Project ID: {pid} | Name: {project_name}\n'
        f'Document type: {doc_type} | Instrument: {instrument} | Year: {year}\n'
    )
    if output_path:
        header += f'\nSave result to: {output_path}\n'

    header += (
        '\nOutput format constraints (strictly enforced):\n'
        '- key_quote: max 250 chars per dimension\n'
        '- rationale per dimension: max 3 sentences / 200 words\n'
        '- key_finding: max 2 sentences / 100 words\n'
        '- Output: a single JSON object only. No preamble before the JSON.\n'
    )

    # ── ISR adjustment instructions (only if ISRs present) ─────────────────
    if has_isrs:
        isr_count = len(isr_texts)
        header += (
            f'\nISR ADJUSTMENT INSTRUCTIONS ({isr_count} supplementary document(s) provided):\n'
            '1. Score all 8 dimensions using the PRIMARY DOCUMENT (PAD) as your primary evidence.\n'
            '2. After scoring, review each SUPPLEMENTARY DOCUMENT in chronological order.\n'
            '3. For any dimension where ISR/ICR evidence materially changes your assessment\n'
            '   (e.g. documented security deterioration with no adaptive response, or a course\n'
            '   correction that improved FCV sensitivity), adjust that dimension\'s score.\n'
            '4. For each adjusted dimension, record the original pad_score and the adjustment_reason.\n'
            '5. Add a trajectory field (2-3 sentences) describing what the ISRs revealed about\n'
            '   implementation-phase FCV sensitivity.\n'
            '6. Set score_adjusted: true if any dimension was changed; false otherwise.\n'
            f'7. Set isr_count: {isr_count}.\n'
        )

    # ── Primary document ────────────────────────────────────────────────────
    body = f'\n---\nPRIMARY DOCUMENT ({doc_type}):\n\n{pad_text}\n'

    # ── Supplementary documents ─────────────────────────────────────────────
    if has_isrs:
        body += f'\n---\nSUPPLEMENTARY DOCUMENTS ({len(isr_texts)} ISR/ICR, chronological order):\n'
        for i, (dtype, date, text) in enumerate(isr_texts, 1):
            body += f'\n[Document {i}: {dtype} — {date}]\n\n{text}\n'

    return header + body
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_build_screening_prompt.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add utils/build_screening_prompt.py tests/test_build_screening_prompt.py
git commit -m "feat: add combined PAD+ISR screening prompt builder"
```

---

## Task 8: End-to-end test on Djibouti

**Files:** No new files. Test the full enhanced pipeline on Djibouti (22 projects).

- [ ] **Step 1: Filter Djibouti PAD texts (if not already done in Task 4)**

```bash
cd "/c/Users/wb559324/OneDrive - WBG/Documents/GitHub/FCV-Portfolio-Screener"
python utils/pad_section_filter.py djibouti
```

Verify `djibouti/extracted_texts_filtered/` contains 22 `.txt` files.

- [ ] **Step 2: Fetch Djibouti ISRs**

```bash
python utils/fetch_isrs.py djibouti
```

Note the summary output: how many projects have ISRs, how many total ISRs saved.
Verify `djibouti/extracted_texts_isr/` is created with files.

- [ ] **Step 3: Run a single-project test screening with the combined prompt**

Pick one Djibouti project that has at least 1 ISR (check `extracted_texts_isr/` for a PID with files). Run a background agent:

```bash
python -c "
import sys, json
from pathlib import Path
sys.path.insert(0, '.')
from utils.build_screening_prompt import build_prompt

# Load one project from screening_targets
targets = json.loads(Path('djibouti/screening_targets.json').read_text())
pid = None
isr_dir = Path('djibouti/extracted_texts_isr')
for t in targets:
    isr_files = sorted(isr_dir.glob(f'{t[\"project_id\"]}_*.txt'))
    if isr_files:
        pid = t['project_id']
        project = t
        break

if not pid:
    print('No projects with ISRs found — using PAD-only mode')
    project = targets[0]
    pid = project['project_id']
    isr_files = []

# Load filtered PAD text
pad_path = Path('djibouti/extracted_texts_filtered') / f'{pid}.txt'
if not pad_path.exists():
    pad_path = Path('djibouti/extracted_texts') / f'{pid}.txt'
pad_text = pad_path.read_text(encoding='utf-8')

# Load ISR texts
isr_texts = []
for f in sorted(isr_files):
    parts = f.stem.split('_')  # P123456_ISR_2021-03
    dtype = parts[1] if len(parts) > 1 else 'ISR'
    date = parts[2] if len(parts) > 2 else 'unknown'
    isr_texts.append((dtype, date, f.read_text(encoding='utf-8')))

prompt = build_prompt(
    pid=pid,
    project_name=project['project_name'],
    doc_type=project['doc_type'],
    instrument=project['instrument_category'],
    year=project['approval_year'],
    pad_text=pad_text,
    isr_texts=isr_texts,
    output_path=f'djibouti/screening_results_{pid}.json',
)
print(f'Prompt for {pid} ({len(isr_texts)} ISRs):')
print(f'  Total chars: {len(prompt):,}')
print(f'  First 300 chars:')
print(prompt[:300])
"
```

Review the prompt output to confirm it's well-formed before running a live agent.

- [ ] **Step 4: Launch screening agent for the test project**

Copy the prompt output and paste into a new Claude Code background agent. Wait for it to complete and save its output JSON.

> **Note:** This is the one step that requires running a live Claude agent. Alternatively, assess the prompt quality visually and proceed directly to the full Djibouti run if it looks correct.

- [ ] **Step 5: Verify screening output includes new fields**

```bash
python -c "
import json
from pathlib import Path
# Find the output file from the test screening
for f in sorted(Path('djibouti').glob('screening_results_P*.json')):
    data = json.loads(f.read_text())
    print(f'{f.name}:')
    print(f'  isr_count: {data.get(\"isr_count\", \"MISSING\")}')
    print(f'  score_adjusted: {data.get(\"score_adjusted\", \"MISSING\")}')
    print(f'  trajectory: {data.get(\"trajectory\", \"MISSING\")}')
    break
"
```

Expected: Fields present (even if `isr_count: 0` for a PAD-only screening).

- [ ] **Step 6: Run normalize on test output**

```bash
python djibouti/normalize_results.py
```

Expected: Runs without error. New fields in normalized JSON.

- [ ] **Step 7: Final commit**

```bash
git add .
git commit -m "feat: end-to-end test — PAD filter + ISR fetch + combined prompt on Djibouti"
```

---

## Appendix: Running the full pipeline for a new country

Once all tasks are complete, the enhanced pipeline for a new country (e.g., CAR) is:

```bash
# 1. Data collection (existing — unchanged)
python car/YYYYMMDD_car_data_collection.py   # Steps 1-3

# 2. Filter PAD texts (new)
python utils/pad_section_filter.py car

# 3. Fetch ISRs (new)
python utils/fetch_isrs.py car

# 4. Screening (launch agents using build_prompt — same as before but use filtered texts)
#    For each project: build_prompt(..., pad_text from extracted_texts_filtered/, isr_texts from extracted_texts_isr/)

# 5. Normalize (existing — now handles new fields)
python car/normalize_results.py

# 6-7. Analysis and report (existing — unchanged)
python car/YYYYMMDD_car_fcv_analysis.py
python car/generate_report.py
```

The token saving is immediate: filtered PAD texts are ~40–50% shorter, and ISR additions are offset by that reduction.
