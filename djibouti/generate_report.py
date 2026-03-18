"""
Djibouti FCV Portfolio Report — HTML Generator
Date: 2026-03-16
Purpose: Assembles the final HTML analytical report from screening results and charts.

Paths are relative to this script's own directory so the script works correctly
when run from the GitHub repo folder. No hardcoded absolute paths.

Run AFTER:
  1. 20260316_djibouti_fcv_analysis.py  (generates charts)
  2. 20260316_djibouti_screening_results_normalized.json exists
"""

from pathlib import Path
import json
import re
import base64
from datetime import datetime
import numpy as np

# ─── Configuration ────────────────────────────────────────────────────────────

SCRIPT_DIR     = Path(__file__).parent
RESULTS_FILE   = SCRIPT_DIR / '20260316_djibouti_screening_results_normalized.json'
PORTFOLIO_FILE = SCRIPT_DIR / 'filtered_djibouti_portfolio.json'
REPORT_FILE    = SCRIPT_DIR / '20260316_djibouti-fcv-portfolio-report.html'

DIM_NAMES = [
    'FCV Context and Diagnostics',
    'Do No Harm and Conflict Risk',
    'Stakeholder and Political Economy',
    'Objectives and Theory of Change',
    'Design and Targeting',
    'Implementation and Operational Flexibility',
    'Results Framework and Adaptive Management',
    'One WBG Integration (IFC/MIGA)',
]
COMPOSITES = ['Sensitivity'] * 3 + ['Responsiveness'] * 5

RF_LABELS = {
    'RF1': 'Unmitigated Conflict Risk',
    'RF2': 'Missing Distributional Analysis',
    'RF3': 'OP 7.30 Weakly Handled',
    'RF4': 'Elite Capture Unmitigated',
    'RF5': 'Macro Framework Unrealistic',
}

EARLY_COHORT = (2015, 2019)
LATE_COHORT  = (2020, 2024)


# ─── Utility functions ────────────────────────────────────────────────────────

def load_data():
    with open(RESULTS_FILE, encoding='utf-8') as f:
        results = json.load(f)
    with open(PORTFOLIO_FILE, encoding='utf-8') as f:
        portfolio = json.load(f)
    proj_meta = {p['id']: p for p in portfolio}
    return results, proj_meta


def rating_badge(rating):
    cls = {
        'Strong':                 'badge-strong',
        'Substantially Addressed':'badge-subst',
        'Partially Addressed':    'badge-part',
        'Not Addressed':          'badge-not',
        'Not Applicable':         'badge-na',
    }.get(rating, 'badge-na')
    return f'<span class="{cls}">{rating}</span>'


def score_cell(score):
    if score is None:
        return '<td style="color:#9aabb8;text-align:center">—</td>'
    try:
        s = float(score)
    except (ValueError, TypeError):
        return f'<td>{score}</td>'
    if s >= 7:
        bg = '#f0f9f4'; color = '#1a5c38'; border = 'rgba(26,122,74,.25)'
    elif s >= 4:
        bg = '#fff7ed'; color = '#7c3d00'; border = 'rgba(224,123,0,.25)'
    else:
        bg = '#fef2f2'; color = '#7f1d1d'; border = 'rgba(185,28,28,.25)'
    return (f'<td style="text-align:center"><span style="background:{bg};color:{color};'
            f'border:1px solid {border};padding:2px 10px;border-radius:20px;'
            f'font-size:12px;font-weight:700;white-space:nowrap">{s:.1f}</span></td>')


def compute_summary_stats(results):
    stats = {}
    def _s(r): return r.get('sensitivity_score') or r.get('composites', {}).get('sensitivity', {}).get('numeric_score', 0)
    def _r(r): return r.get('responsiveness_score') or r.get('composites', {}).get('responsiveness', {}).get('numeric_score', 0)

    sens = [_s(r) for r in results]
    resp = [_r(r) for r in results]
    stats['n']     = len(results)
    stats['n_ipf'] = sum(1 for r in results if r.get('instrument_category') == 'IPF')
    stats['n_dpf'] = sum(1 for r in results if r.get('instrument_category') == 'DPF')
    stats['avg_s'] = sum(sens) / len(sens) if sens else 0
    stats['avg_r'] = sum(resp) / len(resp) if resp else 0

    # Cohort breakdown (early vs late)
    early = [r for r in results if r.get('approval_year') and EARLY_COHORT[0] <= r['approval_year'] <= EARLY_COHORT[1]]
    late  = [r for r in results if r.get('approval_year') and LATE_COHORT[0]  <= r['approval_year'] <= LATE_COHORT[1]]
    stats['n_early']    = len(early)
    stats['n_late']     = len(late)
    early_s = [_s(r) for r in early]; early_r = [_r(r) for r in early]
    late_s  = [_s(r) for r in late];  late_r  = [_r(r) for r in late]
    stats['early_avg_s'] = sum(early_s) / len(early_s) if early_s else 0
    stats['early_avg_r'] = sum(early_r) / len(early_r) if early_r else 0
    stats['late_avg_s']  = sum(late_s)  / len(late_s)  if late_s  else 0
    stats['late_avg_r']  = sum(late_r)  / len(late_r)  if late_r  else 0

    stats['gap_cells'] = {}
    for r in results:
        cell = r.get('gap_matrix_cell', 'Unknown')
        stats['gap_cells'][cell] = stats['gap_cells'].get(cell, 0) + 1
    stats['dominant_gap_cell'] = max(stats['gap_cells'], key=stats['gap_cells'].get) if stats['gap_cells'] else ''

    rf_totals = {'RF1': 0, 'RF2': 0, 'RF3': 0, 'RF4': 0, 'RF5': 0}
    for r in results:
        for k, v in r.get('red_flags', {}).items():
            if v:
                rf_key = k.upper().replace('_', '')
                for rf in ['RF1', 'RF2', 'RF3', 'RF4', 'RF5']:
                    if rf in rf_key:
                        rf_totals[rf] += 1
    stats['rf_totals'] = rf_totals
    stats['any_rf'] = sum(1 for r in results if any(v for v in r.get('red_flags', {}).values()))

    dim_avgs = {}
    for i in range(1, 9):
        scores = [d['numeric_score'] for r in results
                  for d in r.get('dimensions', []) if d['id'] == i
                  and d.get('numeric_score') is not None]
        dim_avgs[i] = sum(scores) / len(scores) if scores else 0
    stats['dim_avgs'] = dim_avgs

    years_sens = [(r.get('approval_year', 0), _s(r)) for r in results if r.get('approval_year')]
    years_resp = [(r.get('approval_year', 0), _r(r)) for r in results if r.get('approval_year')]
    if len(years_sens) > 2:
        yrs = np.array([y for y, s in years_sens], dtype=float)
        sco = np.array([s for y, s in years_sens])
        stats['sens_trend'] = round(float(np.polyfit(yrs, sco, 1)[0]), 2)
    else:
        stats['sens_trend'] = 0.0
    if len(years_resp) > 2:
        yrs = np.array([y for y, s in years_resp], dtype=float)
        sco = np.array([s for y, s in years_resp])
        stats['resp_trend'] = round(float(np.polyfit(yrs, sco, 1)[0]), 2)
    else:
        stats['resp_trend'] = 0.0

    return stats


# ─── HTML component builders ──────────────────────────────────────────────────

def inline_chart(img_src, alt, caption, narrative=None):
    """
    Render a chart with optional narrative paragraph above it.
    The narrative should frontload the key finding — not just introduce the chart.
    No styled callout boxes: the narrative is plain body text.
    """
    para = f'<p>{narrative}</p>' if narrative else ''
    return f"""{para}
    <figure class="chart-figure">
      <img src="{img_src}" alt="{alt}" class="chart-img">
      <figcaption>{caption}</figcaption>
    </figure>"""


def build_expandable_table(results, proj_meta):
    """
    Unified expandable project table. Each row shows summary data;
    clicking expands the full dimension-level detail inline.
    """
    rows = []

    hint_row = """
        <tr class="table-hint-row">
          <td colspan="10">
            &#9654;&nbsp; <strong>Click any project row</strong> to expand the full FCV screening results for that project
          </td>
        </tr>"""
    rows.append(hint_row)

    for idx, r in enumerate(sorted(results, key=lambda x: x.get('sensitivity_score') or 0, reverse=True)):
        pid  = r['project_id']
        meta = proj_meta.get(pid, {})
        s    = r.get('sensitivity_score') or r.get('composites', {}).get('sensitivity', {}).get('numeric_score', 0)
        resp = r.get('responsiveness_score') or r.get('composites', {}).get('responsiveness', {}).get('numeric_score', 0)
        gap  = r.get('gap_matrix_cell', '')
        gap_colors = {
            'High FCV integration':          '#e8f7e0',
            'Implementation gap':            '#fff3e0',
            'Responsive but underanalysed':  '#e0f0ff',
            'Low FCV integration':           '#fde8e8',
        }
        gap_bg   = gap_colors.get(gap, '#f5f5f5')
        gap_html = f'<span style="background:{gap_bg};padding:2px 6px;border-radius:3px;font-size:0.8em">{gap}</span>'

        comm_raw = str(meta.get('totalcommamt') or '0').replace(',', '')
        try:
            comm_val = float(comm_raw)
            comm_str = f'${comm_val/1e6:.1f}M' if comm_val > 0 else '—'
        except (ValueError, TypeError):
            comm_str = '—'

        sector = ''
        s1 = meta.get('sector1', {})
        if isinstance(s1, dict):
            sector = s1.get('Name', '')[:30]

        name_lower = r.get('project_name', '').lower()
        is_af   = any(k in name_lower for k in ['additional financing', 'additional finance'])
        is_rest = 'restructur' in name_lower
        if is_af:
            badge = ('<span style="background:#e8f0fc;color:#002244;border:1px solid #b0c4de;'
                     'font-size:10px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:4px">AF</span>')
        elif is_rest:
            badge = ('<span style="background:#fff3e0;color:#7c3d00;border:1px solid #f7941e80;'
                     'font-size:10px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:4px">REST</span>')
        else:
            badge = ''

        dim_rows = ''
        for d in r.get('dimensions', []):
            dim_rows += f"""
              <tr>
                <td style="width:2.5em;text-align:center;color:#888;font-weight:700">D{d['id']}</td>
                <td style="font-size:0.88em">{d['name']}</td>
                <td>{rating_badge(d.get('rating', ''))}</td>
                <td style="text-align:center;font-weight:700">{d.get('numeric_score', '')}</td>
                <td style="font-size:0.82em;font-style:italic;color:#555">&#8220;{d.get('key_quote', '')[:150]}&#8221;</td>
                <td style="font-size:0.82em">{d.get('rationale', '')}</td>
              </tr>"""

        rf = r.get('red_flags', {})
        rf_html = ' '.join([
            f'<span style="background:{"#C8102E" if v else "#ddd"};color:{"white" if v else "#666"};'
            f'padding:1px 6px;border-radius:3px;font-size:0.78em;margin:1px">'
            f'{k}: {"&#9888;" if v else "&#10003;"}</span>'
            for k, v in rf.items()
        ])

        detail_id   = f'detail-row-{idx}'
        detail_html = f"""
          <div class="detail-panel">
            <p style="margin:0 0 10px;font-size:13px;line-height:1.65">
              <strong>Key finding:</strong> {r.get('key_finding', '')}
            </p>
            <p style="margin:0 0 14px;font-size:12px"><strong>Red flags:</strong>&nbsp; {rf_html}</p>
            <table style="width:100%;border-collapse:collapse;font-size:12px">
              <thead>
                <tr>
                  <th style="width:2.5em;text-align:center">#</th>
                  <th>Dimension</th>
                  <th>Rating</th>
                  <th style="text-align:center">Score</th>
                  <th>Key Quote</th>
                  <th>Rationale</th>
                </tr>
              </thead>
              <tbody>{dim_rows}</tbody>
            </table>
            <div style="margin-top:12px;padding:10px 14px;background:#f5f7fa;border-left:3px solid #002244;border-radius:4px;font-size:12px">
              <strong>Sensitivity rating:</strong> {r.get('sensitivity_rating', '')}
              &nbsp;&nbsp;
              <strong>Responsiveness rating:</strong> {r.get('responsiveness_rating', '')}
            </div>
          </div>"""

        rows.append(f"""
        <tr class="expandable-row" onclick="toggleRow('{detail_id}', 'icon-{idx}')">
          <td style="font-family:monospace;font-size:0.85em;white-space:nowrap">
            <span id="icon-{idx}" class="expand-icon">&#9654;</span>&nbsp;{pid}
          </td>
          <td>{r.get('project_name', '')}{badge}</td>
          <td style="text-align:center">{r.get('instrument_category', '')}</td>
          <td style="text-align:center">{r.get('approval_year', '')}</td>
          <td style="text-align:center">{meta.get('status', '')}</td>
          <td style="font-size:0.85em">{sector}</td>
          <td style="text-align:center">{comm_str}</td>
          {score_cell(s)}
          {score_cell(resp)}
          <td style="font-size:0.82em">{gap_html}</td>
        </tr>
        <tr id="{detail_id}" style="display:none">
          <td colspan="10" style="padding:0;border-bottom:2px solid #47C4EB">{detail_html}</td>
        </tr>""")

    return '\n'.join(rows)


# ─── Main HTML builder ─────────────────────────────────────────────────────────

def build_html(results, proj_meta):
    stats = compute_summary_stats(results)

    # ── Derived values for inline narrative ──
    best_dim_id   = max(stats['dim_avgs'], key=stats['dim_avgs'].get)
    worst_dim_id  = min(stats['dim_avgs'], key=stats['dim_avgs'].get)
    best_dim_name  = DIM_NAMES[best_dim_id - 1]
    worst_dim_name = DIM_NAMES[worst_dim_id - 1]
    best_dim_score  = stats['dim_avgs'][best_dim_id]
    worst_dim_score = stats['dim_avgs'][worst_dim_id]

    year_counts = {}
    for r in results:
        y = r.get('approval_year')
        if y:
            year_counts[y] = year_counts.get(y, 0) + 1
    peak_year       = max(year_counts, key=year_counts.get) if year_counts else 'N/A'
    peak_year_count = year_counts.get(peak_year, 0)

    most_common_rf       = max(stats['rf_totals'], key=stats['rf_totals'].get)
    most_common_rf_label = RF_LABELS.get(most_common_rf, most_common_rf)
    most_common_rf_count = stats['rf_totals'][most_common_rf]
    most_common_rf_pct   = most_common_rf_count / stats['n'] * 100

    n_high       = stats['gap_cells'].get('High FCV integration', 0)
    n_impl_gap   = stats['gap_cells'].get('Implementation gap', 0)
    n_low        = stats['gap_cells'].get('Low FCV integration', 0)
    n_resp_under = stats['gap_cells'].get('Responsive but underanalysed', 0)
    trend_s      = stats.get('sens_trend', 0)
    trend_r      = stats.get('resp_trend', 0)

    # ── Dimension breakdown table ──
    dim_table_rows = ''
    for i, (name, comp) in enumerate(zip(DIM_NAMES, COMPOSITES), 1):
        avg   = stats['dim_avgs'].get(i, 0)
        bar_w = int(avg / 10 * 100)
        comp_color = '#002244' if comp == 'Sensitivity' else '#E07B00'
        dim_table_rows += f"""
        <tr>
          <td style="text-align:center;font-weight:700">D{i}</td>
          <td>{name}</td>
          <td style="text-align:center">
            <span style="background:{'#e8f4fc' if comp == 'Sensitivity' else '#fff7ed'};color:{'#004e7c' if comp == 'Sensitivity' else '#7c3d00'};border:1px solid {'rgba(0,159,218,.25)' if comp == 'Sensitivity' else 'rgba(224,123,0,.25)'};padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600">{comp}</span>
          </td>
          <td style="text-align:center;font-weight:700">{avg:.2f}</td>
          <td style="padding:4px 0">
            <div style="background:#d9e2ec;border-radius:4px;height:10px;width:100%">
              <div style="background:{comp_color};opacity:0.75;border-radius:4px;height:10px;width:{bar_w}%"></div>
            </div>
          </td>
        </tr>"""

    # ── Gap matrix table ──
    gap_cells_html = ''
    cell_styles = {
        'High FCV integration':         ('background:#f0f9f4', '&#9989;'),
        'Implementation gap':           ('background:#fff7ed', '&#9888;'),
        'Responsive but underanalysed': ('background:#e8f4fc', '&#8505;'),
        'Low FCV integration':          ('background:#fef2f2', '&#10060;'),
    }
    for cell, count in sorted(stats['gap_cells'].items(), key=lambda x: -x[1]):
        style, icon = cell_styles.get(cell, ('', ''))
        pct = count / stats['n'] * 100
        gap_cells_html += f"""
        <tr style="{style}">
          <td style="text-align:center;font-size:1.1em">{icon}</td>
          <td><strong>{cell}</strong></td>
          <td style="text-align:center">{count}</td>
          <td style="text-align:center">{pct:.0f}%</td>
        </tr>"""

    expandable_rows = build_expandable_table(results, proj_meta)
    today = datetime.now().strftime('%d %B %Y')

    globe_svg = '''<svg class="wbg-globe" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="16" cy="16" r="14" stroke="rgba(255,255,255,0.6)" stroke-width="1.5"/>
      <ellipse cx="16" cy="16" rx="5.5" ry="14" stroke="rgba(255,255,255,0.6)" stroke-width="1.5"/>
      <line x1="2" y1="16" x2="30" y2="16" stroke="rgba(255,255,255,0.6)" stroke-width="1.5"/>
      <line x1="4" y1="10" x2="28" y2="10" stroke="rgba(255,255,255,0.35)" stroke-width="1"/>
      <line x1="4" y1="22" x2="28" y2="22" stroke="rgba(255,255,255,0.35)" stroke-width="1"/>
    </svg>'''

    # ── Rating labels for inline text ──
    s_rating = 'Substantially Addressed' if stats['avg_s'] >= 7 else ('Partially Addressed' if stats['avg_s'] >= 4 else 'Not Addressed')
    r_rating = 'Substantially Addressed' if stats['avg_r'] >= 7 else ('Partially Addressed' if stats['avg_r'] >= 4 else 'Not Addressed')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Djibouti World Bank Portfolio — FCV Portfolio Screening Report</title>
  <link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@300;400;600;700&family=Source+Serif+4:ital,wght@0,300;0,400;0,600;1,300;1,400&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --navy:   #002244;
      --blue:   #009FDA;
      --cyan:   #47C4EB;
      --white:  #ffffff;
      --bg:     #f8f9fb;
      --border: #dde3eb;
      --muted:  #6b7c93;
      --text:   #1c2b3a;
      --serif:  'Source Serif 4', Georgia, serif;
      --sans:   'Source Sans 3', Arial, sans-serif;
    }}

    html {{ scroll-behavior: smooth; }}

    body {{
      font-family: var(--sans);
      font-size: 15px;
      line-height: 1.75;
      color: var(--text);
      background: var(--bg);
    }}

    /* ── Top bar ── */
    .top-bar {{
      background: var(--navy);
      padding: 6px 32px;
      display: flex; align-items: center; justify-content: space-between;
    }}
    .top-bar-left {{ display: flex; align-items: center; gap: 12px; }}
    .wbg-globe {{ width: 30px; height: 30px; flex-shrink: 0; }}
    .top-bar-wordmark {{ font-size: 13px; font-weight: 600; color: rgba(255,255,255,.9); letter-spacing: .03em; text-transform: uppercase; }}
    .top-bar-divider {{ width: 1px; height: 16px; background: rgba(255,255,255,.25); }}
    .top-bar-unit {{ font-size: 12px; color: var(--cyan); letter-spacing: .04em; text-transform: uppercase; }}
    .top-bar-badge {{ font-size: 10px; padding: 3px 9px; background: rgba(0,159,218,.2); border: 1px solid rgba(0,159,218,.35); border-radius: 20px; color: var(--cyan); letter-spacing: .07em; text-transform: uppercase; }}

    /* ── Hero ── */
    .hero {{
      background: linear-gradient(135deg, #002244 0%, #003d7a 60%, #005a9e 100%);
      padding: 48px 32px 44px; position: relative; overflow: hidden;
    }}
    .hero::before {{
      content: ''; position: absolute; inset: 0;
      background-image: linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px);
      background-size: 44px 44px; pointer-events: none;
    }}
    .hero::after {{
      content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 3px;
      background: linear-gradient(90deg, var(--blue), var(--cyan));
    }}
    .hero-inner {{ max-width: 860px; margin: 0 auto; position: relative; z-index: 1; }}
    .hero-eyebrow {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .14em; color: var(--cyan); margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }}
    .hero-eyebrow::before {{ content: ''; display: inline-block; width: 20px; height: 2px; background: var(--cyan); }}
    .hero h1 {{ font-family: var(--serif); font-weight: 300; font-size: 36px; color: #fff; line-height: 1.15; margin-bottom: 14px; }}
    .hero h1 strong {{ font-weight: 600; color: var(--cyan); }}
    .hero-sub {{ font-size: 15px; color: rgba(255,255,255,.7); line-height: 1.65; margin-bottom: 22px; }}
    .hero-chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .hero-chip {{ font-size: 12px; padding: 5px 13px; background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2); border-radius: 20px; color: rgba(255,255,255,.82); }}

    /* ── Page wrap & content column ── */
    .page-wrap {{ max-width: 860px; margin: 0 auto; padding: 36px 24px 80px; }}

    /* ── Table of contents ── */
    .toc {{
      background: var(--white); border: 1px solid var(--border); border-radius: 6px;
      padding: 18px 24px; margin-bottom: 40px;
      border-left: 3px solid var(--cyan);
    }}
    .toc h3 {{ font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin-bottom: 10px; font-weight: 700; }}
    .toc ol {{ padding-left: 18px; columns: 2; column-gap: 28px; }}
    .toc li {{ margin: 4px 0; font-size: 13px; }}
    .toc a {{ color: var(--blue); text-decoration: none; }}
    .toc a:hover {{ text-decoration: underline; }}

    /* ── Article sections ── */
    .report-section {{ margin-bottom: 52px; }}
    .report-section + .report-section {{ border-top: 1px solid var(--border); padding-top: 44px; }}

    /* ── Typography ── */
    h2 {{
      font-family: var(--serif); font-weight: 400; font-size: 26px;
      color: var(--navy); line-height: 1.2; margin-bottom: 18px;
    }}
    h3 {{
      font-family: var(--sans); font-size: 16px; font-weight: 700;
      color: var(--navy); margin: 28px 0 10px;
    }}
    p {{
      font-size: 15px; line-height: 1.8; color: var(--text);
      margin-bottom: 16px;
    }}
    p:last-child {{ margin-bottom: 0; }}

    /* ── Stat cards ── */
    .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 20px 0 28px; }}
    .stat-card {{ background: var(--white); border: 1px solid var(--border); border-radius: 6px; padding: 16px; text-align: center; border-top: 3px solid var(--cyan); }}
    .stat-card .value {{ font-size: 2em; font-weight: 700; color: var(--navy); line-height: 1; }}
    .stat-card .label {{ font-size: 11px; color: var(--muted); margin-top: 5px; text-transform: uppercase; letter-spacing: .04em; }}

    /* ── Score boxes ── */
    .score-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 20px 0; }}
    .score-box {{ padding: 20px 22px; border-radius: 6px; border: 1px solid var(--border); }}
    .score-box-s {{ background: #eef5fc; border-top: 3px solid var(--navy); }}
    .score-box-r {{ background: #fff8f0; border-top: 3px solid #d97706; }}
    .score-box .value {{ font-size: 2.6em; font-weight: 700; line-height: 1; }}
    .score-box-s .value {{ color: var(--navy); }}
    .score-box-r .value {{ color: #92400e; }}
    .score-box .label {{ font-weight: 700; font-size: 14px; margin: 6px 0 4px; }}
    .score-box .dims {{ font-size: 12px; color: var(--muted); }}

    /* ── Charts ── */
    .chart-figure {{ margin: 24px 0; text-align: center; }}
    .chart-img {{ width: 100%; max-width: 100%; border: 1px solid var(--border); border-radius: 5px; }}
    .chart-figure figcaption {{ font-size: 12px; color: var(--muted); margin-top: 7px; font-style: italic; }}

    /* ── Tables ── */
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }}
    th {{ background: #f0f4f8; color: var(--text); padding: 9px 11px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; font-weight: 700; border-bottom: 2px solid var(--border); }}
    td {{ padding: 8px 11px; border-bottom: 1px solid var(--border); vertical-align: top; }}
    tr:nth-child(even) td {{ background: #fafbfc; }}

    /* ── Expandable table ── */
    .table-hint-row td {{
      background: #eef5fc; color: #003d6e; font-size: 13px;
      text-align: center; padding: 9px; border-bottom: 1px solid #c5daf0;
      font-weight: 600; letter-spacing: .01em;
    }}
    .expandable-row {{ cursor: pointer; }}
    .expandable-row:hover td {{ background: #e4f0fb !important; transition: background 0.12s; }}
    .expand-icon {{ color: var(--muted); font-size: 0.68em; display: inline-block; width: 1em; }}
    .detail-panel {{ padding: 18px 22px; background: #f8fafd; }}

    /* ── Rating badges ── */
    .badge-strong {{ background:#f0f9f4;color:#1a5c38;border:1px solid rgba(26,122,74,.25);padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap; }}
    .badge-subst  {{ background:#e8f4fc;color:#004e7c;border:1px solid rgba(0,159,218,.25);padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap; }}
    .badge-part   {{ background:#fff7ed;color:#7c3d00;border:1px solid rgba(224,123,0,.25);padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap; }}
    .badge-not    {{ background:#fef2f2;color:#7f1d1d;border:1px solid rgba(185,28,28,.25);padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap; }}
    .badge-na     {{ background:#f0f4f8;color:var(--muted);border:1px solid var(--border);padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap; }}

    ul, ol {{ padding-left: 22px; margin: 10px 0 16px; }}
    li {{ margin: 6px 0; line-height: 1.65; }}

    /* ── Cohort panels ── */
    .instr-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 20px 0; }}
    .instr-panel {{ border: 1px solid var(--border); border-radius: 6px; padding: 18px; background: var(--white); }}

    /* ── Methodology collapsible ── */
    details.meth {{ border: none; }}
    details.meth > summary {{
      cursor: pointer; list-style: none; display: inline-flex; align-items: center; gap: 8px;
      font-weight: 700; font-size: 15px; color: var(--navy); margin-bottom: 4px;
    }}
    details.meth > summary::-webkit-details-marker {{ display: none; }}
    details.meth > summary::before {{ content: '\\25B6\\00A0\\00A0'; font-size: 0.7em; color: var(--muted); }}
    details.meth[open] > summary::before {{ content: '\\25BC\\00A0\\00A0'; }}

    /* ── Footer ── */
    .page-footer {{ background: var(--navy); color: rgba(255,255,255,.38); font-size: 11px; padding: 16px 32px; text-align: center; letter-spacing: .04em; }}

    @media print {{
      body {{ background: white; }}
      .page-wrap {{ padding: 0; max-width: 100%; }}
    }}
  </style>
  <script>
    function toggleRow(detailId, iconId) {{
      var row  = document.getElementById(detailId);
      var icon = document.getElementById(iconId);
      if (row.style.display === 'none') {{
        row.style.display = 'table-row';
        if (icon) icon.innerHTML = '&#9660;';
      }} else {{
        row.style.display = 'none';
        if (icon) icon.innerHTML = '&#9654;';
      }}
    }}
  </script>
</head>
<body>

<div class="top-bar">
  <div class="top-bar-left">
    {globe_svg}
    <span class="top-bar-wordmark">World Bank Group</span>
    <div class="top-bar-divider"></div>
    <span class="top-bar-unit">FCV Analytics</span>
  </div>
  <span class="top-bar-badge">DJIBOUTI · FCV-AFFECTED CONTEXT</span>
</div>

<div class="hero">
  <div class="hero-inner">
    <div class="hero-eyebrow">FCV Portfolio Assessment — Djibouti 2015–2024</div>
    <h1>Djibouti World Bank Portfolio<br><strong>FCV Portfolio Screening Report</strong></h1>
    <div class="hero-sub">Systematic FCV Portfolio Assessment of {stats['n']} operations approved 2015–2024, applying the WBG FCV Sensitivity and Responsiveness Screener framework.</div>
    <div class="hero-chips">
      <span class="hero-chip">&#128197; {today}</span>
      <span class="hero-chip">&#128203; {stats['n']} projects screened</span>
      <span class="hero-chip">&#128200; Avg sensitivity {stats['avg_s']:.1f} · responsiveness {stats['avg_r']:.1f}</span>
      <span class="hero-chip">FCV-Affected Context</span>
    </div>
  </div>
</div>

<div class="page-wrap">

  <div class="toc">
    <h3>Contents</h3>
    <ol>
      <li><a href="#overview">What This Assessment Found</a></li>
      <li><a href="#portfolio">The Portfolio: {stats['n']} Projects, 10 Years</a></li>
      <li><a href="#scores">How FCV-Integrated Is the Portfolio?</a></li>
      <li><a href="#dimensions">Where Strengths and Weaknesses Lie</a></li>
      <li><a href="#redflags">Red Flags: Where the Risks Are</a></li>
      <li><a href="#cohorts">Has FCV Quality Improved Over Time?</a></li>
      <li><a href="#conclusions">What This Means for Djibouti Operations</a></li>
      <li><a href="#methodology">Methodology</a></li>
      <li><a href="#annex">Annex — All {stats['n']} Projects</a></li>
    </ol>
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="overview">
    <h2>What This Assessment Found</h2>

    <p>This report presents a systematic FCV (Fragility, Conflict and Violence) portfolio assessment of the World Bank Group's Djibouti engagement — {stats['n']} operations approved between 2015 and 2024, all Investment Project Financing (IPF). Although Djibouti is not currently on the WBG's Harmonized List of Fragile and Conflict-Affected Situations, it is a country significantly affected by drivers of fragility, conflict, and violence. Its economy depends heavily on foreign military base rents (hosting US, French, Chinese, and Japanese installations), creating a concentrated political economy with limited productive diversification. Youth unemployment exceeds 70%, governance is highly centralised, the Afar minority faces structural marginalisation, and Djibouti's borders with Ethiopia, Eritrea, Somalia, and Yemen expose it to multiple regional conflict and displacement spillovers. These are not abstract fragility labels — they are operational realities that should shape every World Bank investment in the country.</p>

    <p>Each project was assessed against the WBG FCV Sensitivity and Responsiveness Screener across eight dimensions and two composites. <strong>FCV Sensitivity</strong> (D1–D3) measures whether a project correctly diagnoses Djibouti's fragility dynamics — conflict drivers, political economy, and do-no-harm risks. <strong>FCV Responsiveness</strong> (D4–D8) measures whether the operational design adapts to that diagnosis: the theory of change, targeting, implementation flexibility, results framework, and One WBG coordination. Scores range from 1 to 10; 7.0 marks the high-performance threshold.</p>

    <p>The headline result is a portfolio that <strong>partially analyses Djibouti's FCV context but fails to translate that analysis into operational design</strong>. The average sensitivity score of <strong>{stats['avg_s']:.1f}/10</strong> ({s_rating}) indicates that most operations engage with FCV context at a surface level — some reference Djibouti's fragility drivers, but few develop a diagnostic deep enough to inform design choices. The average responsiveness score of <strong>{stats['avg_r']:.1f}/10</strong> ({r_rating}) reveals the deeper problem: even where analysis exists, it is not systematically shaping theories of change, targeting, or results frameworks. The {stats['avg_s'] - stats['avg_r']:.1f}-point gap between sensitivity and responsiveness is modest in absolute terms — within the range of measurement uncertainty on a 1–10 scale — but the trend is more telling than the level: FCV sensitivity shows a modest upward trajectory ({trend_s:+.2f}/yr) while FCV responsiveness is flat ({trend_r:+.2f}/yr), meaning the gap is not narrowing over time. The portfolio is gradually getting better at describing Djibouti's fragility while remaining static in its ability to act on that knowledge.</p>

    <p>The chart below maps all {stats['n']} projects onto the two-by-two gap matrix. Each dot is a project; the star marks the portfolio average. The distribution is starkly polarised: {n_high} projects achieve High FCV Integration while {n_low} fall into Low FCV Integration, with just {n_impl_gap} in the Implementation Gap quadrant. This near-even split — rather than a single dominant cluster — indicates that FCV quality in the Djibouti portfolio is not a systemic failure but a systemic inconsistency. Half the portfolio engages seriously with FCV context; the other half does not.</p>

    {inline_chart(
        'chart4_sensitivity_vs_responsiveness.png',
        'Portfolio quadrant analysis',
        'Portfolio positioning: each point is one project, plotted by FCV Sensitivity (y-axis) vs FCV Responsiveness (x-axis). '
        'Star (&#9733;) = portfolio average. Quadrant lines at Sensitivity = 6.0, Responsiveness = 5.5.'
    )}

    <p>This polarisation points to a clear institutional diagnosis: FCV quality in Djibouti operations depends on individual TTL orientation and sector-specific norms rather than on portfolio-wide quality standards. Operations in health, social protection, and governance tend to score higher; infrastructure and private-sector operations tend to score lower. The implication is that the primary lever for improvement is not more FCV guidance (which exists) but more consistent enforcement of that guidance at the concept-note and appraisal stages — particularly for sectors that do not have an inherent FCV orientation.</p>

    <div class="stat-grid">
      <div class="stat-card"><div class="value">{stats['n']}</div><div class="label">Projects Screened</div></div>
      <div class="stat-card"><div class="value">{stats['n_ipf']}</div><div class="label">IPF Operations</div></div>
      <div class="stat-card"><div class="value">{n_high}</div><div class="label">High FCV Integration</div></div>
      <div class="stat-card"><div class="value">{stats['avg_s']:.1f}</div><div class="label">Avg FCV Sensitivity</div></div>
      <div class="stat-card"><div class="value">{stats['avg_r']:.1f}</div><div class="label">Avg FCV Responsiveness</div></div>
      <div class="stat-card"><div class="value">{stats['any_rf']}</div><div class="label">Projects with &#8805;1 Red Flag</div></div>
    </div>
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="portfolio">
    <h2>The Portfolio: {stats['n']} Projects, 10 Years</h2>

    <p>The portfolio spans a decade of WBG engagement in Djibouti, from 2015 to 2024. All {stats['n']} operations are Investment Project Financing (IPF) — no DPF or Programme-for-Results instruments were identified for this period. The sectoral mix covers urban infrastructure, social protection, health, education, water and sanitation, private sector development, and governance. This breadth reflects Djibouti's Vision 2035 agenda, which aims to transform the country from a garrison economy dependent on foreign military base rents into a regional logistics and services hub — a transition that itself carries significant fragility implications if growth benefits are not broadly distributed.</p>

    <p>Approval activity peaked in {peak_year} with {peak_year_count} operations. Several projects are Additional Financing extensions of earlier interventions in health, social safety nets, and urban development, indicating sectoral continuity. One project (P165558, Women and Youth Entrepreneurship) was excluded as no public PDF was available; the remaining {stats['n']} operations represent comprehensive portfolio coverage.</p>

    {inline_chart(
        'chart1_portfolio_timeline.png',
        'Portfolio timeline',
        f'Projects approved per year, 2015\u20132024, by instrument type. All {stats["n"]} screened operations are IPF.'
    )}
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="scores">
    <h2>How FCV-Integrated Is the Portfolio?</h2>

    <p>The two composite scores — sensitivity and responsiveness — are the primary analytical outputs. Sensitivity captures how well project documents diagnose Djibouti's fragility context, conflict risks, and political economy. Responsiveness captures whether the operational design — objectives, targeting, implementation, results — adapts to that diagnosis. Both portfolio averages fall in the Partially Addressed band (4.0–6.9): sensitivity at {stats['avg_s']:.1f}/10 and responsiveness at {stats['avg_r']:.1f}/10. The {stats['avg_s'] - stats['avg_r']:.1f}-point difference between them is not large in absolute terms, but it follows a pattern consistently observed across FCV portfolios: projects are more likely to name fragility risks than to design around them. More telling than the current gap is its trajectory — sensitivity is trending upward while responsiveness is flat, suggesting the portfolio is not learning to translate better analysis into better design.</p>

    <div class="score-grid">
      <div class="score-box score-box-s">
        <div class="value">{stats['avg_s']:.1f}<span style="font-size:0.38em;opacity:0.55">/10</span></div>
        <div class="label">Avg FCV Sensitivity</div>
        <div class="dims">FCV Context &amp; Diagnostics · Do No Harm · Stakeholder &amp; Political Economy</div>
      </div>
      <div class="score-box score-box-r">
        <div class="value">{stats['avg_r']:.1f}<span style="font-size:0.38em;opacity:0.55">/10</span></div>
        <div class="label">Avg FCV Responsiveness</div>
        <div class="dims">Objectives &amp; ToC · Design &amp; Targeting · Implementation Flexibility · Results Framework · One WBG</div>
      </div>
    </div>

    <p>The gap matrix distribution reveals two distinct clusters rather than a single dominant failure mode:</p>

    <table style="max-width:460px">
      <thead><tr><th></th><th>Matrix Position</th><th style="text-align:center">Count</th><th style="text-align:center">Share</th></tr></thead>
      <tbody>{gap_cells_html}</tbody>
    </table>

    <p>The near-equal split between High FCV Integration ({n_high} projects, {n_high/stats['n']*100:.0f}%) and Low FCV Integration ({n_low} projects, {n_low/stats['n']*100:.0f}%) is an unusually polarised pattern. It indicates that the Djibouti portfolio does not have a uniform FCV problem — it has a quality consistency problem. Some TTLs and sector teams are producing well-integrated FCV design; others are not. The two trend charts below show whether this split is narrowing over time. The answer is mixed: sensitivity shows a modest upward trajectory ({trend_s:+.2f}/yr), but responsiveness is essentially flat ({trend_r:+.2f}/yr). This means the portfolio is gradually improving its FCV analysis without correspondingly improving its FCV-adapted design — better diagnosis is not yet producing better operational responses.</p>

    <figure class="chart-figure">
      <img src="chart2_sensitivity_over_time.png" alt="Sensitivity over time" class="chart-img">
      <figcaption>FCV Sensitivity by approval year</figcaption>
    </figure>
    <figure class="chart-figure">
      <img src="chart3_responsiveness_over_time.png" alt="Responsiveness over time" class="chart-img">
      <figcaption>FCV Responsiveness by approval year</figcaption>
    </figure>
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="dimensions">
    <h2>Where Strengths and Weaknesses Lie</h2>

    <p>The dimension-level data reveals where the portfolio's FCV integration breaks down. The strongest area is <strong>D{best_dim_id}: {best_dim_name}</strong> (avg {best_dim_score:.1f}/10) — the entry point where most projects at least reference Djibouti's fragility context. The weakest is <strong>D{worst_dim_id}: {worst_dim_name}</strong> (avg {worst_dim_score:.1f}/10), a systematic gap that indicates the portfolio is not leveraging IFC/MIGA instruments or coordinating across WBG entities to address fragility. The descending pattern from D1 to D8 follows the expected sensitivity-responsiveness gradient: projects are better at describing fragility than at designing for it. Notably, the two lowest-scoring dimensions — D7 (Results Framework, {stats['dim_avgs'].get(7, 0):.1f}) and D8 (One WBG, {stats['dim_avgs'].get(8, 0):.1f}) — are both below 5.0, indicating that the downstream, implementation-facing dimensions are where FCV integration is weakest.</p>

    <p>The radar chart below compares the early cohort (2015–2019) against the later cohort (2020–2024). If the WBG FCV Strategy were driving design improvement, the later cohort should show a wider arc on the responsiveness dimensions (D4–D8). Examine whether this is the case — and whether any narrowing between cohorts on specific dimensions suggests where strategy guidance has been most effective.</p>

    {inline_chart(
        'chart7_dimension_radar.png',
        'Dimension radar chart',
        'Average scores across all 8 dimensions. Early cohort (2015\u20132019) = blue; later cohort (2020\u20132024) = orange; portfolio average = dashed. Scale 0\u201310.',
    )}

    <p>The heatmap below provides project-level granularity. Each column is a project; each row is a dimension. Horizontal patterns (rows that are uniformly amber or red) identify portfolio-wide weaknesses. Vertical patterns (columns that are uniformly green or red) identify strong or weak individual operations. Two patterns stand out: D7 and D8 show the most persistent amber-to-red banding across operations, confirming these as structural weaknesses rather than outlier effects. On the vertical axis, the projects in the left columns (highest sensitivity) show visibly greener profiles across all dimensions, reinforcing the finding that FCV quality in Djibouti is bifurcated rather than uniformly distributed.</p>

    <table>
      <thead><tr><th>#</th><th>Dimension</th><th>Composite</th><th style="text-align:center">Avg Score</th><th style="min-width:130px">Relative Strength</th></tr></thead>
      <tbody>{dim_table_rows}</tbody>
    </table>

    {inline_chart(
        'chart5_dimension_heatmap.png',
        'Dimension score heatmap',
        f'FCV dimension scores across all {stats["n"]} projects. Each column = one project; each row = one dimension. Red = low (1\u20133), amber = moderate (4\u20136), green = high (7\u201310).'
    )}
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="redflags">
    <h2>Red Flags: Where the Risks Are</h2>

    <p>The eight dimensions scored above capture the <em>quality</em> of FCV integration on a 1–10 scale. Red flags serve a different purpose: they are <strong>binary pass/fail checks</strong> on specific design failures that dimension scores alone may miss. A project can score adequately on a dimension — for example, acknowledging conflict dynamics in its context analysis (D2) — and still trigger the related red flag (RF1) if the mitigation it proposes is hollow or pro-forma. Red flags are evidence-based: they trigger only when the project document itself provides the evidence of a gap, not from absence of content. Each triggered flag deducts −0.5 from the Sensitivity composite (floored at 1.0), meaning that projects accumulating multiple flags see their composite pulled below what the dimension averages alone would suggest.</p>

    <p>Across the {stats['n']}-project portfolio, <strong>{stats['any_rf']} operations ({stats['any_rf']/stats['n']*100:.0f}%) trigger at least one red flag</strong>. The most prevalent is <strong>{most_common_rf}: {most_common_rf_label}</strong>, appearing in {most_common_rf_count} of {stats['n']} projects ({most_common_rf_pct:.0f}%). The chart below shows the frequency of each flag.</p>

    {inline_chart(
        'chart6_red_flags.png',
        'Red flag frequency',
        f'Frequency of each red flag across the Djibouti portfolio (n={stats["n"]}). '
        f'RF1 = Unmitigated Conflict Risk · RF2 = Missing Distributional Analysis · RF3 = OP 7.30 Weakly Handled · RF4 = Elite Capture Unmitigated · RF5 = Macro Framework Unrealistic.'
    )}

    <p><strong>RF5 — Macro/Programmatic Framework Unrealistic ({most_common_rf_pct:.0f}%).</strong> The dominant red flag in Djibouti's portfolio reflects a structural challenge rather than individual project failure. Djibouti's small, aid-dependent economy — with GDP heavily concentrated in the port and military base sectors — means that macroeconomic and institutional assumptions underpinning project results frameworks are inherently fragile. Climate shocks (recurring drought, flash flooding), refugee inflows from neighbouring Somalia and Yemen, and a political economy dominated by strategic rents create an operating environment where linear planning assumptions break down. Many IPF operations design results indicators that presuppose stable government delivery capacity and predictable fiscal conditions; in Djibouti's context, these assumptions are frequently overtaken by events. The prevalence of RF5 suggests the portfolio would benefit from more systematic use of scenario-based results frameworks and adaptive management triggers that explicitly account for Djibouti's volatile operating environment.</p>

    <p><strong>RF3 — OP 7.30 Weakly Handled (18%).</strong> RF3 is a narrow, evidence-based flag that checks specifically whether a project engages with or transfers resources to a <em>de facto</em> or unconstitutionally constituted authority — the situation governed by World Bank Operational Policy 7.30. It is not a general resettlement or safeguards check; it should trigger only when the project document explicitly references such an engagement and fails to address the governance and legitimacy risks it creates. <em>Caution is warranted in interpreting the reported 18% rate.</em> During screening, agents are known to have drifted from this narrow definition, applying RF3 more broadly to projects with weak treatment of marginalised community inclusion and customary land rights — genuine FCV design concerns, but ones that fall under D2 (Do No Harm) and D5 (Design and Targeting) dimensions, not OP 7.30. The four projects recorded as triggering RF3 should be reviewed individually: if the agent rationale does not cite explicit OP 7.30 language from the project document, the trigger likely reflects interpretive drift rather than a genuine de facto authority engagement. In Djibouti's context — where constitutional governance, however centralised, is not in question — a true RF3 rate near zero is more plausible than 18%. Readers should treat the recorded rate as an approximate signal of safeguards and inclusion gaps rather than confirmed instances of OP 7.30 non-compliance.</p>

    <p><strong>RF1, RF2, and RF4 — all at 0%.</strong> No projects in the portfolio trigger these flags. For RF2 (Missing Distributional Analysis) and RF4 (Elite Capture Unmitigated), the zero rate is less surprising in a 22-project all-IPF portfolio: these flags are more commonly triggered in DPF and P4R operations where fiscal policy changes or government system-strengthening interact more directly with distributional politics. For RF1 (Unmitigated Conflict Risk), however, the zero rate warrants caution. RF1 triggers only when a document explicitly names a conflict pathway <em>and</em> fails to mitigate it. In a country where clan-based political dynamics, the Eritrea border legacy, and refugee-host community tensions are genuine operational risks, the absence of RF1 may indicate that projects avoid naming conflict pathways in specific enough terms to trigger the flag. The portfolio-average D2 score (Do No Harm and Conflict Risk) of 5.1/10 — squarely in the 'Partially Addressed' range — is consistent with this reading: projects engage with conflict risk at a general level but rarely with the specificity that would either trigger or clearly avoid RF1.</p>
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="cohorts">
    <h2>Has FCV Quality Improved Over Time?</h2>

    <p>Since all {stats['n']} operations are IPF, the most informative analytical cut is temporal: has FCV integration quality improved between the early cohort (2015–2019, n={stats['n_early']}) and the later cohort (2020–2024, n={stats['n_late']})? The 2020 WBG FCV Strategy and its associated operational guidance raised expectations for FCV-classified countries, making the post-2020 cohort a natural test of whether institutional guidance is translating into design practice.</p>

    <p>The results are divergent. FCV sensitivity improved from {stats['early_avg_s']:.1f}/10 (early) to {stats['late_avg_s']:.1f}/10 (later) — a {stats['late_avg_s'] - stats['early_avg_s']:+.1f} point gain consistent with the FCV Strategy's emphasis on better contextual analysis. But FCV responsiveness {'declined' if stats['late_avg_r'] < stats['early_avg_r'] else 'remained flat'}: from {stats['early_avg_r']:.1f}/10 to {stats['late_avg_r']:.1f}/10 ({stats['late_avg_r'] - stats['early_avg_r']:+.1f} points). This divergence is the most important temporal finding. It means the FCV Strategy may be succeeding in getting teams to <em>describe</em> fragility context more thoroughly, but it is not yet succeeding in getting them to <em>design differently</em> as a result. The box plots below show the full score distributions for each cohort, including spread and outliers.</p>

    <div class="instr-grid">
      <div class="instr-panel">
        <h3 style="color:#009FDA;margin-top:0">Early Cohort 2015–2019 (n={stats['n_early']})</h3>
        <p style="margin:0 0 4px"><strong>Avg Sensitivity:</strong> {stats['early_avg_s']:.1f}/10</p>
        <p style="margin:0"><strong>Avg Responsiveness:</strong> {stats['early_avg_r']:.1f}/10</p>
      </div>
      <div class="instr-panel">
        <h3 style="color:#d97706;margin-top:0">Later Cohort 2020–2024 (n={stats['n_late']})</h3>
        <p style="margin:0 0 4px"><strong>Avg Sensitivity:</strong> {stats['late_avg_s']:.1f}/10</p>
        <p style="margin:0"><strong>Avg Responsiveness:</strong> {stats['late_avg_r']:.1f}/10</p>
      </div>
    </div>

    {inline_chart(
        'chart8_score_distribution.png',
        'Score distribution by cohort',
        'Distribution of FCV Sensitivity and Responsiveness scores by approval cohort. '
        'Box = interquartile range; line = median; whiskers = min/max.'
    )}
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="conclusions">
    <h2>What This Means for Djibouti Operations</h2>

    <p>Three findings define the Djibouti portfolio's FCV profile. First, average FCV integration is moderate but the trajectory is uneven — sensitivity is edging upward while responsiveness remains flat, meaning better FCV analysis is not yet translating into better FCV-adapted design. Second, the portfolio is sharply polarised: half the operations achieve high FCV integration while the other half do not, indicating a quality consistency problem rather than a uniform capacity deficit. Third, red flags affect {stats['any_rf']/stats['n']*100:.0f}% of operations, with results framework gaps ({most_common_rf}) as the dominant pattern — a structural weakness that undermines the portfolio's ability to track and adapt to FCV-relevant changes during implementation.</p>

    <p>Five operational priorities follow from these findings:</p>

    <ol>
      <li><strong>Close the analysis-to-action gap.</strong> The divergence between sensitivity (+{stats['late_avg_s'] - stats['early_avg_s']:.1f} points across cohorts) and responsiveness ({stats['late_avg_r'] - stats['early_avg_r']:+.1f} points) suggests that improving FCV analysis alone is not sufficient. Better FCV analysis is only valuable if it changes project design. Quality review at appraisal should require TTLs to demonstrate how their FCV diagnosis has shaped the theory of change, targeting, and implementation arrangements — not just the risk section.</li>
      <li><strong>Raise the floor on low-performing operations.</strong> The {n_low} projects in the Low FCV Integration quadrant are not borderline cases — several score below 4.0 on both composites. In a context affected by significant FCV drivers, this level of FCV integration is insufficient. Operations scoring below 4.0 on either composite should be flagged for mandatory FCV Country Coordinator review at concept note stage, with a clear expectation that FCV design features are incorporated before appraisal.</li>
      <li><strong>Name Djibouti's specific fragility drivers, not generic fragility.</strong> Youth unemployment (estimated at 70%+), marginalisation of Afar communities, climate-driven displacement from the interior, and the political economy of strategic rent concentration are Djibouti's defining fragility pathways. Too many PADs use generic fragility language that could apply to any FCV-affected country. Every project document should explicitly identify which of these pathways intersects with the operation's sector and geography, and how the design responds.</li>
      <li><strong>Fix results frameworks for FCV contexts.</strong> D7 (Results Framework, avg {stats['dim_avgs'].get(7, 0):.1f}/10) is the second-weakest dimension and {most_common_rf} is the most prevalent red flag. Standard development indicators cannot capture whether an operation is adapting to fragility dynamics during implementation. Each results framework should include at least one FCV-adjusted indicator, a mid-term review trigger linked to fragility conditions, and contingency clauses that allow reallocation if context deteriorates.</li>
      <li><strong>Leverage One WBG coordination systematically.</strong> D8 (One WBG Integration, avg {stats['dim_avgs'].get(8, 0):.1f}/10) is the portfolio's weakest dimension. Djibouti's positioning as a regional logistics hub, combined with IFC's presence in energy and financial services, creates opportunities for joint programming that IDA-only PADs are not capturing. The CMU should establish a standing coordination mechanism requiring IPF teams to consult IFC's pipeline and MIGA's risk assessments during preparation — particularly for infrastructure, private sector development, and urban operations.</li>
    </ol>
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="methodology">
    <h2>Methodology</h2>

    <details class="meth">
      <summary>Click to expand methodology details</summary>
      <div style="padding-top:16px">
        <h3>Data collection</h3>
        <p>Project metadata was retrieved via the World Bank Open Data API (search.worldbank.org), filtering for Djibouti (country code: DJ), approval year 2015–2024, and IPF, DPF, or P4R lending instruments. No DPF or P4R operations were found in the portfolio for this period. Document metadata was retrieved using the World Bank Documents and Reports API. Because the project_id filter proved unreliable for Djibouti in the Documents API, Project Appraisal Documents were identified through a text search pre-fetch of all Djibouti-tagged PADs, with bidirectional title-recall matching (threshold: max recall &#8805; 0.55, Jaccard &#8805; 0.18) to link documents to projects. ISRs and Project Papers were retrieved via direct project_id lookup with country validation. Keyword fallback search was used for remaining unmatched projects. PDF text was extracted using PyMuPDF (fitz), capped at 120,000 characters per document.</p>
        <h3>FCV screening framework</h3>
        <p>Each document was screened against the WBG FCV Sensitivity and Responsiveness Screener, grounded in the WBG FCV Strategy (2025) and FCV Operational Manual for FCV Country Coordinators (June 2025). Each dimension is rated on a 4-point scale (Strong / Substantially Addressed / Partially Addressed / Not Addressed), converted to a 1–10 numeric scale. Composite scores are weighted averages of contributing dimensions, with red flag deductions applied to the Sensitivity composite (&#8722;0.5 per red flag, floor 1). Although Djibouti is not currently on the WBG Harmonized List of Fragile and Conflict-Affected Situations, it is significantly affected by FCV drivers, warranting FCV-sensitive portfolio analysis.</p>
        <h3>Scope and limitations</h3>
        <ul>
          <li>1 of 23 portfolio projects (P165558, Djibouti Support for Women and Youth Entrepreneurship) excluded — only procurement plans available publicly, no PAD/ICR PDF URL accessible</li>
          <li>P174461 (Digital Djibouti) matched to the Eastern Africa Regional Digital Integration Programme (EARDIP) PAD — a regional document that covers Djibouti among multiple countries; country-specific content is partial</li>
          <li>Four Additional Financing operations (P172979, P174566, P181612, P181415) screened against parent project PADs; results reflect the quality of the original PAD, not the AF document</li>
          <li>Text extraction capped at 120,000 characters; later sections of very long PADs may not be captured</li>
          <li>One primary document screened per project; ISRs and Aide-Mémoires not included unless the ISR was the only available document</li>
          <li>Gap matrix cell assignments from screening agents were independently recomputed from numeric scores to ensure consistency; three agent errors were corrected during normalisation</li>
        </ul>
      </div>
    </details>
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="annex">
    <h2>Annex — All {stats['n']} Projects</h2>

    <p>The table below lists all {stats['n']} screened projects, sorted by FCV Sensitivity score. <strong>Click any row</strong> to expand the full dimension-by-dimension screening results, key finding, and red flag detail for that project. Score colours: <span style="background:#f0f9f4;padding:1px 6px;border-radius:3px;font-size:11px;color:#1a5c38;border:1px solid rgba(26,122,74,.2)">&#9650; &#8805; 7.0</span> <span style="background:#fff7ed;padding:1px 6px;border-radius:3px;font-size:11px;color:#7c3d00;border:1px solid rgba(224,123,0,.2)">4.0–6.9</span> <span style="background:#fef2f2;padding:1px 6px;border-radius:3px;font-size:11px;color:#7f1d1d;border:1px solid rgba(185,28,28,.2)">&#9660; &lt; 4.0</span></p>

    <table>
      <thead>
        <tr>
          <th>Project ID</th>
          <th>Project Name</th>
          <th style="text-align:center">Instrument</th>
          <th style="text-align:center">Year</th>
          <th style="text-align:center">Status</th>
          <th>Sector</th>
          <th style="text-align:center">Commitment</th>
          <th style="text-align:center">FCV Sens.</th>
          <th style="text-align:center">FCV Resp.</th>
          <th>Gap Matrix</th>
        </tr>
      </thead>
      <tbody>
        {expandable_rows}
      </tbody>
    </table>
  </div>

</div>

<div class="page-footer">
  WBG FCV Screener &nbsp;·&nbsp; WBG FCV Strategy (2025) &nbsp;·&nbsp; FCV Operational Manual (June 2025)
  &nbsp;·&nbsp; Generated {today}
</div>

</body>
</html>"""
    return html


def make_standalone(html: str, script_dir: Path) -> str:
    """
    Replace all relative PNG chart references with inline base64 data URIs,
    producing a single fully self-contained HTML file that can be shared
    without any accompanying image files.
    """
    def encode_png(match):
        fname    = match.group(1)
        img_path = script_dir / fname
        if img_path.exists():
            data = base64.b64encode(img_path.read_bytes()).decode('ascii')
            return f'src="data:image/png;base64,{data}"'
        return match.group(0)  # leave unchanged if file missing

    return re.sub(r'src="(chart[\w]+\.png)"', encode_png, html)


def main():
    print('Djibouti FCV Portfolio Report — HTML Generation')
    print('=' * 52)
    print('Loading data...')
    results, proj_meta = load_data()
    print(f'  {len(results)} projects loaded from {RESULTS_FILE.name}')

    print('Building HTML report...')
    html = build_html(results, proj_meta)

    # Standard version (relative image paths — for local use)
    print(f'Writing {REPORT_FILE.name}...')
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  Saved: {REPORT_FILE}')
    print(f'  Size:  {REPORT_FILE.stat().st_size / 1024:.0f} KB')

    # Standalone version (embedded images — for sharing)
    standalone_file = REPORT_FILE.with_name(REPORT_FILE.stem + '-standalone.html')
    print(f'Writing {standalone_file.name} (self-contained)...')
    standalone_html = make_standalone(html, SCRIPT_DIR)
    with open(standalone_file, 'w', encoding='utf-8') as f:
        f.write(standalone_html)
    print(f'  Saved: {standalone_file}')
    print(f'  Size:  {standalone_file.stat().st_size / 1024:.0f} KB')


if __name__ == '__main__':
    main()
