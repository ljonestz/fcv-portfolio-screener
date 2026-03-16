"""
Somalia FCV Portfolio Report — HTML Generator
Date: 2026-03-14  |  Revised: 2026-03-16
Purpose: Assembles the final HTML analytical report from screening results and charts.

Paths are relative to this script's own directory so the script works correctly
when run from the GitHub repo folder. No hardcoded absolute paths.

Run AFTER:
  1. 20260314_somalia_fcv_analysis.py  (generates charts)
  2. 20260314_somalia_screening_results_normalized.json exists
"""

from pathlib import Path
import json
from datetime import datetime
import numpy as np

# ─── Configuration ────────────────────────────────────────────────────────────

# All paths relative to the script's own directory (the GitHub repo folder)
SCRIPT_DIR   = Path(__file__).parent
RESULTS_FILE = SCRIPT_DIR / '20260314_somalia_screening_results_normalized.json'
PORTFOLIO_FILE = SCRIPT_DIR / 'filtered_somalia_portfolio.json'
REPORT_FILE  = SCRIPT_DIR / '20260316_somalia-fcv-portfolio-report.html'

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


# ─── Utility functions (unchanged) ────────────────────────────────────────────

def load_data():
    with open(RESULTS_FILE, encoding='utf-8') as f:
        results = json.load(f)
    with open(PORTFOLIO_FILE, encoding='utf-8') as f:
        portfolio = json.load(f)
    proj_meta = {p['id']: p for p in portfolio}
    return results, proj_meta


def rating_badge(rating):
    cls = {
        'Strong': 'badge-strong',
        'Substantially Addressed': 'badge-subst',
        'Partially Addressed': 'badge-part',
        'Not Addressed': 'badge-not',
        'Not Applicable': 'badge-na',
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
    stats['n'] = len(results)
    stats['n_ipf'] = sum(1 for r in results if r.get('instrument_category') == 'IPF')
    stats['n_dpf'] = sum(1 for r in results if r.get('instrument_category') == 'DPF')
    stats['avg_s'] = sum(sens) / len(sens) if sens else 0
    stats['avg_r'] = sum(resp) / len(resp) if resp else 0

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

    ipf_s = [_s(r) for r in results if r.get('instrument_category') == 'IPF']
    dpf_s = [_s(r) for r in results if r.get('instrument_category') == 'DPF']
    ipf_r = [_r(r) for r in results if r.get('instrument_category') == 'IPF']
    dpf_r = [_r(r) for r in results if r.get('instrument_category') == 'DPF']
    stats['ipf_avg_s'] = sum(ipf_s) / len(ipf_s) if ipf_s else 0
    stats['dpf_avg_s'] = sum(dpf_s) / len(dpf_s) if dpf_s else 0
    stats['ipf_avg_r'] = sum(ipf_r) / len(ipf_r) if ipf_r else 0
    stats['dpf_avg_r'] = sum(dpf_r) / len(dpf_r) if dpf_r else 0

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

    # Hint row at the top of the table body
    hint_row = """
        <tr class="table-hint-row">
          <td colspan="10">
            &#9654;&nbsp; <strong>Click any project row</strong> to expand the full FCV screening results for that project
          </td>
        </tr>"""
    rows.append(hint_row)

    for idx, r in enumerate(sorted(results, key=lambda x: x.get('sensitivity_score') or 0, reverse=True)):
        pid = r['project_id']
        meta = proj_meta.get(pid, {})
        s = r.get('sensitivity_score') or r.get('composites', {}).get('sensitivity', {}).get('numeric_score', 0)
        resp = r.get('responsiveness_score') or r.get('composites', {}).get('responsiveness', {}).get('numeric_score', 0)
        gap = r.get('gap_matrix_cell', '')
        gap_colors = {
            'High FCV integration': '#e8f7e0',
            'Implementation gap': '#fff3e0',
            'Responsive but underanalysed': '#e0f0ff',
            'Low FCV integration': '#fde8e8',
        }
        gap_bg = gap_colors.get(gap, '#f5f5f5')
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
        is_af = any(k in name_lower for k in ['additional financing', 'additional finance'])
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

        detail_id = f'detail-row-{idx}'
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
    best_dim_id  = max(stats['dim_avgs'], key=stats['dim_avgs'].get)
    worst_dim_id = min(stats['dim_avgs'], key=stats['dim_avgs'].get)
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
        'High FCV integration':        ('background:#f0f9f4', '&#9989;'),
        'Implementation gap':          ('background:#fff7ed', '&#9888;'),
        'Responsive but underanalysed':('background:#e8f4fc', '&#8505;'),
        'Low FCV integration':         ('background:#fef2f2', '&#10060;'),
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
  <title>Somalia World Bank Portfolio — FCV Portfolio Screening Report</title>
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
    /* No card boxes — sections are just content blocks separated by space */
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

    /* ── Instrument panels ── */
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
  <span class="top-bar-badge">SOMALIA · FCV TIER 1</span>
</div>

<div class="hero">
  <div class="hero-inner">
    <div class="hero-eyebrow">FCV Portfolio Assessment — Somalia 2015–2024</div>
    <h1>Somalia World Bank Portfolio<br><strong>FCV Portfolio Screening Report</strong></h1>
    <div class="hero-sub">Systematic FCV Portfolio Assessment of {stats['n']} operations approved 2015–2024, applying the WBG FCV Sensitivity and Responsiveness Screener framework.</div>
    <div class="hero-chips">
      <span class="hero-chip">&#128197; {today}</span>
      <span class="hero-chip">&#128203; {stats['n']} projects screened</span>
      <span class="hero-chip">&#128200; Avg sensitivity {stats['avg_s']:.1f} · responsiveness {stats['avg_r']:.1f}</span>
      <span class="hero-chip">Tier 1 — Crisis / Red</span>
    </div>
  </div>
</div>

<div class="page-wrap">

  <div class="toc">
    <h3>Contents</h3>
    <ol>
      <li><a href="#overview">What This Assessment Found</a></li>
      <li><a href="#portfolio">The Portfolio: 40 Projects, 10 Years</a></li>
      <li><a href="#scores">How FCV-Integrated Is the Portfolio?</a></li>
      <li><a href="#dimensions">Where Strengths and Weaknesses Lie</a></li>
      <li><a href="#redflags">Red Flags: Where the Risks Are</a></li>
      <li><a href="#instruments">Does Instrument Type Make a Difference?</a></li>
      <li><a href="#conclusions">What This Means for Somalia Operations</a></li>
      <li><a href="#methodology">Methodology</a></li>
      <li><a href="#annex">Annex — All 40 Projects</a></li>
    </ol>
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="overview">
    <h2>What This Assessment Found</h2>

    <p>This report presents a systematic FCV (Fragility, Conflict and Violence) Portfolio Assessment of the World Bank Group's Somalia portfolio — {stats['n']} operations approved between 2015 and 2024, covering {stats['n_ipf']} Investment Project Financing (IPF) and {stats['n_dpf']} Development Policy Financing (DPF) instruments. Somalia is a country directly affected by FCV challenges, placing it among the most acutely fragile and conflict-affected environments in the Bank's portfolio. That context matters: the bar for FCV integration is high, and operations that would be considered adequate in a less fragile setting need to do considerably more here.</p>

    <p>Each project was assessed against the WBG FCV Sensitivity and Responsiveness Screener, which evaluates eight analytical dimensions across two composites. <strong>FCV Sensitivity</strong> (Dimensions 1–3) measures how well a project understands Somalia's conflict dynamics — its drivers, political economy, and do-no-harm risks. <strong>FCV Responsiveness</strong> (Dimensions 4–8) measures whether the operational design actually adapts to that context: the theory of change, targeting logic, implementation flexibility, results framework, and One WBG integration. Scores run from 1 to 10; 7.0 is the high-performance threshold.</p>

    <p>The headline result is a portfolio that <strong>understands Somalia's FCV context better than it adapts to it</strong>. The average sensitivity score of <strong>{stats['avg_s']:.1f}/10</strong> ({s_rating}) indicates that projects generally engage with conflict analysis. The average responsiveness score of <strong>{stats['avg_r']:.1f}/10</strong> ({r_rating}) indicates that this analysis is not consistently translating into operational design. The gap between these two figures — {stats['avg_s'] - stats['avg_r']:.1f} points — is the central finding of this assessment and the primary target for improvement. On a positive note, both scores have been improving over time ({trend_s:+.2f}/yr sensitivity, {trend_r:+.2f}/yr responsiveness), suggesting the WBG FCV Strategy is having a discernible effect.</p>

    <p>The chart below is the most direct way to see this pattern. It maps all {stats['n']} projects onto a two-by-two matrix defined by their sensitivity and responsiveness scores. Each dot is a project; the star marks the portfolio average. The dominant cluster in the upper-left — {n_impl_gap} projects — represents the 'Implementation Gap': strong conflict analysis, weaker operational response. Only {n_high} projects achieve High FCV Integration (upper-right). {n_low} fall into Low FCV Integration (lower-left), where both analysis and adaptation are insufficient.</p>

    {inline_chart(
        'chart4_sensitivity_vs_responsiveness.png',
        'Portfolio quadrant analysis',
        'Portfolio positioning: each point is one project, plotted by FCV Sensitivity (y-axis) vs FCV Responsiveness (x-axis). '
        'Star (&#9733;) = portfolio average. Quadrant lines at Sensitivity = 6.0, Responsiveness = 5.5.'
    )}

    <p>The gap matrix classification that emerges from this chart can be summarised as follows. The '{'Implementation Gap'}' is by far the most common pattern, affecting {n_impl_gap} of {stats['n']} operations. Operationally, this means projects are diagnosing the right problems but not designing around them — a fixable failure if addressed systematically through quality review processes.</p>

    <div class="stat-grid">
      <div class="stat-card"><div class="value">{stats['n']}</div><div class="label">Projects Screened</div></div>
      <div class="stat-card"><div class="value">{stats['n_ipf']}</div><div class="label">IPF Operations</div></div>
      <div class="stat-card"><div class="value">{stats['n_dpf']}</div><div class="label">DPF Operations</div></div>
      <div class="stat-card"><div class="value">{stats['avg_s']:.1f}</div><div class="label">Avg FCV Sensitivity</div></div>
      <div class="stat-card"><div class="value">{stats['avg_r']:.1f}</div><div class="label">Avg FCV Responsiveness</div></div>
      <div class="stat-card"><div class="value">{stats['any_rf']}</div><div class="label">Projects with ≥1 Red Flag</div></div>
    </div>
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="portfolio">
    <h2>The Portfolio: {stats['n']} Projects, 10 Years</h2>

    <p>The Somalia portfolio screened here spans a decade of World Bank engagement, from 2015 to 2024. It is predominantly investment lending: {stats['n_ipf']} IPF operations across sectors including governance, health, education, infrastructure and social protection, alongside {stats['n_dpf']} DPF operations focused on fiscal consolidation and institutional reform. This instrument mix reflects Somalia's dual needs — building the physical and human capital destroyed by conflict, while simultaneously strengthening the state institutions needed to sustain any gains.</p>

    <p>Approval activity peaked in {peak_year} with {peak_year_count} operations, reflecting a period of intensified WBG engagement following Somalia's re-engagement with the international financial system. The chart below shows this trajectory. Two things are worth noting: the growing DPF series from 2020 onwards, which coincides with the post-COVID macro stabilisation effort; and the sustained IPF pipeline throughout the period, which illustrates the Bank's long-term sectoral commitments even through periods of acute political instability.</p>

    {inline_chart(
        'chart1_portfolio_timeline.png',
        'Portfolio timeline',
        f'Projects approved per year, 2015–2024, by instrument type. IPF operations in blue; DPF in orange.'
    )}
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="scores">
    <h2>How FCV-Integrated Is the Portfolio?</h2>

    <p>The two composite scores — sensitivity and responsiveness — are the main analytical outputs of this assessment. Sensitivity captures the quality of conflict diagnostics and do-no-harm thinking; responsiveness captures how well the operational design follows from that analysis. At portfolio level, the gap between the two is consistent and meaningful: sensitivity averages {stats['avg_s']:.1f}/10 while responsiveness averages {stats['avg_r']:.1f}/10, a {stats['avg_s'] - stats['avg_r']:.1f}-point gap that holds across sectors and approval years.</p>

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

    <p>Broken down by gap matrix position, the distribution reveals the concentration of the implementation gap challenge:</p>

    <table style="max-width:460px">
      <thead><tr><th></th><th>Matrix Position</th><th style="text-align:center">Count</th><th style="text-align:center">Share</th></tr></thead>
      <tbody>{gap_cells_html}</tbody>
    </table>

    <p>Perhaps the most important story in this data is about trajectory rather than absolute levels. Both sensitivity and responsiveness have been improving over the portfolio period at rates of {trend_s:+.2f}/yr and {trend_r:+.2f}/yr respectively. The two charts below illustrate this: each point is an individual project, and the line tracks the annual average. The upward slope in both charts is consistent with the influence of the 2020 WBG FCV Strategy and its operational guidance, which raised analytical expectations for all operations in FCV contexts. The improvement in sensitivity has been somewhat faster than responsiveness, meaning the gap has narrowed but not closed — which is why responsiveness should be the priority focus for the next CPF cycle.</p>

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

    <p>Composite scores are useful summaries but they can hide important variation within them. Looking at the eight dimensions individually, a clearer picture of where the portfolio succeeds and where it falls short becomes visible. The portfolio's strongest dimension is <strong>D{best_dim_id}: {best_dim_name}</strong> (avg {best_dim_score:.1f}/10) — meaning this is the area where FCV thinking is most consistently applied across operations. The weakest is <strong>D{worst_dim_id}: {worst_dim_name}</strong> (avg {worst_dim_score:.1f}/10), which is where the most systematic design gap lies and where investment in TTL capacity and quality review would have the most impact.</p>

    <p>The radar chart below visualises all eight dimensions simultaneously, comparing IPF and DPF instruments against the overall portfolio average. The shape of the radar tells the story: the sensitivity dimensions (left side, D1–D3) form a wider arc than the responsiveness dimensions (right side, D4–D8), confirming the pattern seen in the composite scores. IPF and DPF instruments follow broadly similar profiles, though DPF tends to score higher on sensitivity dimensions — a pattern explained below in the instrument comparison section.</p>

    {inline_chart(
        'chart7_dimension_radar.png',
        'Dimension radar chart',
        'Average scores across all 8 dimensions. IPF = blue; DPF = orange; portfolio average = dashed. Scale 0–10.',
    )}

    <p>For a more granular view, the table and heatmap below show all eight dimensions with their average scores and relative strength bars, followed by individual project scores across the full portfolio. In the heatmap, each column is a project and each row is a dimension. Look for horizontal patterns — rows that are consistently orange or red signal portfolio-wide weaknesses — and vertical patterns, where uniformly green or red columns identify outlier projects worth examining individually. Rows D6 (Implementation Flexibility) and D7 (Results Framework) are typically the weakest, confirming where operational adaptation most consistently falls short.</p>

    <table>
      <thead><tr><th>#</th><th>Dimension</th><th>Composite</th><th style="text-align:center">Avg Score</th><th style="min-width:130px">Relative Strength</th></tr></thead>
      <tbody>{dim_table_rows}</tbody>
    </table>

    {inline_chart(
        'chart5_dimension_heatmap.png',
        'Dimension score heatmap',
        'FCV dimension scores across all 40 projects. Each column = one project; each row = one dimension. Red = low (1–3), amber = moderate (4–6), green = high (7–10).'
    )}
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="redflags">
    <h2>Red Flags: Where the Risks Are</h2>

    <p>Beyond composite scores, the screener flags specific design failures that carry programmatic risk in conflict-affected settings. These 'red flags' are not just analytical labels — they represent concrete gaps that could cause harm, undermine effectiveness, or erode community trust. A project can score reasonably well on average and still carry a serious red flag if, for example, it names a conflict pathway but provides no mitigation, or if its results framework has no FCV-adjusted indicators whatsoever.</p>

    <p>Across the {stats['n']}-project portfolio, {stats['any_rf']} operations trigger at least one red flag. The most prevalent is <strong>{most_common_rf}: {most_common_rf_label}</strong>, which appears in {most_common_rf_count} of {stats['n']} projects ({most_common_rf_pct:.0f}%). The chart below shows the frequency of each flag across the portfolio. Operationally, this finding points to a specific gap in how projects handle distributional risk and conflict sensitivity in their design documents — an issue that a dedicated checklist in the QER/QAE process could systematically address. Projects triggering multiple red flags should be prioritised for FCV Country Coordinator review at concept stage, before design choices become entrenched.</p>

    {inline_chart(
        'chart6_red_flags.png',
        'Red flag frequency',
        f'Frequency of each red flag across the Somalia portfolio (n={stats["n"]}). '
        f'RF1 = Unmitigated Conflict Risk · RF2 = Missing Distributional Analysis · RF3 = OP 7.30 Weakly Handled · RF4 = Elite Capture Unmitigated · RF5 = Macro Framework Unrealistic.'
    )}
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="instruments">
    <h2>Does Instrument Type Make a Difference?</h2>

    <p>One of the structural questions in any portfolio analysis is whether the type of lending instrument shapes FCV quality, independent of the sector or TTL. For Somalia, the answer is yes — and in an interesting direction. DPF operations, despite being policy-based instruments with fewer operational levers, score higher on sensitivity ({stats['dpf_avg_s']:.1f} vs {stats['ipf_avg_s']:.1f} for IPF). This is almost certainly driven by the mandatory Poverty and Social Impact Analysis (PSIA) requirement in DPF design, which creates a floor for conflict-sensitive analysis that most operations meet.</p>

    <p>On responsiveness, the picture reverses slightly. IPF operations score {stats['ipf_avg_r']:.1f} versus {stats['dpf_avg_r']:.1f} for DPF — a modest difference, but one that reflects the structural constraints of the prior-action model. DPF operations have fewer operational flexibility levers available to them (no CERC, no third-party monitoring provisions, no alternative delivery mechanisms), which structurally limits responsiveness scores regardless of analytical quality. The implication for portfolio management is that sensitivity and responsiveness need to be evaluated in instrument-appropriate ways — and that the analytical rigour evident in DPF Program Documents should be actively transferred to IPF design in related sectors.</p>

    <div class="instr-grid">
      <div class="instr-panel">
        <h3 style="color:#009FDA;margin-top:0">IPF Operations (n={stats['n_ipf']})</h3>
        <p style="margin:0 0 4px"><strong>Avg Sensitivity:</strong> {stats['ipf_avg_s']:.1f}/10</p>
        <p style="margin:0"><strong>Avg Responsiveness:</strong> {stats['ipf_avg_r']:.1f}/10</p>
      </div>
      <div class="instr-panel">
        <h3 style="color:#d97706;margin-top:0">DPF Operations (n={stats['n_dpf']})</h3>
        <p style="margin:0 0 4px"><strong>Avg Sensitivity:</strong> {stats['dpf_avg_s']:.1f}/10</p>
        <p style="margin:0"><strong>Avg Responsiveness:</strong> {stats['dpf_avg_r']:.1f}/10</p>
      </div>
    </div>

    <p>The box plots below show the full score distributions by instrument type — not just averages, but spread, medians and outliers. IPF operations show wider dispersion, reflecting the heterogeneous nature of investment lending across sectors. The lower tail of the IPF distribution is the clearest target for improvement: a handful of IPF operations score in the 3–5 range on responsiveness, dragging down the portfolio average. Systematic FCV peer review at concept stage — specifically targeting Dimensions 6 and 7 — would likely raise this lower tail without requiring fundamental design changes.</p>

    {inline_chart(
        'chart8_score_distribution.png',
        'Score distribution by instrument',
        'Distribution of FCV Sensitivity and Responsiveness scores by instrument type. '
        'Box = interquartile range; line = median; whiskers = min/max.'
    )}
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="conclusions">
    <h2>What This Means for Somalia Operations</h2>

    <p>The Somalia portfolio demonstrates {'reasonably strong' if stats['avg_s'] >= 6 else 'mixed'} FCV sensitivity and {'moderate' if 4 <= stats['avg_r'] < 7 else 'strong' if stats['avg_r'] >= 7 else 'weak'} FCV responsiveness across {stats['n']} screened operations. Given Somalia's acute FCV context, the portfolio {'approaches but does not fully meet' if stats['avg_s'] < 7 else 'meets'} the high-performance threshold on sensitivity, and {'falls short of' if stats['avg_r'] < 7 else 'meets'} it on responsiveness. The positive trajectory is encouraging — but the sensitivity-responsiveness gap is structural and will not close without deliberate action.</p>

    <p>Five priorities stand out from this analysis:</p>

    <ol>
      <li><strong>Close the implementation gap through quality assurance.</strong> The most common failure mode — strong analysis not translating into operational adaptation — should be explicitly addressed in QER/QAE processes. FCV Country Coordinator review should include a specific check on whether Dimensions 6 (Implementation Flexibility) and 7 (Results Framework) reflect the conflict analysis in Dimensions 1–3.</li>
      <li><strong>Strengthen Do No Harm provisions at design stage.</strong> Dimension 2 ratings show the most variance across the portfolio. Operations with active stakeholder opposition or known elite capture risks should require explicit mitigation plans as a condition of concept note approval, not as an afterthought.</li>
      <li><strong>Make TPM and adaptive M&amp;E the default, not the exception.</strong> Third-party monitoring and alternative verification arrangements are frequently absent from Somalia IPF results frameworks. Given the access constraints in Somalia, these should be standard provisions, not exceptional ones requiring a separate justification.</li>
      <li><strong>Deepen One WBG integration.</strong> IFC/MIGA engagement is often absent or superficial in Somalia PADs. Given the country's private sector development needs, CMU should explore systematic joint programming — particularly for energy, financial sector and agri-business operations where IFC has a natural role.</li>
      <li><strong>Transfer DPF analytical rigour to IPF design.</strong> The PSIA-level analytical depth evident in DPF Program Documents should actively inform IPF design in related sectors. The Bank has the analytical assets — the challenge is ensuring they flow across instrument types within the same CMU.</li>
    </ol>
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="methodology">
    <h2>Methodology</h2>

    <details class="meth">
      <summary>Click to expand methodology details</summary>
      <div style="padding-top:16px">
        <h3>Data collection</h3>
        <p>Project metadata was retrieved via the World Bank Open Data API (search.worldbank.org), filtering for Somalia (country code: SO), approval year ≥ 2015, and IPF or DPF lending instruments. Document metadata was retrieved using the World Bank Documents and Reports API, prioritising Project Appraisal Documents (PADs) for IPF projects and Program Documents for DPF operations, with Project Papers included where applicable. PDF text was extracted using PyMuPDF (fitz), capped at 120,000 characters per document.</p>
        <h3>FCV screening framework</h3>
        <p>Each document was screened against the WBG FCV Sensitivity and Responsiveness Screener, grounded in the WBG FCV Strategy (2025) and FCV Operational Manual for FCV Country Coordinators (June 2025). Each dimension is rated on a 4-point scale (Strong / Substantially Addressed / Partially Addressed / Not Addressed), converted to a 1–10 numeric scale. Composite scores are weighted averages of contributing dimensions, with red flag deductions applied to the Sensitivity composite (–0.5 per red flag, floor 1). Somalia is a country directly affected by FCV challenges (high FCV intensity).</p>
        <h3>Scope and limitations</h3>
        <ul>
          <li>3 of 43 projects (P152379, P173637, P178887) excluded — no PDF URL available via API</li>
          <li>Text extraction capped at 120,000 characters; later sections of very long PADs may not be captured</li>
          <li>For Additional Financing documents, scoring reflects the AF PAD quality, not the full programme trajectory</li>
          <li>One primary document screened per project; ISRs and Aide-Mémoires not included</li>
        </ul>
      </div>
    </details>
  </div>


  <!-- ══════════════════════════════════════════════ -->
  <div class="report-section" id="annex">
    <h2>Annex — All 40 Projects</h2>

    <p>The table below lists all {stats['n']} screened projects, sorted by FCV Sensitivity score. <strong>Click any row</strong> to expand the full dimension-by-dimension screening results, key finding, and red flag detail for that project. Score colours: <span style="background:#f0f9f4;padding:1px 6px;border-radius:3px;font-size:11px;color:#1a5c38;border:1px solid rgba(26,122,74,.2)">&#9650; ≥ 7.0</span> <span style="background:#fff7ed;padding:1px 6px;border-radius:3px;font-size:11px;color:#7c3d00;border:1px solid rgba(224,123,0,.2)">4.0–6.9</span> <span style="background:#fef2f2;padding:1px 6px;border-radius:3px;font-size:11px;color:#7f1d1d;border:1px solid rgba(185,28,28,.2)">&#9660; &lt; 4.0</span></p>

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


def main():
    print('Somalia FCV Portfolio Report — HTML Generation')
    print('=' * 52)
    print('Loading data...')
    results, proj_meta = load_data()
    print(f'  {len(results)} projects loaded from {RESULTS_FILE}')

    print('Building HTML report...')
    html = build_html(results, proj_meta)

    print(f'Writing {REPORT_FILE.name}...')
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  Saved: {REPORT_FILE}')
    print(f'  Size:  {REPORT_FILE.stat().st_size / 1024:.0f} KB')


if __name__ == '__main__':
    main()
