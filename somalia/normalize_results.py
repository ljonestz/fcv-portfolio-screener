"""
Normalize FCV screening results across all 3 schema variants into one canonical format.
"""
import json

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

DIM_MAP_LONG = {
    'D1_fcv_context_diagnostics': (1, 'FCV Context and Diagnostics', 'Sensitivity'),
    'D2_do_no_harm_conflict_risk': (2, 'Do No Harm and Conflict Risk', 'Sensitivity'),
    'D3_stakeholder_political_economy': (3, 'Stakeholder and Political Economy', 'Sensitivity'),
    'D4_objectives_theory_of_change': (4, 'Objectives and Theory of Change', 'Responsiveness'),
    'D5_design_targeting': (5, 'Design and Targeting', 'Responsiveness'),
    'D6_implementation_flexibility': (6, 'Implementation and Operational Flexibility', 'Responsiveness'),
    'D7_results_adaptive_management': (7, 'Results Framework and Adaptive Management', 'Responsiveness'),
    'D8_one_wbg_integration': (8, 'One WBG Integration', 'Responsiveness'),
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


def normalize_dims(dims):
    if isinstance(dims, list):
        result = []
        for d in dims:
            if isinstance(d, dict):
                score = d.get('numeric_score', d.get('score', 0))
                result.append({
                    'id': d.get('id', 0),
                    'name': d.get('name', ''),
                    'composite': d.get('composite', ''),
                    'numeric_score': score,
                    'rating': d.get('rating', score_to_rating(score)),
                    'key_quote': d.get('key_quote', d.get('evidence', '')),
                    'rationale': d.get('rationale', ''),
                })
        return result

    elif isinstance(dims, dict):
        result = []
        # Try short keys first
        for key, (did, dname, comp) in DIM_MAP_SHORT.items():
            if key in dims:
                d = dims[key]
                score = d.get('score', d.get('numeric_score', 0))
                label = d.get('label', '')
                rating = d.get('rating') or (label if label in VALID_RATINGS else score_to_rating(score))
                result.append({
                    'id': did, 'name': dname, 'composite': comp,
                    'numeric_score': score, 'rating': rating,
                    'key_quote': d.get('key_quote', d.get('evidence', '')),
                    'rationale': d.get('rationale', ''),
                })
        if result:
            return sorted(result, key=lambda x: x['id'])
        # Try long keys
        for key, (did, dname, comp) in DIM_MAP_LONG.items():
            if key in dims:
                d = dims[key]
                score = d.get('score', d.get('numeric_score', 0))
                label = d.get('label', '')
                rating = d.get('rating') or (label if label in VALID_RATINGS else score_to_rating(score))
                result.append({
                    'id': did, 'name': dname, 'composite': comp,
                    'numeric_score': score, 'rating': rating,
                    'key_quote': d.get('key_quote', d.get('evidence', '')),
                    'rationale': d.get('rationale', ''),
                })
        return sorted(result, key=lambda x: x['id'])

    return []


def normalize_rf(rf):
    if isinstance(rf, dict):
        result = {}
        for k, v in rf.items():
            if isinstance(v, bool):
                result[k] = v
            elif isinstance(v, dict):
                result[k] = v.get('triggered', False)
            else:
                result[k] = bool(v)
        return result
    return {}


def normalize(r):
    if 'composites' in r:
        sens = r['composites']['sensitivity']['numeric_score']
        resp = r['composites']['responsiveness']['numeric_score']
        sens_rating = r['composites']['sensitivity']['rating']
        resp_rating = r['composites']['responsiveness']['rating']
    elif 'composite_scores' in r:
        cs = r['composite_scores']
        sens = cs.get('sensitivity_final', cs.get('sensitivity_raw', 0))
        resp = cs.get('responsiveness_final', cs.get('responsiveness_raw', 0))
        sens_rating = score_to_rating(sens)
        resp_rating = score_to_rating(resp)
    elif 'composite_sensitivity_score' in r:
        sens = r['composite_sensitivity_score']
        resp = r['composite_responsiveness_score']
        sens_rating = score_to_rating(sens)
        resp_rating = score_to_rating(resp)
    else:
        sens = 0
        resp = 0
        sens_rating = 'Unknown'
        resp_rating = 'Unknown'

    instrument = r.get('instrument_category') or r.get('instrument') or 'Unknown'

    return {
        'project_id': r['project_id'],
        'project_name': r.get('project_name', ''),
        'doc_type': r.get('doc_type', ''),
        'instrument_category': instrument,
        'approval_year': r.get('approval_year'),
        'sensitivity_score': round(float(sens), 2) if sens is not None else None,
        'responsiveness_score': round(float(resp), 2) if resp is not None else None,
        'sensitivity_rating': sens_rating,
        'responsiveness_rating': resp_rating,
        'red_flags': normalize_rf(r.get('red_flags', {})),
        'gap_matrix_cell': r.get('gap_matrix_cell', ''),
        'key_finding': r.get('key_finding', ''),
        'dimensions': normalize_dims(r.get('dimensions', [])),
    }


if __name__ == '__main__':
    base = r'C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\20260314_somalia-fcv-portfolio-analysis'
    raw = json.load(open(base + r'\20260314_somalia_screening_results.json', encoding='utf-8'))
    normalized = [normalize(r) for r in raw]

    print(f'Normalized {len(normalized)} records')
    for r in normalized:
        n = len(r['dimensions'])
        print(f'  {r["project_id"]}: {n} dims, sens={r["sensitivity_score"]}, resp={r["responsiveness_score"]}')

    out = base + r'\20260314_somalia_screening_results_normalized.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, indent=2)
    print(f'\nSaved: {out}')
