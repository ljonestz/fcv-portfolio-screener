"""
Ethiopia FCV Portfolio — Data Collection Script (Steps 1–3)
Date: 2026-03-16

Steps performed:
  1. Fetch project portfolio from WB Projects API (country code: ET)
  2. Filter to IPF, DPF, P4R instruments, approval years 2015–2024
  3. Fetch best-available project document (PAD > PD > ICR > PP > CN)
  4. Extract PDF text using PyMuPDF (fitz) — head+tail approach (50k+20k chars)

Outputs (written to this script's directory):
  - filtered_ethiopia_portfolio.json   — project metadata
  - screening_targets.json             — projects + doc URLs ready for screening
  - extracted_texts/<PID>.txt          — raw PDF text per project

Notes:
  - SSL verification disabled (corporate proxy)
  - Use fitz (PyMuPDF), NOT pdfplumber
  - Head+tail extraction captures key sections while staying within ~70k chars per project
"""

import json
import ssl
import time
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

try:
    import fitz  # PyMuPDF
except ImportError:
    raise SystemExit("PyMuPDF not found. Run: pip install PyMuPDF")

# ─── Configuration ─────────────────────────────────────────────────────────────

COUNTRY_CODE   = 'ET'
COUNTRY_SLUG   = 'ethiopia'
START_YEAR     = 2015
END_YEAR       = 2024
HEAD_CHARS     = 50_000   # ~30–35 pages: cover, SORT risk table, context, PDO, ToC
TAIL_CHARS     = 20_000   # ~12–15 pages: results framework, risk annexes, safeguards

SCRIPT_DIR = Path(__file__).parent
PORTFOLIO_FILE       = SCRIPT_DIR / 'filtered_ethiopia_portfolio.json'
SCREENING_FILE       = SCRIPT_DIR / 'screening_targets.json'
EXTRACTED_TEXTS_DIR  = SCRIPT_DIR / 'extracted_texts'

# Instrument categories to include
INCLUDE_INSTRUMENTS = {'IPF', 'DPF', 'P4R'}

# Document type priority (highest = most preferred)
DOC_TYPE_PRIORITY = {
    'Project Appraisal Document': 10,
    'Program Document': 9,
    'Program-for-Results Appraisal Document': 9,  # P4R equivalent
    'PforR Appraisal Document': 9,
    'Implementation Completion Report': 7,
    'Implementation Completion and Results Report': 7,
    'Implementation Status and Results Report': 6,  # ISR for ongoing projects
    'Project Paper': 5,
    'Restructuring Paper': 4,
    'Concept Note': 2,
    'Program-for-Results Concept Note': 2,
}

# ─── SSL Context (corporate proxy) ─────────────────────────────────────────────

def make_ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

SSL_CTX = make_ssl_ctx()


def fetch_json(url: str, retries: int = 3) -> dict:
    """Fetch URL and return parsed JSON. Retries on transient errors."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=60) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            if attempt < retries - 1:
                print(f'    Retry {attempt + 1}/{retries} for {url[:80]}... ({e})')
                time.sleep(2)
            else:
                raise
    return {}


# ─── Step 1: Fetch Portfolio ────────────────────────────────────────────────────

def classify_instrument(lendinginstr: str, lendinginstrtype: str) -> str:
    """Map WB instrument fields to IPF / DPF / P4R / Other."""
    instr  = (lendinginstr or '').lower()
    itype  = (lendinginstrtype or '').lower()

    if 'program-for-results' in instr or 'pfr' in itype or 'pforr' in itype:
        return 'P4R'
    if 'investment' in instr or itype == 'in':
        return 'IPF'
    if 'development policy' in instr or itype in ('dl', 'dpl', 'dpc'):
        return 'DPF'
    return 'Other'


def fetch_portfolio() -> list:
    """Fetch all WB projects for Ethiopia and filter to target instruments/years."""
    print(f'\nStep 1: Fetching portfolio for {COUNTRY_CODE} ({COUNTRY_SLUG.title()})...')

    fields = 'id,project_name,status,boardapprovaldate,closingdate,lendinginstr,lendinginstrtype,sector1,sector2,theme1,totalcommamt,url,regionname,countryname,prodline'
    base_url = (
        f'https://search.worldbank.org/api/v2/projects'
        f'?format=json&countrycode={COUNTRY_CODE}&rows=250&source=IBRD'
        f'&fl={fields}'
    )

    data = fetch_json(base_url)
    projects_raw = list(data.get('projects', {}).values())
    print(f'  Total projects returned by API: {len(projects_raw)}')

    # Ethiopia's portfolio is large — check if pagination is needed
    total = int(data.get('total', 0))
    if total > 250:
        print(f'  Note: API reports {total} total projects. Fetching additional pages...')
        start = 250
        while start < total:
            page_url = base_url + f'&start={start}'
            page_data = fetch_json(page_url)
            page_projects = list(page_data.get('projects', {}).values())
            projects_raw.extend(page_projects)
            print(f'    Page starting at {start}: {len(page_projects)} additional projects')
            start += 250
            time.sleep(0.5)
        print(f'  Total after pagination (before dedup): {len(projects_raw)} projects')

    # Deduplicate by project ID (pagination can return overlapping records)
    seen_ids = set()
    unique_raw = []
    for p in projects_raw:
        pid = p.get('id')
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            unique_raw.append(p)
    if len(unique_raw) < len(projects_raw):
        print(f'  Deduplicated: {len(projects_raw)} -> {len(unique_raw)} unique projects')
    projects_raw = unique_raw

    filtered = []
    for p in projects_raw:
        # Parse approval year
        date_str = p.get('boardapprovaldate', '')
        if not date_str:
            continue
        try:
            year = int(date_str[:4])
        except (ValueError, TypeError):
            continue
        if not (START_YEAR <= year <= END_YEAR):
            continue

        # Classify instrument
        category = classify_instrument(
            p.get('lendinginstr', ''),
            p.get('lendinginstrtype', '')
        )
        if category not in INCLUDE_INSTRUMENTS:
            continue

        p['_instrument_category'] = category
        p['_approval_year'] = year
        filtered.append(p)

    # Sort by approval date
    filtered.sort(key=lambda x: x.get('boardapprovaldate', ''))
    print(f'  After filter ({"/".join(sorted(INCLUDE_INSTRUMENTS))}, {START_YEAR}–{END_YEAR}): {len(filtered)} projects')

    # Print summary
    instr_counts = {}
    for p in filtered:
        cat = p['_instrument_category']
        instr_counts[cat] = instr_counts.get(cat, 0) + 1
    for cat, n in sorted(instr_counts.items()):
        print(f'    {cat}: {n}')

    with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)
    print(f'  Saved: {PORTFOLIO_FILE.name}')

    return filtered


# ─── Step 2: Fetch Project Documents ───────────────────────────────────────────

def _title_words(title: str) -> set:
    """
    Tokenise a title into a set of meaningful words.
    Strips generic WB boilerplate and function words.
    """
    import re
    words = re.sub(r'[^\w\s]', ' ', (title or '').lower()).split()
    stopwords = {
        'the','a','an','and','or','of','in','for','to','at','on','by','with',
        'de','du','la','le','les','et','des','un','une','au','aux',
        'project','programme','program','additional','financing','af',
        'second','third','fourth','phase','initiative',
        'disclosable','restructuring','paper','report','appraisal',
        'implementation','status','results','completion','document',
    }
    return {w for w in words if len(w) > 2 and w not in stopwords}


def fetch_all_ethiopia_pads() -> list:
    """
    The WB Documents API does not reliably link PADs to project IDs.
    Fetch all English Ethiopia PADs via text search.
    Returns list of doc dicts with _docty_priority set.
    """
    results = []
    for docty in ['Project+Appraisal+Document', 'Program+Document',
                  'PforR+Appraisal+Document']:
        url = (
            f'https://search.worldbank.org/api/v2/wds'
            f'?format=json&qterm=Ethiopia&docty_exact={docty}'
            f'&rows=200&fl=id,docty,display_title,pdfurl,docdt,lang'
        )
        try:
            data = fetch_json(url)
            docs = list(data.get('documents', {}).values())
            # Check if we need to paginate (Ethiopia has many documents)
            doc_total = int(data.get('total', 0))
            if doc_total > 200:
                start = 200
                while start < min(doc_total, 800):  # cap at 800 per doctype
                    paged_url = url + f'&start={start}'
                    paged_data = fetch_json(paged_url)
                    paged_docs = list(paged_data.get('documents', {}).values())
                    docs.extend(paged_docs)
                    start += 200
                    time.sleep(0.3)
            for d in docs:
                if d.get('pdfurl') and d.get('lang', 'English') == 'English':
                    d['_docty_priority'] = DOC_TYPE_PRIORITY.get(d.get('docty', ''), 0)
                    results.append(d)
        except Exception as e:
            print(f'    Warning: failed to fetch {docty}: {e}')
        time.sleep(0.3)

    # De-duplicate by pdfurl
    seen = set()
    unique = []
    for d in results:
        url = d.get('pdfurl', '')
        if url not in seen:
            seen.add(url)
            unique.append(d)

    print(f'    Pre-fetched {len(unique)} unique Ethiopia PADs')
    return unique


def match_pad_to_project(project_name: str, pad_candidates: list) -> dict | None:
    """
    Match a project to a PAD using bidirectional recall.
    Accepts a match if max(recall_proj, recall_doc) >= 0.55 AND jaccard >= 0.18.
    Bidirectional recall handles cases where the project name was later updated
    (e.g. COVID-19 AF extension adds new words that dilute recall against the original PAD title).
    """
    proj_words = _title_words(project_name)
    if len(proj_words) < 2:
        return None

    best_score = 0.0
    best_doc   = None

    for d in pad_candidates:
        doc_words = _title_words(d.get('display_title', ''))
        if len(doc_words) < 2:
            continue
        overlap       = len(proj_words & doc_words)
        recall_proj   = overlap / len(proj_words)
        recall_doc    = overlap / len(doc_words)
        jaccard       = overlap / len(proj_words | doc_words)
        bi_recall     = max(recall_proj, recall_doc)
        combined      = (bi_recall + jaccard) / 2

        if bi_recall >= 0.55 and jaccard >= 0.18 and combined > best_score:
            best_score = combined
            best_doc   = d

    return best_doc


def get_best_direct_doc(pid: str) -> dict | None:
    """
    Fetch best document via direct project_id lookup.
    Validates returned docs are Ethiopia-specific (title must contain 'ethiopia').
    """
    url = (
        f'https://search.worldbank.org/api/v2/wds'
        f'?format=json&project_id={pid}&rows=100'
        f'&fl=id,docty,docdt,display_title,pdfurl,lang,disclstat'
    )
    try:
        data = fetch_json(url)
    except Exception as e:
        print(f'           Warning: direct lookup error: {e}')
        return None

    docs = list(data.get('documents', {}).values())
    candidates = []
    for d in docs:
        if not d.get('pdfurl'):
            continue
        if d.get('lang', 'English') != 'English':
            continue
        # Validate the document is actually about Ethiopia
        title_lower = (d.get('display_title', '') or '').lower()
        if 'ethiopia' not in title_lower and 'ethiop' not in title_lower:
            continue
        priority = DOC_TYPE_PRIORITY.get(d.get('docty', ''), 0)
        if priority > 0:
            d['_docty_priority'] = priority
            candidates.append(d)

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x.get('_docty_priority', 0), x.get('docdt', '')), reverse=True)
    return candidates[0]


def get_keyword_doc(project_name: str) -> dict | None:
    """
    Last-resort fallback: search WB Documents by project name keywords + country=ET.
    Accepts Project Paper, ICR, or ISR if title is Ethiopia-specific.
    """
    words = _title_words(project_name)
    # Use the most distinctive 3-4 words (longer words first)
    key_words = sorted(words, key=len, reverse=True)[:4]
    if len(key_words) < 2:
        return None

    qterm = '+'.join(key_words)
    url = (
        f'https://search.worldbank.org/api/v2/wds'
        f'?format=json&qterm={qterm}&countrycode_exact=ET&rows=10'
        f'&fl=id,docty,docdt,display_title,pdfurl,lang'
    )
    try:
        data = fetch_json(url)
    except Exception as e:
        return None

    docs = list(data.get('documents', {}).values())
    candidates = []
    for d in docs:
        if not d.get('pdfurl'):
            continue
        if d.get('lang', 'English') != 'English':
            continue
        title_lower = (d.get('display_title', '') or '').lower()
        if 'ethiopia' not in title_lower and 'ethiop' not in title_lower:
            continue
        priority = DOC_TYPE_PRIORITY.get(d.get('docty', ''), 0)
        if priority > 0:
            d['_docty_priority'] = priority
            candidates.append(d)

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x.get('_docty_priority', 0), x.get('docdt', '')), reverse=True)
    return candidates[0]


def fetch_documents(portfolio: list) -> tuple[list, list]:
    """
    For each project, find the best document:
      1. PAD via title-matching against pre-fetched Ethiopia PADs (strict ≥55% recall)
      2. ISR or Project Paper via direct project_id lookup (Ethiopia-validated)
      3. Keyword fallback search with country=ET
    Returns (targets, excluded).
    """
    print(f'\nStep 2: Fetching document URLs for {len(portfolio)} projects...')

    print('  Pre-fetching all Ethiopia PADs from WB Documents API...')
    all_pads = fetch_all_ethiopia_pads()

    targets  = []
    excluded = []

    for i, p in enumerate(portfolio, 1):
        pid  = p['id']
        name = p.get('project_name', '')
        print(f'  [{i:03d}/{len(portfolio)}] {pid}: {name[:50]}')

        doc    = None
        method = ''

        # Method 1: PAD title-match
        pad_match = match_pad_to_project(name, all_pads)
        if pad_match:
            doc    = pad_match
            method = 'PAD-match'

        # Method 2: direct project_id lookup, Ethiopia-validated
        if doc is None:
            doc = get_best_direct_doc(pid)
            if doc:
                method = 'direct'

        # Method 3: keyword search with country=ET filter
        if doc is None:
            doc = get_keyword_doc(name)
            if doc:
                method = 'keyword'

        if doc is None:
            print(f'           -> No valid document -- EXCLUDED')
            excluded.append({'project_id': pid, 'project_name': name, 'reason': 'no_document'})
            continue

        docty = doc.get('docty', 'Unknown')
        title = (doc.get('display_title', '') or '').replace('\n', ' ').replace('  ', ' ').strip()
        print(f'           -> [{method}] {docty}: {title[:55]}')

        targets.append({
            'project_id':          pid,
            'project_name':        name,
            'doc_type':            docty,
            'doc_id':              doc.get('id', ''),
            'doc_title':           title,
            'pdf_url':             doc.get('pdfurl', ''),
            'instrument_category': p['_instrument_category'],
            'approval_year':       p['_approval_year'],
            'status':              p.get('status', ''),
            'sector':              (p.get('sector1') or {}).get('Name', '') if isinstance(p.get('sector1'), dict) else '',
            'total_commitment':    p.get('totalcommamt', ''),
        })

        time.sleep(0.2)

    # Deduplicate targets by project_id (safety check)
    seen_pids = set()
    unique_targets = []
    for t in targets:
        if t['project_id'] not in seen_pids:
            seen_pids.add(t['project_id'])
            unique_targets.append(t)
    if len(unique_targets) < len(targets):
        print(f'  Target dedup: {len(targets)} -> {len(unique_targets)}')
    targets = unique_targets

    print(f'\n  Documents found: {len(targets)}, Excluded: {len(excluded)}')
    if excluded:
        # Deduplicate excluded list too
        seen_excl = set()
        unique_excl = [e for e in excluded if e['project_id'] not in seen_excl and not seen_excl.add(e['project_id'])]
        excluded = unique_excl
        print('  Excluded projects:')
        for e in excluded:
            print(f'    {e["project_id"]}: {e["project_name"]}')

    with open(SCREENING_FILE, 'w', encoding='utf-8') as f:
        json.dump(targets, f, indent=2, ensure_ascii=False)
    print(f'  Saved: {SCREENING_FILE.name}')

    return targets, excluded


# ─── Step 3: Extract PDF Text (head + tail) ─────────────────────────────────────

def extract_pdf_text(url: str, head_chars: int = HEAD_CHARS, tail_chars: int = TAIL_CHARS) -> str:
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


def extract_all_texts(targets: list) -> dict:
    """Extract text for all screening targets. Returns {project_id: text}."""
    print(f'\nStep 3: Extracting PDF text for {len(targets)} projects...')
    EXTRACTED_TEXTS_DIR.mkdir(exist_ok=True)

    results = {}
    failed  = []

    for i, t in enumerate(targets, 1):
        pid      = t['project_id']
        pdf_url  = t['pdf_url']
        out_file = EXTRACTED_TEXTS_DIR / f'{pid}.txt'

        # Skip if already extracted
        if out_file.exists():
            text = out_file.read_text(encoding='utf-8')
            results[pid] = text
            print(f'  [{i:03d}/{len(targets)}] {pid}: cached ({len(text):,} chars)')
            continue

        print(f'  [{i:03d}/{len(targets)}] {pid}: {t["doc_type"][:40]}...', end='', flush=True)
        try:
            text = extract_pdf_text(pdf_url)
            out_file.write_text(text, encoding='utf-8')
            results[pid] = text
            sep_present = '[... procurement' in text
            print(f' {len(text):,} chars{"  [head+tail]" if sep_present else "  [full]"}')
        except Exception as e:
            print(f' FAILED: {e}')
            failed.append({'project_id': pid, 'error': str(e)})
            results[pid] = ''

        time.sleep(0.5)

    print(f'\n  Extracted: {len(results) - len(failed)}, Failed: {len(failed)}')
    if failed:
        print('  Failed extractions:')
        for f in failed:
            print(f'    {f["project_id"]}: {f["error"]}')

    return results


# ─── Main ───────────────────────────────────────────────────────────────────────

def main():
    print('=' * 60)
    print(f'Ethiopia FCV Portfolio — Data Collection')
    print(f'Country: {COUNTRY_SLUG.title()} ({COUNTRY_CODE})')
    print(f'Period:  {START_YEAR}–{END_YEAR}')
    print(f'Instruments: {", ".join(sorted(INCLUDE_INSTRUMENTS))}')
    print(f'Extraction: head {HEAD_CHARS:,} + tail {TAIL_CHARS:,} chars per PDF')
    print(f'Run date: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 60)

    portfolio = fetch_portfolio()
    if not portfolio:
        print('\nNo projects found. Check country code and date range.')
        return

    targets, excluded = fetch_documents(portfolio)
    if not targets:
        print('\nNo screeable projects found.')
        return

    texts = extract_all_texts(targets)

    # Summary
    print('\n' + '=' * 60)
    print('Data Collection Complete')
    print(f'  Portfolio projects:  {len(portfolio)}')
    print(f'  Screening targets:   {len(targets)}')
    print(f'  Excluded (no doc):   {len(excluded)}')
    print(f'  Text extracted:      {sum(1 for v in texts.values() if v)} / {len(targets)}')
    print(f'\nOutputs:')
    print(f'  {PORTFOLIO_FILE.name}')
    print(f'  {SCREENING_FILE.name}')
    print(f'  extracted_texts/<PID>.txt')
    print('\nNext step: Run FCV screening agents (see CLAUDE.md Step 4)')


if __name__ == '__main__':
    main()
