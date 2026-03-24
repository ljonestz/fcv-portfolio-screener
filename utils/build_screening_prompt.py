"""
Screening prompt builder — assembles the agent prompt for FCV screening.

Supports PAD-only mode (existing behaviour) and PAD + ISR combined mode.

Usage:
    from utils.build_screening_prompt import build_prompt

    # PAD-only (existing behaviour)
    prompt = build_prompt(pid='P148447', project_name='Ethiopia Roads',
                          doc_type='PAD', instrument='IPF', year=2016,
                          pad_text=filtered_pad_text, isr_texts=[],
                          output_path='ethiopia/screening_results_P148447.json')

    # PAD + ISRs
    prompt = build_prompt(..., isr_texts=[('ISR', '2020-03', isr_text)])
"""

from pathlib import Path


def build_prompt(
    pid: str,
    project_name: str,
    doc_type: str,
    instrument: str,
    year: int,
    pad_text: str,
    isr_texts: list,  # list of (doc_type_label, date, text) tuples
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
        isr_texts: List of (doc_type_label, date, text) for supplementary docs.
                   Empty list -> PAD-only mode (current behaviour).
        output_path: Path where agent should save its JSON result.
                     If empty, agent outputs to stdout.

    Returns:
        Complete prompt string ready to pass to a screener agent.
    """
    has_isrs = len(isr_texts) > 0

    # -- Metadata header ------------------------------------------------------
    lines = [
        'Screen this project using the FCV screener skill.',
        f'Project ID: {pid} | Name: {project_name}',
        f'Document type: {doc_type} | Instrument: {instrument} | Year: {year}',
    ]
    if output_path:
        lines.append(f'\nSave result to: {output_path}')

    lines += [
        '',
        'Output format constraints (strictly enforced):',
        '- key_quote: max 250 chars per dimension',
        '- rationale per dimension: max 3 sentences / 200 words',
        '- key_finding: max 2 sentences / 100 words',
        '- Output: a single JSON object only. No preamble before the JSON.',
    ]

    # -- ISR adjustment instructions (only when ISRs present) -----------------
    if has_isrs:
        isr_count = len(isr_texts)
        lines += [
            '',
            f'ISR ADJUSTMENT INSTRUCTIONS ({isr_count} supplementary document(s) provided):',
            '1. Score all 8 dimensions using the PRIMARY DOCUMENT (PAD) as primary evidence.',
            '2. Review each SUPPLEMENTARY DOCUMENT in chronological order.',
            '3. For any dimension where ISR/ICR evidence materially changes your assessment,',
            '   adjust that dimension\'s score. Examples of material changes:',
            '   - Security deterioration documented with no adaptive management response',
            '   - Course correction that demonstrably improved FCV sensitivity',
            '   - Systematic GRM failure evidenced across multiple ISRs',
            '4. For each adjusted dimension, record the original pad_score and adjustment_reason.',
            '5. Add a trajectory field (2-3 sentences): what did the ISRs reveal about',
            '   implementation-phase FCV sensitivity?',
            '6. Set score_adjusted: true if any dimension was changed; false otherwise.',
            f'7. Set isr_count: {isr_count}.',
        ]

    # -- Primary document -----------------------------------------------------
    lines += [
        '',
        '---',
        f'PRIMARY DOCUMENT ({doc_type}):',
        '',
        pad_text,
    ]

    # -- Supplementary documents ----------------------------------------------
    if has_isrs:
        lines += [
            '',
            '---',
            f'SUPPLEMENTARY DOCUMENTS ({len(isr_texts)} ISR/ICR, chronological order):',
        ]
        for i, (dtype, date, text) in enumerate(isr_texts, 1):
            lines += [
                '',
                f'[Document {i}: {dtype} — {date}]',
                '',
                text,
            ]

    return '\n'.join(lines)
