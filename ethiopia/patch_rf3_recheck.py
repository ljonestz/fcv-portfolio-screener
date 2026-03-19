"""
Ethiopia RF3 Recheck — Patch Script
Date: 2026-03-18

Reads 20 recheck JSON files (one per project) and patches the normalized results:
- Updates red_flags for all 5 flags (RF1–RF5)
- Updates sensitivity_score, responsiveness_score, and dimensions from the recheck
- Backs up the original normalized JSON before writing

Usage: python patch_rf3_recheck.py
Run from: ethiopia/ folder or anywhere (uses Path(__file__).parent)
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent

NORMALIZED_FILE = SCRIPT_DIR / '20260316_ethiopia_screening_results_normalized.json'
BACKUP_FILE     = SCRIPT_DIR / f'20260316_ethiopia_screening_results_normalized.BACKUP_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

# All 20 projects that had RF3=true in the original screening
RECHECK_PIDS = [
    'P151712', 'P148447', 'P151847', 'P158770', 'P159382',
    'P160279', 'P161373', 'P163350', 'P163438', 'P160395',
    'P168566', 'P162607', 'P167794', 'P169079', 'P174874',
    'P171034', 'P175045', 'P175853', 'P178821', 'P176255',
]

SENSITIVITY_THRESHOLD    = 6.0
RESPONSIVENESS_THRESHOLD = 5.5


def score_to_rating(s):
    if s is None:
        return 'Unknown'
    if s >= 7:
        return 'Substantially Addressed'
    if s >= 4:
        return 'Partially Addressed'
    return 'Not Addressed'


def gap_cell(sens, resp):
    high_s = (sens is not None and sens >= SENSITIVITY_THRESHOLD)
    high_r = (resp is not None and resp >= RESPONSIVENESS_THRESHOLD)
    if high_s and high_r:
        return 'High FCV integration'
    if high_s and not high_r:
        return 'Implementation gap'
    if not high_s and high_r:
        return 'Responsive but underanalysed'
    return 'Low FCV integration'


def normalize_rf(rf):
    """Extract boolean values from red_flags dict, handling both bool and dict formats."""
    if not isinstance(rf, dict):
        return {}
    result = {}
    for k, v in rf.items():
        key = k.upper()
        if isinstance(v, bool):
            result[key] = v
        elif isinstance(v, dict):
            result[key] = v.get('triggered', False)
        else:
            result[key] = bool(v)
    return result


def normalize_dims(dims):
    if not isinstance(dims, list):
        return []
    result = []
    for d in dims:
        if isinstance(d, dict):
            score = d.get('numeric_score', d.get('score', 0))
            result.append({
                'id':            d.get('id', d.get('dimension_id', 0)),
                'name':          d.get('name', ''),
                'composite':     d.get('composite', ''),
                'numeric_score': float(score) if score is not None else 0.0,
                'rating':        d.get('rating', score_to_rating(score)),
                'key_quote':     d.get('key_quote', d.get('evidence', '')),
                'rationale':     d.get('rationale', ''),
            })
    return sorted(result, key=lambda x: str(x.get('id', '')))


def load_recheck(pid: str):
    path = SCRIPT_DIR / f'screening_results_{pid}_rf3recheck.json'
    if not path.exists():
        print(f'  WARNING: {path.name} not found -- skipping {pid}')
        return None
    raw = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(raw, list):
        raw = raw[0]
    return raw


def extract_scores(recheck: dict):
    """Pull sensitivity and responsiveness scores from any schema variant."""
    if 'composites' in recheck:
        s = recheck['composites']
        sens_key = 'sensitivity' if 'sensitivity' in s else list(s.keys())[0]
        resp_key = 'responsiveness' if 'responsiveness' in s else list(s.keys())[1]
        sens = s[sens_key]['numeric_score']
        resp = s[resp_key]['numeric_score']
    elif 'sensitivity_score' in recheck:
        sens = recheck['sensitivity_score']
        resp = recheck['responsiveness_score']
    elif 'composite_scores' in recheck:
        cs = recheck['composite_scores']
        sens = cs.get('sensitivity_final', cs.get('sensitivity_raw'))
        resp = cs.get('responsiveness_final', cs.get('responsiveness_raw'))
    else:
        return None, None
    return (round(float(sens), 2) if sens is not None else None,
            round(float(resp), 2) if resp is not None else None)


def main():
    print('Ethiopia RF3 Recheck -- Patching Normalized Results')
    print('=' * 52)

    normalized = json.loads(NORMALIZED_FILE.read_text(encoding='utf-8'))
    print(f'Loaded {len(normalized)} projects from {NORMALIZED_FILE.name}')

    shutil.copy2(NORMALIZED_FILE, BACKUP_FILE)
    print(f'Backup saved: {BACKUP_FILE.name}')

    index = {p['project_id']: i for i, p in enumerate(normalized)}

    changed = 0
    for pid in RECHECK_PIDS:
        recheck = load_recheck(pid)
        if recheck is None:
            continue

        if pid not in index:
            print(f'  WARNING: {pid} not found in normalized results -- skipping')
            continue

        i = index[pid]
        orig = normalized[i]
        print(f'\n  {pid} -- {orig["project_name"][:55]}')

        # --- Red flags ---
        new_rf = normalize_rf(recheck.get('red_flags', {}))
        old_rf = orig.get('red_flags', {})
        for flag in ['RF1', 'RF2', 'RF3', 'RF4', 'RF5']:
            old_val = old_rf.get(flag, False)
            new_val = new_rf.get(flag, False)
            marker = ' <-- CHANGED' if old_val != new_val else ''
            print(f'    {flag}: {old_val} -> {new_val}{marker}')

        # --- Scores ---
        new_sens, new_resp = extract_scores(recheck)
        if new_sens is not None:
            old_sens = orig.get('sensitivity_score')
            old_resp = orig.get('responsiveness_score')
            print(f'    Sensitivity:    {old_sens} -> {new_sens}')
            print(f'    Responsiveness: {old_resp} -> {new_resp}')

        # --- Dimensions ---
        new_dims = normalize_dims(recheck.get('dimensions', []))

        # --- Apply patches ---
        merged_rf = dict(old_rf)
        merged_rf.update(new_rf)
        normalized[i]['red_flags'] = merged_rf

        if new_sens is not None:
            normalized[i]['sensitivity_score']     = new_sens
            normalized[i]['responsiveness_score']  = new_resp
            normalized[i]['sensitivity_rating']    = score_to_rating(new_sens)
            normalized[i]['responsiveness_rating'] = score_to_rating(new_resp)
            normalized[i]['gap_matrix_cell']       = gap_cell(new_sens, new_resp)

        if new_dims:
            normalized[i]['dimensions'] = new_dims

        if recheck.get('key_finding'):
            normalized[i]['key_finding'] = recheck['key_finding']

        changed += 1

    print(f'\nPatched {changed} projects.')

    NORMALIZED_FILE.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Saved: {NORMALIZED_FILE.name}')

    # Post-patch summary
    rf3_count  = sum(1 for p in normalized if p.get('red_flags', {}).get('RF3', False))
    any_rf_count = sum(1 for p in normalized if any(v for v in p.get('red_flags', {}).values()))
    for flag in ['RF1', 'RF2', 'RF3', 'RF4', 'RF5']:
        cnt = sum(1 for p in normalized if p.get('red_flags', {}).get(flag, False))
        print(f'  {flag}: {cnt}/{len(normalized)} ({cnt/len(normalized)*100:.0f}%)')
    print(f'\nPost-patch RF3 count: {rf3_count} / {len(normalized)} projects')
    print(f'Post-patch any_rf count: {any_rf_count} / {len(normalized)} projects')


if __name__ == '__main__':
    main()
