"""
ISR/ICR Fetcher — fetches Implementation Status Reports and Completion Reports
from the WB Documents API for portfolio projects, extracts head+tail text.

Usage (module):
    from utils.fetch_isrs import run_isr_fetch

Usage (CLI):
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

HEAD_CHARS = 10_000
TAIL_CHARS = 5_000

ISR_DOC_TYPES = {
    'Implementation Status and Results Report',
    'Implementation Status Report',
}
ICR_DOC_TYPES = {
    'Implementation Completion Report',
    'Implementation Completion and Results Report',
}
TARGET_DOC_TYPES = ISR_DOC_TYPES | ICR_DOC_TYPES

# NOTE: 'projectid' (no underscore) is correct for the wds endpoint ISR/ICR queries.
# The projects endpoint uses 'project_id' (with underscore).
WDS_ISR_URL = (
    'https://search.worldbank.org/api/v2/wds'
    '?format=json&projectid={pid}'
    '&docty_exact=Implementation+Status+and+Results+Report'
    '&fl=id,docdt,docty,url,pdfurl,txturl&rows=50'
)
WDS_ICR_URL = (
    'https://search.worldbank.org/api/v2/wds'
    '?format=json&projectid={pid}'
    '&docty_exact=Implementation+Completion+Report'
    '&fl=id,docdt,docty,url,pdfurl,txturl&rows=10'
)


def _make_ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


_SSL_CTX = _make_ssl_ctx()


def parse_isr_date(raw_date: str) -> str:
    """Normalise a WB API date string to 'YYYY-MM' format."""
    cleaned = raw_date.replace('/', '').replace('-', '')
    m = re.match(r'(\d{4})(\d{2})\d{2}', cleaned)
    if m:
        return f'{m.group(1)}-{m.group(2)}'
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
    """Head+tail extraction. Short documents returned in full."""
    cap = head_chars + tail_chars
    if len(text) <= cap:
        return text
    head = text[:head_chars]
    tail = text[max(head_chars, len(text) - tail_chars):]
    return head + '\n\n[...]\n\n' + tail


def fetch_isr_metadata(pid: str) -> list[dict]:
    """
    Query WB Documents API for ISRs and ICRs for a given project ID.
    Returns list of dicts with keys: id, doc_type, date, url, pdfurl, txturl.
    """
    results = []
    for url_template in (WDS_ISR_URL, WDS_ICR_URL):
        url = url_template.format(pid=pid)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=30) as r:
                data = json.loads(r.read())
            for doc in data.get('documents', {}).values():
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
                    'pdfurl': doc.get('pdfurl', ''),
                    'txturl': doc.get('txturl', ''),
                })
        except Exception as e:
            print(f'  Warning: API error for {pid}: {e}')

    # Deduplicate by document ID (same doc cannot appear under both ISR and ICR queries)
    seen_ids: set[str] = set()
    deduped = []
    for doc in results:
        doc_id = doc['id']
        if doc_id and doc_id not in seen_ids:
            seen_ids.add(doc_id)
            deduped.append(doc)
        elif not doc_id:
            deduped.append(doc)

    deduped.sort(key=lambda d: d['date'])
    return deduped


def _fetch_text_from_txturl(txturl: str) -> Optional[str]:
    """Download pre-extracted text from the WB txturl endpoint."""
    req = urllib.request.Request(txturl, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=_SSL_CTX, timeout=90) as r:
        text = r.read().decode('utf-8', errors='replace')
    # Reject stub/error responses (real ISR text is typically 5k+ chars)
    if len(text) < 500:
        return None
    return text


def _fetch_text_from_pdfurl(pdfurl: str) -> Optional[str]:
    """Download PDF from pdfurl and extract text via PyMuPDF."""
    req = urllib.request.Request(pdfurl, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=_SSL_CTX, timeout=90) as r:
        pdf_bytes = r.read()
    fitz_doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    text = ''.join(page.get_text() for page in fitz_doc)
    fitz_doc.close()
    if len(text) < 500:
        return None
    return text


def fetch_and_save_isrs(pid: str, out_dir: Path, delay: float = 0.3) -> list[dict]:
    """Fetch all ISRs/ICRs for a project, extract text, save to out_dir.

    Uses a fallback chain: txturl (pre-extracted text) → pdfurl (PDF + PyMuPDF) → skip.
    """
    metadata = fetch_isr_metadata(pid)
    saved = []

    for doc in metadata:
        filename = build_isr_filename(pid, doc['doc_type'], doc['date'])
        out_path = out_dir / filename

        if out_path.exists():
            print(f'  {filename}: already exists, skipping')
            saved.append({**doc, 'filename': filename, 'status': 'skipped'})
            continue

        text = None
        source = None

        # Fallback 1: txturl (pre-extracted plain text — best quality)
        if doc.get('txturl'):
            try:
                text = _fetch_text_from_txturl(doc['txturl'])
                if text:
                    source = 'txturl'
            except Exception:
                pass

        # Fallback 2: pdfurl (direct PDF binary → PyMuPDF extraction)
        if text is None and doc.get('pdfurl'):
            try:
                text = _fetch_text_from_pdfurl(doc['pdfurl'])
                if text:
                    source = 'pdfurl'
            except Exception:
                pass

        # Fallback 3: skip with warning
        if text is None:
            print(f'  {filename}: no accessible content (txturl/pdfurl both failed), skipping')
            saved.append({**doc, 'filename': filename, 'status': 'no_content'})
            continue

        extracted = extract_isr_text(text)
        out_path.write_text(extracted, encoding='utf-8')
        print(f'  {filename}: saved ({len(extracted):,} chars) [from {source}]')
        saved.append({**doc, 'filename': filename, 'status': 'saved', 'source': source})
        time.sleep(delay)

    return saved


def run_isr_fetch(country_dir: Path, delay: float = 0.3) -> dict:
    """
    Fetch ISRs/ICRs for all projects in <country_dir>/screening_targets.json.
    Saves to <country_dir>/extracted_texts_isr/.
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


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fetch ISR/ICR documents for portfolio projects')
    parser.add_argument('country_dir', help='Path to country directory (e.g. djibouti)')
    parser.add_argument('--delay', type=float, default=0.3)
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
