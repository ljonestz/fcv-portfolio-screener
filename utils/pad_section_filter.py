"""
PAD Section Filter — extracts FCV-relevant sections from World Bank PAD documents.

Design principles:
- Roman numeral sections I–V are always kept (strategic context, PDO, description,
  implementation, risks — all FCV-relevant).
- Roman numeral section VI (Appraisal Summary) is selectively kept:
    KEEP: E (Social), F (Environment), G (World Bank Grievance Redress)
    STRIP: A (Economic), B (Technical), C (Financial Management), D (Procurement)
- Annexes: keep 1, 3, 7; strip all others.
- Front matter (everything before first Roman numeral section) is stripped.
- Trailing back matter (BORROWER COMMENTS, signatures, end-of-document markers)
  is stripped by detecting a logical document end after the last annex.
- Non-PAD doc types (ISR, ICR, RESTRUCTURING, AF, PID, PCN) pass through unchanged.
- If fewer than 5 headers are detected, fall back to returning the full text.

Note on Table of Contents (ToC) handling:
  World Bank PAD PDFs typically begin with a Table of Contents where section headers
  appear as dot-leader lines, e.g.:
      I. STRATEGIC CONTEXT ....................................  7
      A. Country Context ......................................  7
  These lines match the same regex patterns as the real body headers that appear later
  in the document.  To avoid capturing ToC entries instead of real body headers, all
  three regex patterns use [^.] in the title capture group, which prevents matching any
  line whose title portion contains one or more literal periods (the dot-leader pattern).
  Real section-header lines never contain periods in the title text itself.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── doc types that pass through without filtering ────────────────────────────

_PASSTHROUGH_DOC_TYPES = {'ISR', 'ICR', 'RESTRUCTURING', 'AF', 'PID', 'PCN'}

# ─── keep/strip rules ─────────────────────────────────────────────────────────

# Roman numeral sections that are fully kept
_KEEP_ROMAN = {'I', 'II', 'III', 'IV', 'V'}

# Roman numeral sections where we keep only specific lettered subsections
_PARTIAL_ROMAN = {
    'VI': {'E', 'F', 'G'},   # Social, Environment, World Bank GRM
}

# Annexes to keep (by integer number)
_KEEP_ANNEXES = {1, 3, 7}

# Minimum number of detected headers before we attempt filtering
_MIN_HEADERS_FOR_FILTER = 5

# Patterns that signal the end of substantive annex content (back matter)
_RE_BACK_MATTER = re.compile(
    r'^\s*(BORROWER\s+COMMENTS?|ANNEX\s+\d+\s*[:\-]?\s*BORROWER|'
    r'\[END\s+OF\s+DOCUMENT\]|END\s+OF\s+DOCUMENT)',
    re.MULTILINE | re.IGNORECASE,
)

# ─── section detection ────────────────────────────────────────────────────────

# Regex patterns (compiled once at module load)
#
# All three patterns use [^.]+ in the title capture group to exclude dot-leader lines
# from the Table of Contents (e.g. "I. STRATEGIC CONTEXT ..............  7").
# Real body section headers never contain periods in the title text; ToC entries always
# do (the dot leaders).  Without this exclusion the filter captures only the narrow
# gap between adjacent ToC lines (often a single newline), reducing large PADs to
# near-zero content.
_RE_ROMAN = re.compile(
    r'^\s*([IVX]{1,5})\.\s+([A-Z][^.]+?)\s*$',
    re.MULTILINE,
)
_RE_LETTER = re.compile(
    r'^\s*([A-Z])\.\s+([A-Z][^.]+?)\s*$',
    re.MULTILINE,
)
_RE_ANNEX = re.compile(
    r'^\s*Annex\s+(\d+):\s+([^.]+?)\s*$',
    re.MULTILINE | re.IGNORECASE,
)

# Only accept genuine Roman numerals up to XVIII (covers any realistic PAD)
_VALID_ROMAN = {
    'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
    'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII',
}


def detect_sections(text: str) -> list[dict]:
    """
    Detect all section headers in *text* and return them as a sorted list of dicts.

    Each dict has:
        type  : 'roman' | 'letter' | 'annex'
        key   : the section identifier (e.g. 'I', 'A', '1')
        name  : the section title
        start : character position of the match start
        end   : character position of the match end

    When a Roman numeral pattern and a letter pattern match at the same position
    (e.g. "I. STRATEGIC CONTEXT" matches both), the Roman entry is kept and the
    letter duplicate is discarded.
    """
    sections: list[dict] = []
    roman_positions: set[int] = set()

    # Collect Roman numeral sections first
    for m in _RE_ROMAN.finditer(text):
        key = m.group(1)
        if key in _VALID_ROMAN:
            roman_positions.add(m.start())
            sections.append({
                'type': 'roman',
                'key': key,
                'name': m.group(2).strip(),
                'start': m.start(),
                'end': m.end(),
            })

    # Collect lettered subsections, skipping positions already claimed by Roman matches
    for m in _RE_LETTER.finditer(text):
        if m.start() in roman_positions:
            continue  # duplicate — Roman match takes precedence
        sections.append({
            'type': 'letter',
            'key': m.group(1),
            'name': m.group(2).strip(),
            'start': m.start(),
            'end': m.end(),
        })

    # Collect annex headers
    for m in _RE_ANNEX.finditer(text):
        sections.append({
            'type': 'annex',
            'key': m.group(1),          # string digit, e.g. '1'
            'name': m.group(2).strip(),
            'start': m.start(),
            'end': m.end(),
        })

    # Sort by position; stable for same-position ties (shouldn't occur after dedup)
    sections.sort(key=lambda s: s['start'])
    return sections


# ─── back-matter boundary detection ──────────────────────────────────────────

def _find_back_matter_start(text: str) -> int:
    """
    Return the character position where back matter begins (BORROWER COMMENTS,
    [END OF DOCUMENT], etc.), or len(text) if none found.
    """
    m = _RE_BACK_MATTER.search(text)
    return m.start() if m else len(text)


# ─── keep-range computation ───────────────────────────────────────────────────

def _compute_keep_ranges(text: str, sections: list[dict]) -> list[tuple[int, int]]:
    """
    Given the ordered list of detected sections, return a list of (start, end)
    character ranges in *text* that should be included in the filtered output.

    The document end is clipped at the back-matter boundary (BORROWER COMMENTS etc.)
    so trailing non-substantive content is excluded.

    Ranges may be adjacent or overlapping; they are merged before returning.
    """
    n = len(sections)
    doc_end = _find_back_matter_start(text)   # clip everything after this
    raw_ranges: list[tuple[int, int]] = []

    def _body_start(idx: int) -> int:
        """Character position immediately after a section header line."""
        return sections[idx]['end']

    def _section_end(idx: int) -> int:
        """
        Character position where the content of section[idx] ends.

        For roman numeral sections (type == 'roman'), letter subsections are
        children of the roman section and must NOT terminate its range.  We look
        ahead for the next *roman* section or annex header — letter sections
        encountered along the way are skipped.

        For letter and annex sections, any later section boundary terminates the
        range (original behaviour).
        """
        current_start = sections[idx]['start']
        sec_type = sections[idx]['type']

        for j in range(idx + 1, n):
            candidate = sections[j]
            if candidate['start'] <= current_start:
                continue  # shouldn't happen after sort, but guard anyway
            if sec_type == 'roman':
                # Only roman sections or annexes end a roman parent's range
                if candidate['type'] in ('roman', 'annex'):
                    return min(candidate['start'], doc_end)
                # Letter children are skipped — keep looking
            else:
                # For letter / annex sections, first later boundary wins
                return min(candidate['start'], doc_end)
        return doc_end

    # State: are we inside section VI?
    in_vi = False

    for i, sec in enumerate(sections):
        sec_type = sec['type']
        sec_key = sec['key']

        # Skip sections that start at or after the back-matter boundary
        if sec['start'] >= doc_end:
            break

        if sec_type == 'roman':
            if sec_key in _KEEP_ROMAN:
                raw_ranges.append((_body_start(i), _section_end(i)))
                in_vi = False
            elif sec_key in _PARTIAL_ROMAN:
                # Enter section VI — subsections decide individually
                in_vi = True
            else:
                in_vi = False

        elif sec_type == 'letter':
            if in_vi:
                kept_letters = _PARTIAL_ROMAN.get('VI', set())
                if sec_key in kept_letters:
                    # Include from header start (not body_start) so header text is retained
                    raw_ranges.append((sec['start'], _section_end(i)))
            # Letter sections outside VI are subheadings of an already-kept Roman section;
            # their content is already covered by the parent Roman section range.

        elif sec_type == 'annex':
            in_vi = False  # Annexes always reset VI tracking
            annex_num = int(sec_key)
            if annex_num in _KEEP_ANNEXES:
                raw_ranges.append((sec['start'], _section_end(i)))

    return _merge_ranges(raw_ranges)


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or adjacent ranges (sorted by start)."""
    if not ranges:
        return []
    # Filter out inverted ranges (start >= end) that can arise from edge cases
    valid = [(s, e) for s, e in ranges if s < e]
    if not valid:
        return []
    sorted_ranges = sorted(valid)
    merged = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


# ─── public API ───────────────────────────────────────────────────────────────

def filter_pad(
    text: str,
    doc_type: str = 'PAD',
    pid: str = '',
) -> tuple[str, dict]:
    """
    Filter *text* to retain only FCV-relevant sections for PAD documents.

    Parameters
    ----------
    text     : raw document text
    doc_type : document type string (e.g. 'PAD', 'ISR', 'ICR', ...)
    pid      : optional project ID for logging

    Returns
    -------
    (filtered_text, stats_dict)

    stats_dict always contains:
        headers_found   : int
        original_chars  : int
        filtered_chars  : int
        reduction_pct   : float
        status          : 'passthrough' | 'fallback' | 'filtered'
    """
    original_chars = len(text)

    # ── 1. Non-PAD doc types pass through unchanged ──────────────────────────
    normalised_type = (doc_type or 'PAD').strip().upper()
    if normalised_type in _PASSTHROUGH_DOC_TYPES:
        return text, {
            'headers_found': 0,
            'original_chars': original_chars,
            'filtered_chars': original_chars,
            'reduction_pct': 0.0,
            'status': 'passthrough',
        }

    # ── 2. Detect sections ───────────────────────────────────────────────────
    sections = detect_sections(text)
    headers_found = len(sections)

    # ── 3. Fallback if too few headers ───────────────────────────────────────
    if headers_found < _MIN_HEADERS_FOR_FILTER:
        warning = {
            'event': 'pad_filter_fallback',
            'pid': pid,
            'doc_type': doc_type,
            'headers_found': headers_found,
            'reason': 'Fewer than 5 headers detected; returning full text.',
        }
        logger.warning(json.dumps(warning))
        return text, {
            'headers_found': headers_found,
            'original_chars': original_chars,
            'filtered_chars': original_chars,
            'reduction_pct': 0.0,
            'status': 'fallback',
        }

    # ── 3b. Fallback if no roman-numeral headers detected ────────────────────
    #   All headers found may be letter-only (e.g. an unusual PAD format where
    #   Roman numeral section lines were not extracted by the PDF parser, or the
    #   document uses a different header style).  Without roman headers there are
    #   no parent anchors and _compute_keep_ranges would return an empty list,
    #   producing a 100% reduction.  Return full text instead.
    roman_headers = [s for s in sections if s['type'] == 'roman']
    if not roman_headers:
        warning = {
            'event': 'pad_filter_fallback',
            'pid': pid,
            'doc_type': doc_type,
            'headers_found': headers_found,
            'reason': 'No Roman-numeral section headers detected; returning full text.',
        }
        logger.warning(json.dumps(warning))
        return text, {
            'headers_found': headers_found,
            'original_chars': original_chars,
            'filtered_chars': original_chars,
            'reduction_pct': 0.0,
            'status': 'fallback',
        }

    # ── 4. Compute keep ranges and extract ───────────────────────────────────
    keep_ranges = _compute_keep_ranges(text, sections)

    kept_chunks: list[str] = []
    for start, end in keep_ranges:
        chunk = text[start:end].strip()
        if chunk:
            kept_chunks.append(chunk)

    body = '\n\n'.join(kept_chunks)
    filtered_chars = len(body)
    reduction_pct = round(
        (1 - filtered_chars / original_chars) * 100, 1
    ) if original_chars > 0 else 0.0

    header_line = (
        f'[FILTERED: FCV-relevant sections only. '
        f'Original length: {original_chars} chars \u2192 '
        f'Filtered: {filtered_chars} chars ({reduction_pct}% reduction). '
        f'Sections kept: I\u2013V (full), VI E/F/G (social/env/GRM), Annexes 1, 3, 7.]'
    )
    filtered_text = header_line + '\n\n' + body

    stats = {
        'headers_found': headers_found,
        'original_chars': original_chars,
        'filtered_chars': filtered_chars,  # content only, not including the header prefix
        'reduction_pct': reduction_pct,
        'status': 'filtered',
    }
    return filtered_text, stats


# ─── batch / CLI helpers ──────────────────────────────────────────────────────

def run_filter_on_directory(
    country_dir: Path,
    doc_type: str = 'PAD',
    dry_run: bool = False,
    sample: int = 0,
) -> list[dict]:
    """
    Apply filter_pad to all .txt files in <country_dir>/extracted_texts/.

    Parameters
    ----------
    country_dir : path to the country folder (e.g. Path('ethiopia'))
    doc_type    : document type to pass to filter_pad
    dry_run     : if True, do not write output files
    sample      : if > 0, process only the first N files

    Returns
    -------
    List of per-file stats dicts (each includes a 'filename' key).
    """
    source_dir = country_dir / 'extracted_texts'
    output_dir = country_dir / 'extracted_texts_filtered'

    if not source_dir.exists():
        logger.warning(f'Source directory not found: {source_dir}')
        return []

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(source_dir.glob('*.txt'))
    if sample > 0:
        txt_files = txt_files[:sample]

    results: list[dict] = []
    for fpath in txt_files:
        text = fpath.read_text(encoding='utf-8', errors='replace')
        filtered, stats = filter_pad(text, doc_type=doc_type, pid=fpath.stem)
        stats['filename'] = fpath.name
        results.append(stats)

        if not dry_run:
            out_path = output_dir / fpath.name
            out_path.write_text(filtered, encoding='utf-8')

    return results


# ─── CLI entry point ──────────────────────────────────────────────────────────

def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description='Filter PAD documents to FCV-relevant sections.'
    )
    parser.add_argument('country_dir', type=Path, help='Path to country directory')
    parser.add_argument('--doc-type', default='PAD', help='Document type (default: PAD)')
    parser.add_argument('--sample', type=int, default=0, help='Process only first N files')
    parser.add_argument('--dry-run', action='store_true', help='Do not write output files')
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate sections without writing (implies --dry-run)',
    )
    args = parser.parse_args()

    if args.validate:
        args.dry_run = True

    results = run_filter_on_directory(
        country_dir=args.country_dir,
        doc_type=args.doc_type,
        dry_run=args.dry_run,
        sample=args.sample,
    )

    if not results:
        print('No files processed.')
        return

    for r in results:
        print(
            f"{r['filename']:50s}  "
            f"status={r['status']:12s}  "
            f"headers={r['headers_found']:3d}  "
            f"reduction={r['reduction_pct']:5.1f}%"
        )

    total = len(results)
    filtered_count = sum(1 for r in results if r['status'] == 'filtered')
    fallback_count = sum(1 for r in results if r['status'] == 'fallback')
    passthrough_count = sum(1 for r in results if r['status'] == 'passthrough')
    avg_reduction = (
        sum(r['reduction_pct'] for r in results if r['status'] == 'filtered') / filtered_count
        if filtered_count > 0
        else 0.0
    )
    print(
        f'\nSummary: {total} files | '
        f'{filtered_count} filtered (avg {avg_reduction:.1f}% reduction) | '
        f'{fallback_count} fallback | '
        f'{passthrough_count} passthrough'
    )


if __name__ == '__main__':
    _cli()
