"""Tests for ISR/ICR fetcher utility."""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.fetch_isrs import (
    fetch_isr_metadata,
    fetch_and_save_isrs,
    extract_isr_text,
    parse_isr_date,
    build_isr_filename,
    _fetch_text_from_txturl,
    _fetch_text_from_pdfurl,
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
                'pdfurl': 'https://example.com/isr-direct.pdf',
                'txturl': 'https://example.com/isr.txt',
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
    assert result[0]['pdfurl'] == 'https://example.com/isr-direct.pdf'
    assert result[0]['txturl'] == 'https://example.com/isr.txt'


def test_fetch_isr_metadata_empty_response():
    mock_response = json.dumps({'documents': {}, 'total': 0}).encode()
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=mock_response)))
    mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

    with patch('utils.fetch_isrs.urllib.request.urlopen', mock_urlopen):
        result = fetch_isr_metadata('P000000')

    assert result == []


# ─── _fetch_text_from_txturl ─────────────────────────────────────────────────

def test_fetch_text_from_txturl_returns_text():
    real_text = 'A' * 5000  # Longer than 500-char minimum
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__ = MagicMock(
        return_value=MagicMock(read=MagicMock(return_value=real_text.encode('utf-8')))
    )
    mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

    with patch('utils.fetch_isrs.urllib.request.urlopen', mock_urlopen):
        result = _fetch_text_from_txturl('https://example.com/isr.txt')

    assert result == real_text


def test_fetch_text_from_txturl_rejects_stub():
    """Stub responses (< 500 chars) are rejected."""
    stub = 'Short stub response'
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__ = MagicMock(
        return_value=MagicMock(read=MagicMock(return_value=stub.encode('utf-8')))
    )
    mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

    with patch('utils.fetch_isrs.urllib.request.urlopen', mock_urlopen):
        result = _fetch_text_from_txturl('https://example.com/isr.txt')

    assert result is None


# ─── fetch_and_save_isrs fallback chain ──────────────────────────────────────

def test_fetch_and_save_isrs_prefers_txturl(tmp_path):
    """When txturl succeeds, pdfurl should not be attempted."""
    real_text = 'ISR content from txturl ' * 200  # > 500 chars

    with patch('utils.fetch_isrs.fetch_isr_metadata') as mock_meta, \
         patch('utils.fetch_isrs._fetch_text_from_txturl', return_value=real_text) as mock_txt, \
         patch('utils.fetch_isrs._fetch_text_from_pdfurl') as mock_pdf:
        mock_meta.return_value = [{
            'id': 'doc1', 'doc_type': 'Implementation Status and Results Report',
            'date': '2023-03', 'url': '', 'pdfurl': 'https://x.pdf', 'txturl': 'https://x.txt',
        }]
        result = fetch_and_save_isrs('P999999', tmp_path, delay=0)

    assert len(result) == 1
    assert result[0]['status'] == 'saved'
    assert result[0]['source'] == 'txturl'
    mock_pdf.assert_not_called()
    # Verify file was written
    assert (tmp_path / 'P999999_ISR_2023-03.txt').exists()


def test_fetch_and_save_isrs_falls_back_to_pdfurl(tmp_path):
    """When txturl fails, should fall back to pdfurl."""
    real_text = 'ISR content from pdfurl ' * 200

    with patch('utils.fetch_isrs.fetch_isr_metadata') as mock_meta, \
         patch('utils.fetch_isrs._fetch_text_from_txturl', return_value=None) as mock_txt, \
         patch('utils.fetch_isrs._fetch_text_from_pdfurl', return_value=real_text) as mock_pdf:
        mock_meta.return_value = [{
            'id': 'doc1', 'doc_type': 'Implementation Status and Results Report',
            'date': '2023-03', 'url': '', 'pdfurl': 'https://x.pdf', 'txturl': 'https://x.txt',
        }]
        result = fetch_and_save_isrs('P999999', tmp_path, delay=0)

    assert len(result) == 1
    assert result[0]['status'] == 'saved'
    assert result[0]['source'] == 'pdfurl'


def test_fetch_and_save_isrs_skips_when_both_fail(tmp_path):
    """When both txturl and pdfurl fail, status should be 'no_content'."""
    with patch('utils.fetch_isrs.fetch_isr_metadata') as mock_meta, \
         patch('utils.fetch_isrs._fetch_text_from_txturl', return_value=None), \
         patch('utils.fetch_isrs._fetch_text_from_pdfurl', return_value=None):
        mock_meta.return_value = [{
            'id': 'doc1', 'doc_type': 'Implementation Status and Results Report',
            'date': '2023-03', 'url': '', 'pdfurl': 'https://x.pdf', 'txturl': 'https://x.txt',
        }]
        result = fetch_and_save_isrs('P999999', tmp_path, delay=0)

    assert len(result) == 1
    assert result[0]['status'] == 'no_content'
    assert not (tmp_path / 'P999999_ISR_2023-03.txt').exists()


def test_fetch_and_save_isrs_no_txturl_uses_pdfurl(tmp_path):
    """When txturl is empty string, should go straight to pdfurl."""
    real_text = 'Content from PDF ' * 200

    with patch('utils.fetch_isrs.fetch_isr_metadata') as mock_meta, \
         patch('utils.fetch_isrs._fetch_text_from_txturl') as mock_txt, \
         patch('utils.fetch_isrs._fetch_text_from_pdfurl', return_value=real_text):
        mock_meta.return_value = [{
            'id': 'doc1', 'doc_type': 'Implementation Status and Results Report',
            'date': '2023-03', 'url': '', 'pdfurl': 'https://x.pdf', 'txturl': '',
        }]
        result = fetch_and_save_isrs('P999999', tmp_path, delay=0)

    assert result[0]['status'] == 'saved'
    assert result[0]['source'] == 'pdfurl'
    mock_txt.assert_not_called()
