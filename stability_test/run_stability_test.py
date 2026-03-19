"""
run_stability_test.py
Status checker and prompt generator for FCV screener stability test.

For each test project, shows how many runs are complete and prints the
agent prompt template to use for launching the next batch of agents.

Usage:
    python stability_test/run_stability_test.py --project P148850
    python stability_test/run_stability_test.py --all
"""

import argparse
import hashlib
import json
from pathlib import Path

# ── Project registry ────────────────────────────────────────────────────────
# Baseline scores come from the post-RF3-recheck normalized results (2026-03-18).
# S = sensitivity_score, R = responsiveness_score

PROJECTS = {
    'P148850': {
        'name':    'Ethiopia Expressway Development Support Project',
        'country': 'ethiopia',
        'year':    2015,
        'doc_type': 'Project Appraisal Document',
        'instrument': 'IPF',
        'baseline_sensitivity':     2.00,
        'baseline_responsiveness':  1.80,
        'baseline_gap_cell':        'Low FCV integration',
        'rationale': 'Very low scorer — floor stability',
    },
    'P148586': {
        'name':    'Enhancing Income Opportunities in DJ',
        'country': 'djibouti',
        'year':    2015,
        'doc_type': 'Project Appraisal Document',
        'instrument': 'IPF',
        'baseline_sensitivity':     3.33,
        'baseline_responsiveness':  3.60,
        'baseline_gap_cell':        'Low FCV integration',
        'rationale': 'Low scorer — floor stability',
    },
    'P162901': {
        'name':    'Djibouti Integrated Slum Upgrading Project',
        'country': 'djibouti',
        'year':    2018,
        'doc_type': 'Project Appraisal Document',
        'instrument': 'IPF',
        'baseline_sensitivity':     7.00,
        'baseline_responsiveness':  6.60,
        'baseline_gap_cell':        'High FCV integration',
        'rationale': 'High scorer — ceiling stability',
    },
    'P166220': {
        'name':    'Integrated Cash Transfer and Human Capital Project',
        'country': 'djibouti',
        'year':    2019,
        'doc_type': 'Project Appraisal Document',
        'instrument': 'IPF',
        'baseline_sensitivity':     5.83,
        'baseline_responsiveness':  5.50,
        'baseline_gap_cell':        'Responsive but underanalysed',
        'rationale': 'Near both key thresholds — most at risk of gap-matrix category flips',
    },
    'P177233': {
        'name':    'Response Recovery Resilience for Conflict-Affected Communities in Ethiopia',
        'country': 'ethiopia',
        'year':    2022,
        'doc_type': 'Project Appraisal Document',
        'instrument': 'IPF',
        'baseline_sensitivity':     8.33,
        'baseline_responsiveness':  7.40,
        'baseline_gap_cell':        'High FCV integration',
        'rationale': 'Very high FCV-integrated project — ceiling stability',
    },
}

TOTAL_RUNS   = 15
REPO_ROOT    = Path(__file__).parent.parent
RESULTS_ROOT = Path(__file__).parent / 'results'


def get_text_path(project_id: str) -> Path:
    country = PROJECTS[project_id]['country']
    return REPO_ROOT / country / 'extracted_texts' / f'{project_id}.txt'


def get_results_dir(project_id: str) -> Path:
    return RESULTS_ROOT / project_id


def count_completed_runs(project_id: str) -> list[int]:
    """Return list of run numbers (1-based) that already have a results file."""
    d = get_results_dir(project_id)
    if not d.exists():
        return []
    completed = []
    for i in range(1, TOTAL_RUNS + 1):
        if (d / f'run_{i:02d}.json').exists():
            completed.append(i)
    return completed


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def build_prompt(project_id: str, run_number: int, text: str) -> str:
    p = PROJECTS[project_id]
    save_path = f'stability_test/results/{project_id}/run_{run_number:02d}.json'
    return (
        f"Screen this single project using the FCV screener skill.\n"
        f"Project ID: {project_id} | Name: {p['name']}\n"
        f"Document type: {p['doc_type']} | Instrument: {p['instrument']} | Year: {p['year']}\n\n"
        f"STABILITY TEST RUN {run_number} OF {TOTAL_RUNS} — treat this as a normal screening.\n\n"
        f"Output format constraints (strictly enforced):\n"
        f"- key_quote: max 250 chars per dimension\n"
        f"- rationale per dimension: max 3 sentences / 200 words\n"
        f"- key_finding: max 2 sentences / 100 words\n"
        f"- Output: a single JSON object only. No preamble before the JSON.\n\n"
        f"Save result to: {save_path}\n\n"
        f"[extracted text below]\n{text}"
    )


def report_project(project_id: str) -> None:
    if project_id not in PROJECTS:
        print(f"ERROR: Unknown project ID '{project_id}'")
        print(f"Known IDs: {', '.join(PROJECTS)}")
        return

    p = PROJECTS[project_id]
    text_path = get_text_path(project_id)

    print(f"\n{'=' * 65}")
    print(f"Project: {project_id} — {p['name']}")
    print(f"Country: {p['country'].capitalize()} | Year: {p['year']} | {p['instrument']}")
    print(f"Rationale: {p['rationale']}")
    print(f"Baseline: S={p['baseline_sensitivity']:.2f}  R={p['baseline_responsiveness']:.2f}  [{p['baseline_gap_cell']}]")
    print(f"{'=' * 65}")

    if not text_path.exists():
        print(f"  ERROR: Extracted text not found at:\n  {text_path}")
        return

    text = text_path.read_text(encoding='utf-8')
    print(f"\nExtracted text: {len(text):,} chars | SHA256[:12]: {text_hash(text)}")

    completed = count_completed_runs(project_id)
    pending   = [i for i in range(1, TOTAL_RUNS + 1) if i not in completed]

    print(f"\nRuns complete : {len(completed)}/{TOTAL_RUNS}  {completed if completed else '(none)'}")
    print(f"Runs pending  : {len(pending)}  {pending}")

    if not pending:
        print("\nAll 15 runs complete. Run analyze_stability.py to compute statistics.")
        return

    print(f"\nNext run to launch: {pending[0]}")
    print("\n--- Sample prompt (run 1) ---")
    sample_prompt = build_prompt(project_id, pending[0], '<TEXT OMITTED — use full extracted text>')
    print(sample_prompt)


def main() -> None:
    parser = argparse.ArgumentParser(description='FCV Screener Stability Test — status and prompt generator')
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--project', metavar='PID', help='Single project ID (e.g. P148850)')
    group.add_argument('--all', action='store_true',  help='Report status for all 5 test projects')
    args = parser.parse_args()

    if args.all:
        for pid in PROJECTS:
            report_project(pid)
        # Cross-project summary
        print(f"\n{'=' * 65}")
        print("SUMMARY — runs complete per project")
        print(f"{'=' * 65}")
        for pid, p in PROJECTS.items():
            completed = count_completed_runs(pid)
            bar = '#' * len(completed) + '-' * (TOTAL_RUNS - len(completed))
            print(f"  {pid}  {bar}  {len(completed):2d}/{TOTAL_RUNS}  {p['country']}")
    else:
        report_project(args.project)


if __name__ == '__main__':
    main()
