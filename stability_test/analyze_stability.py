"""
analyze_stability.py
Compute stability statistics from repeated FCV screening runs.

Loads all run_*.json files for a project, computes per-dimension and
composite variance, detects categorical flips, and saves:
  - Console summary table
  - stability_test/stability_summary.csv  (all projects x all metrics)
  - stability_test/stability_heatmap_<PID>.png  (8 dims x N runs, coloured 1-10)

Usage:
    python stability_test/analyze_stability.py --project P148850
    python stability_test/analyze_stability.py --all
"""

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

# -- Config ------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).parent
RESULTS_ROOT = SCRIPT_DIR / 'results'
SUMMARY_CSV  = SCRIPT_DIR / 'stability_summary.csv'

SENSITIVITY_THRESHOLD    = 6.0
RESPONSIVENESS_THRESHOLD = 5.5

# Acceptance thresholds
SD_STABLE    = 0.5
SD_MARGINAL  = 1.0
RF_FLIP_MAX  = 0.10   # ≤10 % flip rate → stable

DIMENSIONS = [
    ('D1', 'FCV Context & Diagnostics',      'Sensitivity'),
    ('D2', 'Do No Harm & Conflict Risk',      'Sensitivity'),
    ('D3', 'Stakeholder & Political Economy', 'Sensitivity'),
    ('D4', 'Objectives & Theory of Change',   'Responsiveness'),
    ('D5', 'Design & Targeting',              'Responsiveness'),
    ('D6', 'Implementation & Op. Flexibility','Responsiveness'),
    ('D7', 'Results Framework & Adapt. Mgmt', 'Responsiveness'),
    ('D8', 'One WBG Integration',             'Responsiveness'),
]

PROJECTS = {
    'P148850': {'name': 'Ethiopia Expressway', 'country': 'ethiopia'},
    'P148586': {'name': 'DJ Enhancing Income Opportunities', 'country': 'djibouti'},
    'P162901': {'name': 'DJ Integrated Slum Upgrading', 'country': 'djibouti'},
    'P166220': {'name': 'DJ Integrated Cash Transfer', 'country': 'djibouti'},
    'P177233': {'name': 'ETH R3R Conflict-Affected Areas', 'country': 'ethiopia'},
}

RED_FLAGS = ['RF1', 'RF2', 'RF3', 'RF4', 'RF5']


# -- Helpers ------------------------------------------------------------------

def score_to_rating(s: float) -> str:
    if s >= 7:
        return 'Substantially Addressed'
    if s >= 4:
        return 'Partially Addressed'
    return 'Not Addressed'


def gap_cell(sens: float, resp: float) -> str:
    high_s = sens >= SENSITIVITY_THRESHOLD
    high_r = resp >= RESPONSIVENESS_THRESHOLD
    if high_s and high_r:
        return 'High FCV integration'
    if high_s and not high_r:
        return 'Implementation gap'
    if not high_s and high_r:
        return 'Responsive but underanalysed'
    return 'Low FCV integration'


def sd_label(sd: float) -> str:
    if sd <= SD_STABLE:
        return 'STABLE'
    if sd <= SD_MARGINAL:
        return 'MARGINAL'
    return 'UNSTABLE'


def extract_dimension_score(run: dict, dim_id: str) -> float | None:
    """Extract numeric score for a given dimension ID from a run JSON."""
    dims = run.get('dimensions', [])
    if isinstance(dims, list):
        for d in dims:
            if isinstance(d, dict):
                did = str(d.get('id', d.get('dimension_id', ''))).upper()
                if not did.startswith('D'):
                    did = f'D{did}'
                if did == dim_id:
                    score = d.get('numeric_score', d.get('score'))
                    if score is not None:
                        return float(score)
    return None


def extract_rf(run: dict) -> dict[str, bool]:
    rf_raw = run.get('red_flags', {})
    result = {}
    for flag in RED_FLAGS:
        v = rf_raw.get(flag, rf_raw.get(flag.lower()))
        if v is None:
            result[flag] = False
        elif isinstance(v, bool):
            result[flag] = v
        elif isinstance(v, dict):
            result[flag] = bool(v.get('triggered', False))
        else:
            result[flag] = bool(v)
    return result


def load_runs(project_id: str) -> list[dict]:
    """Load all run_*.json files for a project. Returns list of parsed dicts."""
    results_dir = RESULTS_ROOT / project_id
    if not results_dir.exists():
        return []
    runs = []
    for f in sorted(results_dir.glob('run_*.json')):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            # Some agents wrap in a list; unwrap if so
            if isinstance(data, list):
                if len(data) == 1:
                    data = data[0]
                else:
                    print(f"  WARNING: {f.name} contains a list of {len(data)} items -- using first")
                    data = data[0]
            data['_run_file'] = f.name
            runs.append(data)
        except json.JSONDecodeError as e:
            print(f"  ERROR: Could not parse {f.name}: {e}")
    return runs


# -- Core analysis ------------------------------------------------------------

def analyze_project(project_id: str) -> dict | None:
    """
    Run stability analysis for one project.
    Returns a stats dict, or None if insufficient runs.
    """
    runs = load_runs(project_id)
    n = len(runs)

    if n == 0:
        print(f"\n{project_id}: No run files found in {RESULTS_ROOT / project_id}")
        return None
    if n < 2:
        print(f"\n{project_id}: Only {n} run -- need at least 2 to compute variance")
        return None

    print(f"\n{'=' * 65}")
    print(f"Project: {project_id} -- {PROJECTS.get(project_id, {}).get('name', '')}")
    print(f"Runs loaded: {n}")
    print(f"{'=' * 65}")

    # -- Extract composite scores from each run -------------------------------
    sens_scores = []
    resp_scores = []

    for run in runs:
        composites = run.get('composites', {})
        if composites:
            s = composites.get('sensitivity', {}).get('numeric_score')
            r = composites.get('responsiveness', {}).get('numeric_score')
        else:
            # Fallback: compute from dimensions
            cs = run.get('composite_scores', {})
            s = cs.get('sensitivity_final', cs.get('sensitivity_score', cs.get('sensitivity_raw')))
            r = cs.get('responsiveness_final', cs.get('responsiveness_score', cs.get('responsiveness_raw')))

        if s is None or r is None:
            # Last resort: compute from dimensions
            d_scores = [extract_dimension_score(run, f'D{i}') for i in range(1, 9)]
            if all(x is not None for x in d_scores[:3]):
                s = sum(d_scores[:3]) / 3
            if all(x is not None for x in d_scores[3:]):
                r = sum(d_scores[3:]) / 5

        if s is not None:
            sens_scores.append(float(s))
        if r is not None:
            resp_scores.append(float(r))

    # -- Dimension scores (D1-D8) ---------------------------------------------
    dim_scores: dict[str, list[float]] = {dim_id: [] for dim_id, _, _ in DIMENSIONS}

    for run in runs:
        for dim_id, _, _ in DIMENSIONS:
            score = extract_dimension_score(run, dim_id)
            if score is not None:
                dim_scores[dim_id].append(score)

    # -- Red flags ------------------------------------------------------------
    rf_values: dict[str, list[bool]] = {f: [] for f in RED_FLAGS}
    for run in runs:
        rfs = extract_rf(run)
        for f in RED_FLAGS:
            rf_values[f].append(rfs[f])

    # -- Gap matrix cells -----------------------------------------------------
    gap_cells = []
    for s, r in zip(sens_scores, resp_scores):
        gap_cells.append(gap_cell(s, r))

    # -- Statistics -----------------------------------------------------------
    def safe_stats(vals: list[float]) -> dict:
        if not vals:
            return {'mean': None, 'sd': None, 'min': None, 'max': None, 'n': 0}
        return {
            'mean': round(statistics.mean(vals), 3),
            'sd':   round(statistics.stdev(vals), 3) if len(vals) > 1 else 0.0,
            'min':  round(min(vals), 2),
            'max':  round(max(vals), 2),
            'n':    len(vals),
        }

    sens_stats = safe_stats(sens_scores)
    resp_stats = safe_stats(resp_scores)
    dim_stats = {}
    for dim_id, _, _ in DIMENSIONS:
        dim_stats[dim_id] = safe_stats(dim_scores[dim_id])

    # -- Categorical flip rates ------------------------------------------------
    sens_ratings  = [score_to_rating(s) for s in sens_scores]
    resp_ratings  = [score_to_rating(r) for r in resp_scores]
    modal_s_rating = Counter(sens_ratings).most_common(1)[0][0] if sens_ratings else None
    modal_r_rating = Counter(resp_ratings).most_common(1)[0][0] if resp_ratings else None
    modal_gap      = Counter(gap_cells).most_common(1)[0][0]    if gap_cells     else None

    s_flip_rate   = sum(1 for x in sens_ratings if x != modal_s_rating) / len(sens_ratings)   if sens_ratings else None
    r_flip_rate   = sum(1 for x in resp_ratings if x != modal_r_rating) / len(resp_ratings)   if resp_ratings else None
    gap_flip_rate = sum(1 for x in gap_cells    if x != modal_gap)      / len(gap_cells)      if gap_cells    else None

    # -- RF flip rates ---------------------------------------------------------
    rf_flip_rates = {}
    for flag in RED_FLAGS:
        vals = rf_values[flag]
        if vals:
            modal = Counter(vals).most_common(1)[0][0]
            rf_flip_rates[flag] = sum(1 for v in vals if v != modal) / len(vals)
        else:
            rf_flip_rates[flag] = None

    # -- Print summary --------------------------------------------------------
    print(f"\nComposite Scores ({n} runs)")
    print(f"  {'':28s}  {'Mean':>6}  {'SD':>6}  {'Min':>6}  {'Max':>6}  {'Status'}")
    print(f"  {'-' * 70}")

    for label, stats, flip_rate, modal_rating in [
        ('Sensitivity',    sens_stats, s_flip_rate, modal_s_rating),
        ('Responsiveness', resp_stats, r_flip_rate, modal_r_rating),
    ]:
        sd = stats['sd']
        status = sd_label(sd) if sd is not None else 'N/A'
        flip_pct = f"{flip_rate:.0%}" if flip_rate is not None else 'N/A'
        print(f"  {label:28s}  {stats['mean']:>6.3f}  {sd:>6.3f}  {stats['min']:>6.2f}  {stats['max']:>6.2f}  {status}  rating flips: {flip_pct} (modal: {modal_rating})")

    print(f"\nDimension Scores ({n} runs)")
    print(f"  {'':3s}  {'Dimension':30s}  {'Mean':>6}  {'SD':>6}  {'Min':>5}  {'Max':>5}  {'Status'}")
    print(f"  {'-' * 70}")
    for dim_id, dim_name, composite in DIMENSIONS:
        st = dim_stats[dim_id]
        if st['n'] == 0:
            print(f"  {dim_id:3s}  {dim_name:30s}  NO DATA")
            continue
        sd = st['sd']
        status = sd_label(sd) if sd is not None else 'N/A'
        print(f"  {dim_id:3s}  {dim_name:30s}  {st['mean']:>6.3f}  {sd:>6.3f}  {st['min']:>5.1f}  {st['max']:>5.1f}  {status}")

    print(f"\nGap Matrix Cell Distribution ({n} runs)")
    cell_counts = Counter(gap_cells)
    for cell, count in cell_counts.most_common():
        marker = ' <-- MODAL' if cell == modal_gap else ''
        print(f"  {count:3d}x  {cell}{marker}")
    flip_str = f"{gap_flip_rate:.0%}" if gap_flip_rate is not None else 'N/A'
    print(f"  Gap matrix flip rate: {flip_str}")

    print(f"\nRed Flag Stability ({n} runs)")
    for flag in RED_FLAGS:
        vals = rf_values[flag]
        if not vals:
            print(f"  {flag}: NO DATA")
            continue
        modal_val = Counter(vals).most_common(1)[0][0]
        flip_rate_rf = rf_flip_rates[flag]
        status = 'STABLE' if flip_rate_rf <= RF_FLIP_MAX else 'UNSTABLE'
        true_count  = sum(1 for v in vals if v is True)
        false_count = len(vals) - true_count
        print(f"  {flag}: {true_count}x True / {false_count}x False  |  flip rate: {flip_rate_rf:.0%}  {status}")

    # -- Verdict ---------------------------------------------------------------
    all_composite_sds = [
        s for s in [sens_stats.get('sd'), resp_stats.get('sd')] if s is not None
    ]
    max_composite_sd = max(all_composite_sds) if all_composite_sds else None
    composite_verdict = sd_label(max_composite_sd) if max_composite_sd is not None else 'N/A'
    any_cat_flip = (s_flip_rate and s_flip_rate > 0) or (r_flip_rate and r_flip_rate > 0)
    any_rf_unstable = any(
        v is not None and v > RF_FLIP_MAX for v in rf_flip_rates.values()
    )

    print(f"\n{'-' * 65}")
    print(f"VERDICT: Composite SD status: {composite_verdict} (max SD = {max_composite_sd:.3f})")
    print(f"         Categorical rating flips: {'YES -- INVESTIGATE' if any_cat_flip else 'None'}")
    print(f"         Red flag instability:     {'YES -- INVESTIGATE' if any_rf_unstable else 'None'}")
    print(f"{'-' * 65}")

    # -- Assemble return dict --------------------------------------------------
    return {
        'project_id':       project_id,
        'n_runs':           n,
        'sens_mean':        sens_stats['mean'],
        'sens_sd':          sens_stats['sd'],
        'sens_min':         sens_stats['min'],
        'sens_max':         sens_stats['max'],
        'resp_mean':        resp_stats['mean'],
        'resp_sd':          resp_stats['sd'],
        'resp_min':         resp_stats['min'],
        'resp_max':         resp_stats['max'],
        'max_composite_sd': max_composite_sd,
        'composite_verdict': composite_verdict,
        's_flip_rate':      round(s_flip_rate, 4) if s_flip_rate is not None else None,
        'r_flip_rate':      round(r_flip_rate, 4) if r_flip_rate is not None else None,
        'gap_flip_rate':    round(gap_flip_rate, 4) if gap_flip_rate is not None else None,
        'modal_gap_cell':   modal_gap,
        **{f'rf{flag[-1]}_flip_rate': round(rf_flip_rates[flag], 4) if rf_flip_rates[flag] is not None else None
           for flag in RED_FLAGS},
        **{f'd{dim_id[1]}_mean': dim_stats[dim_id]['mean'] for dim_id, _, _ in DIMENSIONS},
        **{f'd{dim_id[1]}_sd':   dim_stats[dim_id]['sd']   for dim_id, _, _ in DIMENSIONS},
        'dim_scores': {dim_id: dim_scores[dim_id] for dim_id, _, _ in DIMENSIONS},
    }


# -- Heatmap ------------------------------------------------------------------

def make_heatmap(result: dict, project_id: str) -> None:
    """Save a heatmap of dimension scores x runs."""
    dim_ids   = [d[0] for d in DIMENSIONS]
    dim_names = [d[1] for d in DIMENSIONS]
    n_runs    = result['n_runs']

    # Build 2D array: dims x runs
    matrix = np.full((len(dim_ids), n_runs), np.nan)
    for i, dim_id in enumerate(dim_ids):
        scores = result['dim_scores'].get(dim_id, [])
        for j, s in enumerate(scores):
            if j < n_runs:
                matrix[i, j] = s

    fig, ax = plt.subplots(figsize=(max(8, n_runs * 0.55 + 2), 5))

    cmap = plt.get_cmap('RdYlGn')
    norm = mcolors.Normalize(vmin=1, vmax=10)
    im   = ax.imshow(matrix, cmap=cmap, norm=norm, aspect='auto')

    # Annotate cells
    for i in range(len(dim_ids)):
        for j in range(n_runs):
            val = matrix[i, j]
            if not np.isnan(val):
                ax.text(j, i, f'{val:.1f}', ha='center', va='center',
                        fontsize=8, color='black' if 0.3 < norm(val) < 0.85 else 'white')

    ax.set_xticks(range(n_runs))
    ax.set_xticklabels([f'R{j+1:02d}' for j in range(n_runs)], fontsize=8)
    ax.set_yticks(range(len(dim_ids)))
    ax.set_yticklabels([f'{did}: {name}' for did, name in zip(dim_ids, dim_names)], fontsize=9)

    cbar = fig.colorbar(im, ax=ax, orientation='vertical', fraction=0.03, pad=0.02)
    cbar.set_label('Score (1-10)', fontsize=9)

    proj_name = PROJECTS.get(project_id, {}).get('name', project_id)
    ax.set_title(
        f'FCV Screener Stability Test -- {project_id}: {proj_name}\n'
        f'Dimension Scores Across {n_runs} Independent Runs',
        fontsize=10, pad=10
    )

    out_path = SCRIPT_DIR / f'stability_heatmap_{project_id}.png'
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"\nHeatmap saved: {out_path.name}")


# -- CSV output ----------------------------------------------------------------

CSV_COLS = [
    'project_id', 'n_runs',
    'sens_mean', 'sens_sd', 'sens_min', 'sens_max',
    'resp_mean', 'resp_sd', 'resp_min', 'resp_max',
    'max_composite_sd', 'composite_verdict',
    's_flip_rate', 'r_flip_rate', 'gap_flip_rate', 'modal_gap_cell',
    'rf1_flip_rate', 'rf2_flip_rate', 'rf3_flip_rate', 'rf4_flip_rate', 'rf5_flip_rate',
    'd1_mean', 'd1_sd', 'd2_mean', 'd2_sd', 'd3_mean', 'd3_sd',
    'd4_mean', 'd4_sd', 'd5_mean', 'd5_sd', 'd6_mean', 'd6_sd',
    'd7_mean', 'd7_sd', 'd8_mean', 'd8_sd',
]


def update_summary_csv(new_row: dict) -> None:
    """Append or update a row in stability_summary.csv."""
    rows: list[dict] = []

    if SUMMARY_CSV.exists():
        import csv as csv_mod
        with SUMMARY_CSV.open(newline='', encoding='utf-8') as f:
            reader = csv_mod.DictReader(f)
            for row in reader:
                if row.get('project_id') != new_row['project_id']:
                    rows.append(row)

    rows.append({col: new_row.get(col, '') for col in CSV_COLS})

    import csv as csv_mod
    with SUMMARY_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv_mod.DictWriter(f, fieldnames=CSV_COLS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Summary CSV updated: {SUMMARY_CSV.name}  ({len(rows)} row(s))")


# -- Entry point ---------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description='FCV Screener Stability Test -- analysis')
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--project', metavar='PID', help='Single project ID')
    group.add_argument('--all',     action='store_true', help='Analyze all projects with completed runs')
    args = parser.parse_args()

    if args.all:
        pids_to_run = list(PROJECTS.keys())
    else:
        pids_to_run = [args.project]

    for pid in pids_to_run:
        result = analyze_project(pid)
        if result:
            # Strip dim_scores before CSV (not needed there)
            csv_row = {k: v for k, v in result.items() if k != 'dim_scores'}
            update_summary_csv(csv_row)
            make_heatmap(result, pid)


if __name__ == '__main__':
    main()
