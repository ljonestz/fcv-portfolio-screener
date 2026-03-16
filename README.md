# FCV Portfolio Screener

A reusable workflow for running World Bank **FCV (Fragility, Conflict & Violence) Sensitivity and Responsiveness** portfolio analyses at the country level.

## What it does

Takes a World Bank country portfolio, fetches the most policy-relevant project document for each operation, extracts text from PDFs, and applies the FCV Sensitivity and Responsiveness Screener to every document. Outputs 8 analytical charts and a self-contained HTML report.

## Methodology

Scores each project across 8 dimensions (1–10) grouped into two composites:
- **FCV Sensitivity** (D1–D3): how well the project understands the FCV context
- **FCV Responsiveness** (D4–D8): how well the project adapts operationally to that context

Based on the WBG FCV Strategy (2025) and FCV Operational Manual (June 2025).

## Countries

| Country | Period | Projects | Avg Sensitivity | Avg Responsiveness |
|---------|--------|----------|----------------|-------------------|
| Somalia | 2015–2024 | 40 | 6.64 | 5.97 |

## Structure

```
fcv-portfolio-screener/
├── CLAUDE.md              # Full replication guide
├── README.md              # This file
├── .gitignore
└── somalia/
    ├── 20260314_somalia_fcv_analysis.py          # Chart generation
    ├── generate_report.py                        # HTML report generator
    ├── normalize_results.py                      # Merge + normalise batch results
    ├── screening_targets.json                    # 40 projects with PDF URLs
    ├── filtered_somalia_portfolio.json           # Filtered portfolio (43 projects)
    ├── 20260314_somalia_screening_results_normalized.json  # Canonical results
    ├── chart1_portfolio_timeline.png
    ├── ... (8 charts total)
    ├── 20260314_somalia-fcv-portfolio-report.html   # original report
    └── 20260316_somalia-fcv-portfolio-report.html   # redesigned blog-style report
```

## Setup

```bash
pip install requests PyMuPDF pandas matplotlib seaborn numpy
```

Requires the FCV screener skill installed in Claude Code. See `CLAUDE.md` for full instructions.

## Running the report generator

```bash
cd somalia
python generate_report.py
```

The script reads data files from its own directory (`Path(__file__).parent`) and writes the HTML report alongside them — no hardcoded paths. Output: `20260316_somalia-fcv-portfolio-report.html`.

## Replication

See `CLAUDE.md` for the step-by-step workflow and instructions for adapting to a new country.

## Contributing

All changes should be made on a feature branch (`git checkout -b <type>/<description>`), not directly on `main`. See the global `CLAUDE.md` for the branch-first workflow convention.
