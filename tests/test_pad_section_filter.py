"""Tests for PAD section filter utility."""
import sys
from pathlib import Path

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
    assert 'Regional Risk Assessment' in filtered
    assert stats['status'] == 'filtered'


def test_retains_key_risks_sort():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'SORT' in filtered or 'KEY RISKS' in filtered.upper()


def test_strips_financial_management():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'OP/BP 10.02' not in filtered


def test_strips_procurement():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'Procurement Regulations for IPF Borrowers' not in filtered


def test_retains_social_safeguards():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'Grievance Redress Mechanism' in filtered


def test_retains_annex_1_results():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'Do-No-Harm Indicators' in filtered


def test_retains_annex_3_implementation():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'FCV Specialist' in filtered


def test_strips_annex_5_economic():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'NPV calculations' not in filtered


def test_retains_annex_7_social():
    text = load_fixture('sample_pad.txt')
    filtered, stats = filter_pad(text)
    assert 'Stakeholder Engagement Plan' in filtered


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
    assert filtered == text
    assert stats['status'] == 'fallback'
    assert stats['headers_found'] < 5


def test_fallback_preserves_full_text():
    text = "Short unstructured document.\n\nSome more text."
    filtered, stats = filter_pad(text)
    assert filtered == text


# ─── Table of Contents regression tests ───────────────────────────────────────

# Real World Bank PADs begin with a Table of Contents where section headers appear
# as dot-leader lines (e.g. "I. STRATEGIC CONTEXT ......................  7").
# These lines previously caused the filter to match ToC entries instead of the real
# body headers, producing near-zero filtered output (95%+ reduction).

_TOC_PAD = """\
WORLD BANK PROJECT APPRAISAL DOCUMENT

TABLE OF CONTENTS

I. STRATEGIC CONTEXT ....................................................  5
A. Country Context ......................................................  5
B. Sectoral and Institutional Context ..................................  8
II. PROJECT DESCRIPTION .................................................  12
A. PDO ...................................................................  12
B. Project Components ...................................................  13
III. IMPLEMENTATION .....................................................  20
IV. KEY RISKS ...........................................................  25
V. APPRAISAL SUMMARY ....................................................  30
A. Economic Analysis ....................................................  30
B. Technical .............................................................  31
C. Financial Management .................................................  32
D. Procurement ...........................................................  33
E. Social (including Safeguards) ........................................  34
VI. RESULTS FRAMEWORK AND MONITORING ...................................  38
Annex 1: Detailed Project Description ..................................  45
Annex 2: Implementation Arrangements ...................................  50
Annex 3: Implementation Support Plan ..................................  55
Annex 5: Economic and Financial Analysis ..............................  60
Annex 7: Stakeholder Engagement Plan ...................................  65

I. STRATEGIC CONTEXT

A. Country Context

1. The country faces significant fragility risks. The Regional Risk Assessment
identifies three key drivers of conflict: land tenure disputes, resource scarcity,
and weak state legitimacy in peripheral regions.

B. Sectoral and Institutional Context

2. The education sector has been severely affected by displacement.

II. PROJECT DESCRIPTION

A. PDO

3. The project development objective is to improve access to quality education
for conflict-affected populations in target regions.

B. Project Components

4. Component 1 focuses on school rehabilitation in conflict-affected zones.

III. IMPLEMENTATION

A. Institutional and Implementation Arrangements

5. Implementation will be led by the Ministry of Education with support from
a dedicated FCV Specialist embedded in the PIU.

IV. KEY RISKS

A. Overall Risk Rating

6. The overall risk rating is High due to the volatile security environment.

V. APPRAISAL SUMMARY

A. Economic Analysis

7. The economic rate of return is estimated at 12 percent.

B. Technical

8. The technical design follows best practices for fragile settings.

C. Financial Management

9. OP/BP 10.02 requirements apply. Procurement Regulations for IPF Borrowers.

D. Procurement

10. Procurement will follow World Bank procurement guidelines.

E. Social (including Safeguards)

11. A Grievance Redress Mechanism will be established in all target districts
to ensure community accountability and conflict-sensitive feedback loops.

Annex 1: Detailed Project Description

Do-No-Harm Indicators: The project will monitor conflict sensitivity through
quarterly community perception surveys.

Annex 3: Implementation Support Plan

FCV Specialist: A dedicated FCV Specialist will conduct bi-annual conflict
sensitivity assessments throughout implementation.

Annex 5: Economic and Financial Analysis

NPV calculations show a net present value of US$4.2 million.

Annex 7: Stakeholder Engagement Plan

Stakeholder Engagement Plan: Community consultations were conducted in all
target districts prior to project design.

BORROWER COMMENTS

The Government of [Country] welcomes this project and confirms its commitment.
"""


def test_toc_dot_leaders_not_matched_as_sections():
    """ToC lines with dot leaders must not be detected as section headers."""
    sections = detect_sections(_TOC_PAD)
    # All detected headers must NOT have periods/dots in the name
    for sec in sections:
        assert '.' not in sec['name'], (
            f"Section '{sec['name']}' looks like a ToC entry (contains a period); "
            f"dot-leader lines should be excluded"
        )


def test_toc_pad_uses_body_headers_not_toc():
    """Filter must capture body-section content, not ToC placeholder positions."""
    filtered, stats = filter_pad(_TOC_PAD)
    # The real body text must be present
    assert 'Regional Risk Assessment' in filtered, (
        "Body content from Section I not found — filter may have used ToC positions"
    )
    assert 'FCV Specialist' in filtered, (
        "Body content from Annex 3 not found — filter may have used ToC positions"
    )


def test_toc_pad_reduction_within_expected_range():
    """Reduction on a PAD with ToC must be 30–70%, not 90%+."""
    _, stats = filter_pad(_TOC_PAD)
    assert stats['status'] == 'filtered', f"Expected 'filtered', got {stats['status']}"
    assert stats['reduction_pct'] < 75, (
        f"Reduction {stats['reduction_pct']}% is too aggressive — "
        f"ToC dot-leader lines may be matched instead of real body headers"
    )


# ─── non-PAD pass-through ──────────────────────────────────────────────────────

def test_isr_passes_through_unfiltered():
    text = load_fixture('sample_isr.txt')
    filtered, stats = filter_pad(text, doc_type='ISR')
    assert filtered == text
    assert stats['status'] == 'passthrough'


def test_icr_passes_through_unfiltered():
    # Uses ISR fixture — passthrough is doc_type-based, not content-based
    text = load_fixture('sample_isr.txt')
    filtered, stats = filter_pad(text, doc_type='ICR')
    assert filtered == text
    assert stats['status'] == 'passthrough'
