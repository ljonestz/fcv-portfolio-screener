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
    assert '[...]' in result


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
