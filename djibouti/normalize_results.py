"""
Djibouti FCV Portfolio — Normalize and Merge Screening Results
Date: 2026-03-16

Merges screening_results_batch_1/2/3.json into one canonical JSON file.
Also recalculates gap_matrix_cell from scores to correct any agent errors.

Output: 20260316_djibouti_screening_results_normalized.json
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

BATCH_FILES = [
    SCRIPT_DIR / 'screening_results_batch_1.json',
    SCRIPT_DIR / 'screening_results_batch_2.json',
    SCRIPT_DIR / 'screening_results_batch_3.json',
]

OUTPUT_FILE = SCRIPT_DIR / '20260316_djibouti_screening_results_normalized.json'

# Gap matrix thresholds (must match CLAUDE.md)
SENSITIVITY_THRESHOLD   = 6.0
RESPONSIVENESS_THRESHOLD = 5.5

DIM_MAP_SHORT = {
    'D1': (1, 'FCV Context and Diagnostics', 'Sensitivity'),
    'D2': (2, 'Do No Harm and Conflict Risk', 'Sensitivity'),
    'D3': (3, 'Stakeholder and Political Economy', 'Sensitivity'),
    'D4': (4, 'Objectives and Theory of Change', 'Responsiveness'),
    'D5': (5, 'Design and Targeting', 'Responsiveness'),
    'D6': (6, 'Implementation and Operational Flexibility', 'Responsiveness'),
    'D7': (7, 'Results Framework and Adaptive Management', 'Responsiveness'),
    'D8': (8, 'One WBG Integration', 'Responsiveness'),
}

VALID_RATINGS = {'Substantially Addressed', 'Partially Addressed', 'Not Addressed', 'Strong', 'Not Applicable'}


def score_to_rating(s):
    if s is None:
        return 'Unknown'
    if s >= 7:
        return 'Substantially Addressed'
    if s >= 4:
        return 'Partially Addressed'
    return 'Not Addressed'


def gap_cell(sens, resp):
    """Recalculate gap matrix cell from scores to override any agent errors."""
    high_s = (sens is not None and sens >= SENSITIVITY_THRESHOLD)
    high_r = (resp is not None and resp >= RESPONSIVENESS_THRESHOLD)
    if high_s and high_r:
        return 'High FCV integration'
    if high_s and not high_r:
        return 'Implementation gap'
    if not high_s and high_r:
        return 'Responsive but underanalysed'
    return 'Low FCV integration'


def normalize_dims(dims):
    if isinstance(dims, list):
        result = []
        for d in dims:
            if isinstance(d, dict):
                score = d.get('numeric_score', d.get('score', 0))
                result.append({
                    'id':           d.get('id', 0),
                    'name':         d.get('name', ''),
                    'composite':    d.get('composite', ''),
                    'numeric_score': float(score) if score is not None else 0.0,
                    'rating':       d.get('rating', score_to_rating(score)),
                    'key_quote':    d.get('key_quote', d.get('evidence', '')),
                    'rationale':    d.get('rationale', ''),
                    # NEW — null when no ISR adjustment was made (NOT copied from numeric_score)
                    'pad_score':         d.get('pad_score', None),
                    'adjustment_reason': d.get('adjustment_reason', None),
                })
        return sorted(result, key=lambda x: x['id'])
    return []


def normalize_rf(rf):
    if isinstance(rf, dict):
        result = {}
        for k, v in rf.items():
            key = k.upper()  # normalise RF1/RF2... keys
            if isinstance(v, bool):
                result[key] = v
            elif isinstance(v, dict):
                result[key] = v.get('triggered', False)
            else:
                result[key] = bool(v)
        return result
    return {}


def normalize(r):
    # Extract composite scores
    if 'composites' in r:
        sens = r['composites']['sensitivity']['numeric_score']
        resp = r['composites']['responsiveness']['numeric_score']
        sens_rating = r['composites']['sensitivity'].get('rating', score_to_rating(sens))
        resp_rating = r['composites']['responsiveness'].get('rating', score_to_rating(resp))
        sens_rationale = r['composites']['sensitivity'].get('rationale', '')
        resp_rationale = r['composites']['responsiveness'].get('rationale', '')
    elif 'composite_scores' in r:
        cs = r['composite_scores']
        sens = cs.get('sensitivity_final', cs.get('sensitivity_raw', 0))
        resp = cs.get('responsiveness_final', cs.get('responsiveness_raw', 0))
        sens_rating = score_to_rating(sens)
        resp_rating = score_to_rating(resp)
        sens_rationale = ''
        resp_rationale = ''
    else:
        sens = 0
        resp = 0
        sens_rating = 'Unknown'
        resp_rating = 'Unknown'
        sens_rationale = ''
        resp_rationale = ''

    sens = round(float(sens), 2) if sens is not None else None
    resp = round(float(resp), 2) if resp is not None else None

    # Recalculate gap cell from scores (overrides agent-written value)
    computed_gap = gap_cell(sens, resp)
    agent_gap    = r.get('gap_matrix_cell', '')
    if agent_gap != computed_gap:
        print(f'    Gap correction for {r["project_id"]}: "{agent_gap}" -> "{computed_gap}"')

    return {
        'project_id':           r['project_id'],
        'project_name':         r.get('project_name', ''),
        'doc_type':             r.get('doc_type', ''),
        'instrument_category':  r.get('instrument_category', 'IPF'),
        'approval_year':        r.get('approval_year'),
        'sensitivity_score':    sens,
        'responsiveness_score': resp,
        'sensitivity_rating':   sens_rating,
        'responsiveness_rating': resp_rating,
        'sensitivity_rationale':  sens_rationale,
        'responsiveness_rationale': resp_rationale,
        'red_flags':            normalize_rf(r.get('red_flags', {})),
        'gap_matrix_cell':      computed_gap,
        'key_finding':          r.get('key_finding', ''),
        'dimensions':           normalize_dims(r.get('dimensions', [])),
        # NEW — backward-compatible ISR fields (default to absent/null if not present)
        'isr_count':            r.get('isr_count', 0),
        'score_adjusted':       r.get('score_adjusted', False),
        'trajectory':           r.get('trajectory', None),
    }


def main():
    print('Djibouti FCV Portfolio — Normalizing Screening Results')
    print('=' * 55)

    raw = []
    for f in BATCH_FILES:
        if not f.exists():
            print(f'  WARNING: {f.name} not found — skipping')
            continue
        batch = json.loads(f.read_text(encoding='utf-8'))
        print(f'  {f.name}: {len(batch)} records')
        raw.extend(batch)

    print(f'\nTotal raw records: {len(raw)}')
    print('\nNormalizing...')

    normalized = [normalize(r) for r in raw]

    # Sort by approval year then project_id
    normalized.sort(key=lambda x: (x.get('approval_year') or 0, x['project_id']))

    print(f'\nNormalized: {len(normalized)} records')
    for r in normalized:
        ndim = len(r['dimensions'])
        print(f'  {r["project_id"]}: {ndim} dims, S={r["sensitivity_score"]}, R={r["responsiveness_score"]}, gap={r["gap_matrix_cell"]}')

    OUTPUT_FILE.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nSaved: {OUTPUT_FILE.name}')

    # Summary stats
    scores_s = [r['sensitivity_score'] for r in normalized if r['sensitivity_score']]
    scores_r = [r['responsiveness_score'] for r in normalized if r['responsiveness_score']]
    print(f'\nPortfolio averages:')
    print(f'  Sensitivity:   {sum(scores_s)/len(scores_s):.2f}')
    print(f'  Responsiveness:{sum(scores_r)/len(scores_r):.2f}')

    from collections import Counter
    gap_counts = Counter(r['gap_matrix_cell'] for r in normalized)
    print('\nGap matrix distribution:')
    for cell, n in gap_counts.most_common():
        print(f'  {n:2d}x {cell}')


if __name__ == '__main__':
    main()
