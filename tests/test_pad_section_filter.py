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
