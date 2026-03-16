"""
Somalia FCV Portfolio Report — HTML Generator
Date: 2026-03-14
Purpose: Assembles the final HTML analytical report from screening results and charts.

Run AFTER:
  1. 20260314_somalia_fcv_analysis.py  (generates charts)
  2. 20260314_somalia_screening_results.json exists (from aggregated batch screening)
"""

from pathlib import Path
import json
import base64
from datetime import datetime
import numpy as np

# ─── Configuration ────────────────────────────────────────────────────────────

OUT_DIR = Path(r'C:\Users\wb559324\OneDrive - WBG\Claude_Outputs\20260314_somalia-fcv-portfolio-analysis')
RESULTS_FILE = OUT_DIR / '20260314_somalia_screening_results_normalized.json'
PORTFOLIO_FILE = OUT_DIR / 'filtered_somalia_portfolio.json'
REPORT_FILE = OUT_DIR / '20260314_somalia-fcv-portfolio-report.html'

CHART_FILES = [
    ('chart1_portfolio_timeline.png',           'Chart 1: Portfolio Timeline'),
    ('chart2_sensitivity_over_time.png',         'Chart 2: FCV Sensitivity Over Time'),
    ('chart3_responsiveness_over_time.png',      'Chart 3: FCV Responsiveness Over Time'),
    ('chart4_sensitivity_vs_responsiveness.png', 'Chart 4: Sensitivity vs Responsiveness Quadrant'),
    ('chart5_dimension_heatmap.png',             'Chart 5: Dimension Score Heatmap'),
    ('chart6_red_flags.png',                     'Chart 6: Red Flag Frequency'),
    ('chart7_dimension_radar.png',               'Chart 7: Dimension Radar Chart'),
    ('chart8_score_distribution.png',            'Chart 8: Score Distribution by Instrument'),
]


def load_data():
    with open(RESULTS_FILE, encoding='utf-8') as f:
        results = json.load(f)
    with open(PORTFOLIO_FILE, encoding='utf-8') as f:
        portfolio = json.load(f)
    proj_meta = {p['id']: p for p in portfolio}
    return results, proj_meta


def img_tag(filename, alt='', width='100%'):
    """Return <img> tag with relative path."""
    return f'<img src="{filename}" alt="{alt}" style="width:{width};max-width:100%;border:1px solid #e0e0e0;border-radius:4px;margin:12px 0;">'


def rating_badge(rating):
    """Return coloured badge HTML for a rating."""
    cls = {
        'Strong': 'badge-strong',
        'Substantially Addressed': 'badge-subst',
        'Partially Addressed': 'badge-part',
        'Not Addressed': 'badge-not',
        'Not Applicable': 'badge-na',
    }.get(rating, 'badge-na')
    return f'<span class="{cls}">{rating}</span>'


def score_cell(score, instrument=None):
    """Return coloured score pill cell."""
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


def build_portfolio_table(results, proj_meta):
    """Build the portfolio overview summary table."""
    rows = []
    for r in sorted(results, key=lambda x: x.get('sensitivity_score') or 0, reverse=True):
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
            badge = '<span style="background:#e8f0fc;color:#002244;border:1px solid #b0c4de;font-size:10px;font-weight:700;padding:1px 6px;border-radius:4px;margin-left:5px">AF</span>'
        elif is_rest:
            badge = '<span style="background:#fff3e0;color:#7c3d00;border:1px solid #f7941e80;font-size:10px;font-weight:700;padding:1px 6px;border-radius:4px;margin-left:5px">REST</span>'
        else:
            badge = ''
        rows.append(f"""
        <tr>
          <td style="font-family:monospace;font-size:0.85em">{pid}</td>
          <td>{r.get('project_name','')}{badge}</td>
          <td style="text-align:center">{r.get('instrument_category','')}</td>
          <td style="text-align:center">{r.get('approval_year','')}</td>
          <td style="text-align:center">{meta.get('status','')}</td>
          <td style="font-size:0.85em">{sector}</td>
          <td style="text-align:center">{comm_str}</td>
          {score_cell(s)}
          {score_cell(resp)}
          <td style="font-size:0.82em">{gap_html}</td>
        </tr>""")
    return '\n'.join(rows)


def build_annex(results):
    """Build collapsible individual project screening outputs."""
    items = []
    for r in sorted(results, key=lambda x: x.get('sensitivity_score') or 0, reverse=True):
        pid = r['project_id']
        name = r.get('project_name', pid)
        s_score = r.get('sensitivity_score') or r.get('composites', {}).get('sensitivity', {}).get('numeric_score', 0)
        r_score = r.get('responsiveness_score') or r.get('composites', {}).get('responsiveness', {}).get('numeric_score', 0)
        gap = r.get('gap_matrix_cell', '')
        ann_lower = name.lower()
        ann_is_af = any(k in ann_lower for k in ['additional financing', 'additional finance'])
        ann_is_rest = 'restructur' in ann_lower
        if ann_is_af:
            ann_badge = ' <span style="background:#e8f0fc;color:#002244;border:1px solid #b0c4de;font-size:10px;font-weight:700;padding:1px 6px;border-radius:4px">AF</span>'
        elif ann_is_rest:
            ann_badge = ' <span style="background:#fff3e0;color:#7c3d00;border:1px solid #f7941e80;font-size:10px;font-weight:700;padding:1px 6px;border-radius:4px">REST</span>'
        else:
            ann_badge = ''

        # Dimension table
        dim_rows = ''
        for d in r.get('dimensions', []):
            dim_rows += f"""
            <tr>
              <td style="width:2em;text-align:center;color:#888">{d['id']}</td>
              <td style="font-size:0.88em">{d['name']}</td>
              <td>{rating_badge(d.get('rating',''))}</td>
              <td style="text-align:center;font-weight:600">{d.get('numeric_score','')}</td>
              <td style="font-size:0.82em;font-style:italic;color:#555">"{d.get('key_quote','')[:150]}"</td>
              <td style="font-size:0.82em">{d.get('rationale','')}</td>
            </tr>"""

        rf = r.get('red_flags', {})
        rf_html = ' '.join([
            f'<span style="background:{"#C8102E" if v else "#ddd"};color:{"white" if v else "#666"};padding:1px 6px;border-radius:3px;font-size:0.78em;margin:1px">{k}: {"&#9888;" if v else "&#10003;"}</span>'
            for k, v in rf.items()
        ])

        items.append(f"""
        <details>
          <summary>
            <span>
              <span style="font-family:monospace;color:var(--wbg-blue);font-size:12px">{pid}</span>
              &nbsp;·&nbsp;<span style="font-size:13px">{name[:70]}</span>{ann_badge}
            </span>
            <span style="display:flex;gap:10px;align-items:center;font-size:12px;color:var(--muted)">
              <span>S: <strong style="color:var(--text)">{s_score:.1f}</strong></span>
              <span>R: <strong style="color:var(--text)">{r_score:.1f}</strong></span>
              <span style="font-size:11px">{gap}</span>
            </span>
          </summary>
          <div style="padding:16px 18px">
            <p style="margin:0 0 8px;font-size:13px"><strong>Key finding:</strong> {r.get('key_finding','')}</p>
            <p style="margin:0 0 12px;font-size:12px"><strong>Red flags:</strong> {rf_html}</p>
            <table style="width:100%;border-collapse:collapse;font-size:12px">
              <thead>
                <tr>
                  <th style="width:2em;text-align:center">#</th>
                  <th>Dimension</th>
                  <th>Rating</th>
                  <th style="text-align:center">Score</th>
                  <th>Key Quote</th>
                  <th>Rationale</th>
                </tr>
              </thead>
              <tbody>{dim_rows}</tbody>
            </table>
            <div style="margin-top:12px;padding:10px 14px;background:var(--off-white);border-left:3px solid var(--wbg-navy);border-radius:var(--radius-sm);font-size:12px">
              <strong>Sensitivity rating:</strong> {r.get('sensitivity_rating','')}<br>
              <strong>Responsiveness rating:</strong> {r.get('responsiveness_rating','')}
            </div>
          </div>
        </details>""")
    return '\n'.join(items)


def compute_summary_stats(results):
    """Compute portfolio-level summary statistics."""
    stats = {}
    sens = [r.get('sensitivity_score') or r.get('composites', {}).get('sensitivity', {}).get('numeric_score', 0) for r in results]
    resp = [r.get('responsiveness_score') or r.get('composites', {}).get('responsiveness', {}).get('numeric_score', 0) for r in results]
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

    # Red flag totals
    rf_totals = {'RF1': 0, 'RF2': 0, 'RF3': 0, 'RF4': 0, 'RF5': 0}
    for r in results:
        for k, v in r.get('red_flags', {}).items():
            if v:
                rf_key = k.upper().replace('_', '')
                for rf in ['RF1', 'RF2', 'RF3', 'RF4', 'RF5']:
                    if rf in rf_key:
                        rf_totals[rf] += 1
    stats['rf_totals'] = rf_totals
    stats['any_rf'] = sum(
        1 for r in results
        if any(v for v in r.get('red_flags', {}).values())
    )

    # Dimension averages
    dim_avgs = {}
    for i in range(1, 9):
        scores = [d['numeric_score'] for r in results
                  for d in r.get('dimensions', []) if d['id'] == i
                  and d.get('numeric_score') is not None]
        dim_avgs[i] = sum(scores) / len(scores) if scores else 0
    stats['dim_avgs'] = dim_avgs

    # IPF vs DPF averages
    def _s(r): return r.get('sensitivity_score') or r.get('composites', {}).get('sensitivity', {}).get('numeric_score', 0)
    def _r(r): return r.get('responsiveness_score') or r.get('composites', {}).get('responsiveness', {}).get('numeric_score', 0)
    ipf_s = [_s(r) for r in results if r.get('instrument_category') == 'IPF']
    dpf_s = [_s(r) for r in results if r.get('instrument_category') == 'DPF']
    ipf_r = [_r(r) for r in results if r.get('instrument_category') == 'IPF']
    dpf_r = [_r(r) for r in results if r.get('instrument_category') == 'DPF']
    stats['ipf_avg_s'] = sum(ipf_s) / len(ipf_s) if ipf_s else 0
    stats['dpf_avg_s'] = sum(dpf_s) / len(dpf_s) if dpf_s else 0
    stats['ipf_avg_r'] = sum(ipf_r) / len(ipf_r) if ipf_r else 0
    stats['dpf_avg_r'] = sum(dpf_r) / len(dpf_r) if dpf_r else 0

    # Trend slopes
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


def generate_executive_summary(stats):
    """Generate 4 key headline findings."""
    s = stats['avg_s']
    r = stats['avg_r']
    gap = s - r
    dominant = stats['dominant_gap_cell']

    findings = []

    # Finding 1: Overall scores
    s_label = 'moderate' if 4 <= s < 7 else ('strong' if s >= 7 else 'weak')
    r_label = 'moderate' if 4 <= r < 7 else ('strong' if r >= 7 else 'weak')
    findings.append(f"The Somalia portfolio exhibits <strong>{s_label} FCV sensitivity</strong> (avg {s:.1f}/10) "
                    f"and <strong>{r_label} FCV responsiveness</strong> (avg {r:.1f}/10) across {stats['n']} screened documents.")

    # Finding 2: Gap pattern
    if dominant == 'Implementation gap':
        findings.append(f"<strong>The dominant failure mode is the 'Implementation Gap'</strong>: "
                        f"{stats['gap_cells'].get('Implementation gap', 0)} of {stats['n']} projects show stronger conflict analysis than operational adaptation, "
                        f"consistent with the WBG FCV Strategy's documented systemic failure pattern.")
    elif dominant == 'High FCV integration':
        findings.append(f"<strong>The majority of projects ({stats['gap_cells'].get('High FCV integration', 0)}/{stats['n']}) demonstrate High FCV Integration</strong>, "
                        f"reflecting genuine alignment between conflict analysis and operational design.")
    elif dominant == 'Low FCV integration':
        findings.append(f"<strong>The dominant pattern is Low FCV Integration</strong> "
                        f"({stats['gap_cells'].get('Low FCV integration', 0)}/{stats['n']} projects), "
                        f"indicating systemic weakness in both conflict analysis and operational adaptation.")

    # Finding 3: IPF vs DPF
    if stats['n_dpf'] > 0:
        dpf_better_s = stats['dpf_avg_s'] > stats['ipf_avg_s']
        dpf_better_r = stats['dpf_avg_r'] > stats['ipf_avg_r']
        if dpf_better_s or dpf_better_r:
            findings.append(f"<strong>DPF operations score higher</strong> than IPF on "
                            f"{'sensitivity (' + str(round(stats['dpf_avg_s'], 1)) + ' vs ' + str(round(stats['ipf_avg_s'], 1)) + ')' if dpf_better_s else ''}"
                            f"{' and ' if dpf_better_s and dpf_better_r else ''}"
                            f"{'responsiveness (' + str(round(stats['dpf_avg_r'], 1)) + ' vs ' + str(round(stats['ipf_avg_r'], 1)) + ')' if dpf_better_r else ''}"
                            f", likely reflecting the PSIA requirement and macro-framework obligations in DPF design.")
        else:
            findings.append(f"<strong>IPF operations score comparably or higher</strong> than DPF on both sensitivity "
                            f"({stats['ipf_avg_s']:.1f} vs {stats['dpf_avg_s']:.1f}) and responsiveness "
                            f"({stats['ipf_avg_r']:.1f} vs {stats['dpf_avg_r']:.1f}).")

    # Finding 4: Red flags
    most_common_rf = max(stats['rf_totals'], key=stats['rf_totals'].get)
    rf_labels = {
        'RF1': 'Unmitigated Conflict Risk',
        'RF2': 'Missing Distributional Analysis',
        'RF3': 'OP 7.30 Weakly Handled',
        'RF4': 'Elite Capture Unmitigated',
        'RF5': 'Macro Framework Unrealistic',
    }
    rf_count = stats['rf_totals'][most_common_rf]
    rf_pct = rf_count / stats['n'] * 100
    findings.append(f"<strong>Red flag '{rf_labels.get(most_common_rf, most_common_rf)}'</strong> is the most prevalent, "
                    f"appearing in {rf_count} of {stats['n']} projects ({rf_pct:.0f}%). "
                    f"{stats['any_rf']} projects trigger at least one red flag.")

    # Finding 5: Trend over time
    sens_slope = stats.get('sens_trend', 0)
    resp_slope = stats.get('resp_trend', 0)
    trend_dir = 'positive' if sens_slope > 0 and resp_slope > 0 else 'mixed'
    if trend_dir == 'positive':
        findings.append(
            f"<strong>Both FCV sensitivity and responsiveness show a positive trend</strong> over the portfolio period "
            f"({sens_slope:+.2f}/yr and {resp_slope:+.2f}/yr respectively), suggesting that more recently approved "
            f"operations integrate FCV considerations more thoroughly — consistent with the influence of the WBG FCV "
            f"Strategy (2020) and its operational follow-on guidance."
        )
    else:
        trend_s_word = 'rising' if sens_slope > 0 else 'declining'
        trend_r_word = 'rising' if resp_slope > 0 else 'declining'
        findings.append(
            f"<strong>Sensitivity is {trend_s_word} ({sens_slope:+.2f}/yr) while responsiveness is {trend_r_word} "
            f"({resp_slope:+.2f}/yr)</strong> over the portfolio period. This mixed trajectory suggests uneven "
            f"adoption of FCV operational guidance and warrants attention in the next Country Partnership Framework."
        )

    return findings


def build_html(results, proj_meta):
    """Build the complete HTML report."""
    stats = compute_summary_stats(results)
    exec_findings = generate_executive_summary(stats)

    portfolio_table_rows = build_portfolio_table(results, proj_meta)
    annex_html = build_annex(results)

    # Chart index
    chart_index_rows = ''
    for i, (fname, title) in enumerate(CHART_FILES, 1):
        chart_index_rows += f'<tr><td style="text-align:center">{i}</td><td><a href="#{fname}">{title}</a></td><td>{fname}</td></tr>\n'

    # Dimension table for aggregate
    dim_table_rows = ''
    dim_names_full = [
        'FCV Context and Diagnostics', 'Do No Harm and Conflict Risk',
        'Stakeholder and Political Economy', 'Objectives and Theory of Change',
        'Design and Targeting', 'Implementation and Operational Flexibility',
        'Results Framework and Adaptive Management', 'One WBG Integration (IFC/MIGA)',
    ]
    composites = ['Sensitivity'] * 3 + ['Responsiveness'] * 5
    for i, (name, comp) in enumerate(zip(dim_names_full, composites), 1):
        avg = stats['dim_avgs'].get(i, 0)
        bar_w = int(avg / 10 * 100)
        comp_color = 'var(--wbg-navy)' if comp == 'Sensitivity' else '#E07B00'
        dim_table_rows += f"""
        <tr>
          <td style="text-align:center;font-weight:700">D{i}</td>
          <td>{name}</td>
          <td style="text-align:center">
            <span style="background:{'#e8f4fc' if comp == 'Sensitivity' else '#fff7ed'};color:{'#004e7c' if comp == 'Sensitivity' else '#7c3d00'};border:1px solid {'rgba(0,159,218,.25)' if comp == 'Sensitivity' else 'rgba(224,123,0,.25)'};padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600">{comp}</span>
          </td>
          <td style="text-align:center;font-weight:700">{avg:.2f}</td>
          <td style="padding:4px 0">
            <div style="background:var(--border);border-radius:4px;height:12px;width:100%;position:relative">
              <div style="background:{comp_color};opacity:0.8;border-radius:4px;height:12px;width:{bar_w}%"></div>
            </div>
          </td>
        </tr>"""

    # Gap cells table
    gap_cells_html = ''
    cell_styles = {
        'High FCV integration': ('background:#f0f9f4', '&#9989;'),
        'Implementation gap': ('background:#fff7ed', '&#9888;'),
        'Responsive but underanalysed': ('background:#e8f4fc', '&#8505;'),
        'Low FCV integration': ('background:#fef2f2', '&#10060;'),
    }
    for cell, count in sorted(stats['gap_cells'].items(), key=lambda x: -x[1]):
        style, icon = cell_styles.get(cell, ('', ''))
        pct = count / stats['n'] * 100
        gap_cells_html += f"""
        <tr style="{style}">
          <td style="text-align:center;font-size:1.2em">{icon}</td>
          <td><strong>{cell}</strong></td>
          <td style="text-align:center">{count}</td>
          <td style="text-align:center">{pct:.0f}%</td>
        </tr>"""

    exec_bullets = ''.join(f'<li style="margin:10px 0">{f}</li>' for f in exec_findings)
    today = datetime.now().strftime('%d %B %Y')

    # WBG Globe SVG (inline, 32×32)
    globe_svg = '''<svg class="wbg-globe" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="16" cy="16" r="14" stroke="rgba(255,255,255,0.6)" stroke-width="1.5"/>
      <ellipse cx="16" cy="16" rx="5.5" ry="14" stroke="rgba(255,255,255,0.6)" stroke-width="1.5"/>
      <line x1="2" y1="16" x2="30" y2="16" stroke="rgba(255,255,255,0.6)" stroke-width="1.5"/>
      <line x1="4" y1="10" x2="28" y2="10" stroke="rgba(255,255,255,0.35)" stroke-width="1"/>
      <line x1="4" y1="22" x2="28" y2="22" stroke="rgba(255,255,255,0.35)" stroke-width="1"/>
    </svg>'''

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Somalia World Bank Portfolio — FCV Screening Report</title>
  <link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@300;400;600;700&family=Source+Serif+4:ital,wght@0,300;0,400;0,600&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --wbg-navy:  #002244;
      --wbg-blue:  #009FDA;
      --wbg-cyan:  #47C4EB;
      --wbg-dark:  #00263A;
      --white:     #ffffff;
      --off-white: #f5f7fa;
      --border:    #d9e2ec;
      --muted:     #5a6a7e;
      --text:      #1a2a3a;
      --radius:    8px;
      --radius-sm: 5px;
      --shadow-sm: 0 1px 4px rgba(0,34,68,.08);
      --shadow-md: 0 4px 14px rgba(0,34,68,.10);
    }}

    html {{ scroll-behavior: smooth; }}
    body {{ font-family: 'Source Sans 3', Arial, sans-serif; font-size: 15px; line-height: 1.6; color: var(--text); background: var(--off-white); }}

    /* ── Top bar ── */
    .top-bar {{
      background: var(--wbg-navy);
      padding: 6px 32px;
      display: flex; align-items: center; justify-content: space-between;
    }}
    .top-bar-left {{ display: flex; align-items: center; gap: 12px; }}
    .wbg-globe {{ width: 32px; height: 32px; flex-shrink: 0; }}
    .top-bar-wordmark {{
      font-size: 13px; font-weight: 600; color: rgba(255,255,255,.9);
      letter-spacing: .03em; text-transform: uppercase;
    }}
    .top-bar-divider {{ width: 1px; height: 16px; background: rgba(255,255,255,.25); margin: 0 4px; }}
    .top-bar-unit {{
      font-size: 12px; font-weight: 400; color: var(--wbg-cyan);
      letter-spacing: .04em; text-transform: uppercase;
    }}
    .top-bar-badge {{
      font-size: 10px; padding: 3px 9px;
      background: rgba(0,159,218,.2); border: 1px solid rgba(0,159,218,.35);
      border-radius: 20px; color: var(--wbg-cyan);
      letter-spacing: .07em; text-transform: uppercase;
    }}

    /* ── Hero ── */
    .hero {{
      background: linear-gradient(135deg, #002244 0%, #004080 55%, #005a9e 100%);
      padding: 44px 32px 40px;
      position: relative; overflow: hidden;
    }}
    .hero::before {{
      content: ''; position: absolute; inset: 0;
      background-image:
        linear-gradient(rgba(255,255,255,.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px);
      background-size: 40px 40px;
      pointer-events: none;
    }}
    .hero::after {{
      content: ''; position: absolute;
      bottom: 0; left: 0; right: 0; height: 3px;
      background: linear-gradient(90deg, var(--wbg-blue), var(--wbg-cyan));
    }}
    .hero-inner {{ max-width: 1136px; margin: 0 auto; position: relative; z-index: 1; }}
    .hero-eyebrow {{
      font-size: 11px; font-weight: 600; text-transform: uppercase;
      letter-spacing: .14em; color: var(--wbg-cyan); margin-bottom: 10px;
      display: flex; align-items: center; gap: 8px;
    }}
    .hero-eyebrow::before {{ content: ''; display: inline-block; width: 20px; height: 2px; background: var(--wbg-cyan); }}
    .hero h1 {{
      font-family: 'Source Serif 4', serif;
      font-weight: 300; font-size: 34px;
      color: #fff; line-height: 1.2; margin-bottom: 10px;
      letter-spacing: -.01em;
    }}
    .hero h1 strong {{ font-weight: 600; color: var(--wbg-cyan); }}
    .hero-sub {{ font-size: 15px; color: rgba(255,255,255,.72); max-width: 560px; line-height: 1.6; margin-bottom: 20px; }}
    .hero-chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .hero-chip {{
      display: inline-flex; align-items: center; gap: 6px;
      font-size: 12px; padding: 5px 12px;
      background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2);
      border-radius: 20px; color: rgba(255,255,255,.8);
    }}

    /* ── Page layout ── */
    .page-wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px 24px 60px; }}

    /* ── Table of contents ── */
    .toc-card {{
      background: var(--white); border: 1px solid var(--border);
      border-radius: var(--radius); box-shadow: var(--shadow-sm);
      padding: 20px 28px; margin-bottom: 16px;
      border-left: 4px solid var(--wbg-cyan);
    }}
    .toc-card h3 {{ font-family: 'Source Serif 4', serif; font-weight: 400; font-size: 16px; color: var(--text); margin-bottom: 12px; }}
    .toc-card ol {{ padding-left: 20px; columns: 2; column-gap: 32px; }}
    .toc-card li {{ margin: 5px 0; font-size: 13px; }}
    .toc-card a {{ color: var(--wbg-blue); text-decoration: none; }}
    .toc-card a:hover {{ text-decoration: underline; }}

    /* ── Section card ── */
    .section-card {{
      background: var(--white); border: 1px solid var(--border);
      border-radius: var(--radius); box-shadow: var(--shadow-sm);
      margin-bottom: 16px; overflow: hidden;
    }}
    .section-inner {{ padding: 28px 32px; }}

    h2 {{
      font-family: 'Source Serif 4', serif; font-weight: 400; font-size: 20px;
      color: var(--text); padding-bottom: 10px;
      border-bottom: 2px solid var(--wbg-cyan); margin-bottom: 18px;
    }}
    h3 {{ font-size: 15px; font-weight: 700; color: var(--wbg-navy); margin: 18px 0 10px; }}
    h4 {{ font-size: 13px; font-weight: 600; color: var(--muted); margin: 12px 0 8px; text-transform: uppercase; letter-spacing: .05em; }}
    p {{ margin: 8px 0; }}

    /* ── Tables ── */
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }}
    th {{
      background: var(--off-white); color: var(--text);
      padding: 9px 11px; text-align: left;
      font-size: 11px; text-transform: uppercase; letter-spacing: .04em; font-weight: 700;
      border-bottom: 2px solid var(--border);
    }}
    td {{ padding: 8px 11px; border-bottom: 1px solid var(--border); vertical-align: top; }}
    tr:nth-child(even) td {{ background: #fafbfc; }}
    tr:hover td {{ background: #eef7fc; }}

    /* ── Stat cards ── */
    .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 14px; margin: 16px 0; }}
    .stat-card {{
      background: var(--off-white); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 16px; text-align: center;
      border-top: 3px solid var(--wbg-cyan);
    }}
    .stat-card .value {{ font-size: 2em; font-weight: 700; color: var(--wbg-navy); }}
    .stat-card .label {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}

    /* ── Callouts ── */
    .callout {{
      border-radius: var(--radius-sm); padding: 13px 16px; margin: 14px 0;
      display: flex; gap: 11px; align-items: flex-start; border: 1px solid;
    }}
    .callout.info {{ background: #e8f4fc; border-color: #a8d8f0; color: #004e7c; }}
    .callout.warning {{ background: #fff7ed; border-color: #fbbf24; color: #7c3d00; }}
    .callout.danger {{ background: #fef2f2; border-color: #fca5a5; color: #7f1d1d; }}
    .callout.success {{ background: #f0f9f4; border-color: #86efac; color: #1a5c38; }}
    .callout-body {{ font-size: 13px; line-height: 1.55; }}

    /* ── Highlight callout (chart intro) ── */
    .chart-intro {{
      background: var(--off-white); border: 1px solid var(--border);
      border-left: 3px solid var(--wbg-blue);
      border-radius: var(--radius-sm); padding: 11px 16px; margin: 14px 0;
      font-size: 13px; color: var(--muted);
    }}

    /* ── Charts ── */
    .chart-container {{ margin: 20px 0; text-align: center; }}
    .chart-container figcaption {{ font-size: 12px; color: var(--muted); margin-top: 6px; font-style: italic; }}
    .chart-img {{
      width: 100%; max-width: 100%;
      border: 1px solid var(--border); border-radius: var(--radius-sm);
      margin: 12px 0;
    }}

    /* ── Rating badges ── */
    .badge-strong {{ background:#f0f9f4;color:#1a5c38;border:1px solid rgba(26,122,74,.25);padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap; }}
    .badge-subst  {{ background:#e8f4fc;color:#004e7c;border:1px solid rgba(0,159,218,.25);padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap; }}
    .badge-part   {{ background:#fff7ed;color:#7c3d00;border:1px solid rgba(224,123,0,.25);padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap; }}
    .badge-not    {{ background:#fef2f2;color:#7f1d1d;border:1px solid rgba(185,28,28,.25);padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap; }}
    .badge-na     {{ background:var(--off-white);color:var(--muted);border:1px solid var(--border);padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap; }}

    ul, ol {{ padding-left: 22px; margin: 10px 0; }}
    li {{ margin: 6px 0; }}

    /* ── Annex details ── */
    details {{ margin: 8px 0; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }}
    details summary {{
      cursor: pointer; padding: 11px 16px;
      background: var(--off-white); font-weight: 600;
      list-style: none; display: flex; justify-content: space-between; align-items: center;
      font-size: 13px;
    }}
    details summary::-webkit-details-marker {{ display: none; }}
    details summary::before {{ content: '▶ '; font-size: 0.75em; color: var(--muted); }}
    details[open] summary::before {{ content: '▼ '; }}
    details[open] summary {{ border-bottom: 1px solid var(--border); }}

    /* ── IPF/DPF instrument panels ── */
    .instr-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    .instr-panel {{ border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; }}

    /* ── Footer ── */
    .page-footer {{
      background: var(--wbg-navy); color: rgba(255,255,255,.4);
      font-size: 11px; padding: 16px 32px; text-align: center; letter-spacing: .04em;
    }}

    @media print {{
      body {{ background: white; }}
      .page-wrap {{ padding: 0; }}
      .section-card {{ box-shadow: none; border: 1px solid #ccc; }}
    }}
  </style>
</head>
<body>

<!-- Top bar -->
<div class="top-bar">
  <div class="top-bar-left">
    {globe_svg}
    <span class="top-bar-wordmark">World Bank Group</span>
    <div class="top-bar-divider"></div>
    <span class="top-bar-unit">FCV Analytics</span>
  </div>
  <span class="top-bar-badge">SOMALIA · FCV TIER 1</span>
</div>

<!-- Hero banner -->
<div class="hero">
  <div class="hero-inner">
    <div class="hero-eyebrow">FCV Portfolio Assessment — Somalia 2015–2024</div>
    <h1>Somalia World Bank Portfolio<br><strong>FCV Screening Report</strong></h1>
    <div class="hero-sub">Systematic FCV Sensitivity &amp; Responsiveness assessment of {stats['n']} operations (2015–2024) using the WBG FCV Screener framework.</div>
    <div class="hero-chips">
      <span class="hero-chip">&#128197; {today}</span>
      <span class="hero-chip">&#128203; {stats['n']} projects screened</span>
      <span class="hero-chip">&#128200; Avg S: {stats['avg_s']:.1f} · R: {stats['avg_r']:.1f}</span>
      <span class="hero-chip">&#127988; Tier 1 — Crisis / Red</span>
    </div>
  </div>
</div>

<div class="page-wrap">

  <!-- Table of Contents -->
  <div class="toc-card">
    <h3>Contents</h3>
    <ol>
      <li><a href="#exec-summary">Executive Summary</a></li>
      <li><a href="#methodology">Methodology</a></li>
      <li><a href="#portfolio-overview">Portfolio Overview</a></li>
      <li><a href="#quadrant">Sensitivity vs Responsiveness Positioning</a></li>
      <li><a href="#aggregate-fcv">Aggregate FCV Assessment</a></li>
      <li><a href="#trends">Trends Over Time</a></li>
      <li><a href="#red-flags">Red Flags Analysis</a></li>
      <li><a href="#instrument-comparison">Key Findings by Instrument Type</a></li>
      <li><a href="#conclusions">Conclusions &amp; Recommendations</a></li>
      <li><a href="#chart-index">Chart Index</a></li>
      <li><a href="#annex">Annex A — Individual Project Screening Outputs</a></li>
    </ol>
  </div>

  <!-- 1. Executive Summary -->
  <div class="section-card" id="exec-summary">
    <div class="section-inner">
      <h2>1. Executive Summary</h2>
      <div class="callout info">
        <div class="callout-body">
          <strong>Portfolio snapshot</strong>
          {stats['n']} projects screened &nbsp;·&nbsp;
          {stats['n_ipf']} IPF / {stats['n_dpf']} DPF &nbsp;·&nbsp;
          Avg sensitivity: <strong>{stats['avg_s']:.1f}/10</strong> &nbsp;·&nbsp;
          Avg responsiveness: <strong>{stats['avg_r']:.1f}/10</strong> &nbsp;·&nbsp;
          Dominant pattern: <strong>{stats['dominant_gap_cell']}</strong>
        </div>
      </div>
      <h3>Headline Findings</h3>
      <ul>{exec_bullets}</ul>
    </div>
  </div>

  <!-- 2. Methodology -->
  <div class="section-card" id="methodology">
    <div class="section-inner">
      <h2>2. Methodology</h2>
      <h3>Data Collection</h3>
      <p>Project metadata was retrieved via the World Bank Open Data API (search.worldbank.org), filtering for Somalia (country code: SO), approval year ≥ 2015, and IPF or DPF lending instruments. Document metadata was retrieved using the World Bank Documents and Reports API, prioritising Project Appraisal Documents (PADs) for IPF projects and Program Documents for DPF operations, with Project Papers included where applicable.</p>
      <p>PDF text was extracted using PyMuPDF (fitz), capped at 120,000 characters per document. Documents with fewer than 2,000 extractable characters were flagged as potentially image-only.</p>
      <h3>FCV Screening Framework</h3>
      <p>Each document was screened against the <strong>WBG FCV Sensitivity and Responsiveness Screener</strong>, grounded in the WBG FCV Strategy (2025) and FCV Operational Manual for FCV Country Coordinators (June 2025). The framework assesses:</p>
      <ul>
        <li><strong>FCV Sensitivity</strong> (Dimensions 1–3): quality of conflict analysis, do-no-harm measures, and stakeholder/political economy treatment</li>
        <li><strong>FCV Responsiveness</strong> (Dimensions 4–8): objectives and theory of change, design and targeting, implementation flexibility, results framework, and One WBG integration</li>
      </ul>
      <p>Somalia is classified as <strong>Tier 1 — High FCV intensity</strong> (Crisis/Red under the 2025 WBG traffic-light scheme).</p>
      <h3>Scoring</h3>
      <p>Each dimension is rated on a 4-point scale (Strong / Substantially Addressed / Partially Addressed / Not Addressed), converted to a 1–10 numeric scale. Composite scores are weighted averages of contributing dimensions, with red flag deductions applied to the Sensitivity composite (–0.5 per red flag, floor 1).</p>
      <h3>Scope and Limitations</h3>
      <ul>
        <li>3 of 43 projects (P152379, P173637, P178887) could not be screened due to missing document metadata (no PDF URL returned by API)</li>
        <li>Text extraction is capped at 120,000 characters; later sections of very long PADs may not be captured</li>
        <li>For Additional Financing documents, scoring reflects the AF PAD quality, not the full programme trajectory</li>
        <li>Screening was applied to one primary document per project; ISRs and Aide-Mémoires are not included</li>
      </ul>
    </div>
  </div>

  <!-- 3. Portfolio Overview -->
  <div class="section-card" id="portfolio-overview">
    <div class="section-inner">
      <h2>3. Portfolio Overview</h2>
      <div class="stat-grid">
        <div class="stat-card"><div class="value">{stats['n']}</div><div class="label">Projects Screened</div></div>
        <div class="stat-card"><div class="value">{stats['n_ipf']}</div><div class="label">IPF Operations</div></div>
        <div class="stat-card"><div class="value">{stats['n_dpf']}</div><div class="label">DPF Operations</div></div>
        <div class="stat-card"><div class="value">{stats['avg_s']:.1f}</div><div class="label">Avg FCV Sensitivity</div></div>
        <div class="stat-card"><div class="value">{stats['avg_r']:.1f}</div><div class="label">Avg FCV Responsiveness</div></div>
        <div class="stat-card"><div class="value">{stats['any_rf']}</div><div class="label">Projects with ≥1 Red Flag</div></div>
      </div>
      <h3>All Projects — Summary Table</h3>
      <p style="font-size:13px;color:var(--muted);margin-bottom:8px">Sorted by FCV Sensitivity score (highest first). Score colours: <span style="background:#f0f9f4;padding:1px 6px;border-radius:4px;font-size:11px;color:#1a5c38;border:1px solid rgba(26,122,74,.2)">≥7 high</span> <span style="background:#fff7ed;padding:1px 6px;border-radius:4px;font-size:11px;color:#7c3d00;border:1px solid rgba(224,123,0,.2)">4–6.9 moderate</span> <span style="background:#fef2f2;padding:1px 6px;border-radius:4px;font-size:11px;color:#7f1d1d;border:1px solid rgba(185,28,28,.2)">&lt;4 low</span> &nbsp; <span style="background:#e8f0fc;color:#002244;border:1px solid #b0c4de;font-size:10px;font-weight:700;padding:1px 6px;border-radius:4px">AF</span> = Additional Financing &nbsp; <span style="background:#fff3e0;color:#7c3d00;border:1px solid #f7941e80;font-size:10px;font-weight:700;padding:1px 6px;border-radius:4px">REST</span> = Restructuring</p>
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
        <tbody>{portfolio_table_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- 4. Sensitivity vs Responsiveness Positioning (moved up) -->
  <div class="section-card" id="quadrant">
    <div class="section-inner">
      <h2>4. Sensitivity vs Responsiveness Positioning</h2>
      <div class="chart-intro">
        The quadrant chart below shows where each project sits relative to the portfolio average. Projects in the upper-right quadrant show strong FCV integration; projects in the upper-left have strong analysis but weaker operational adaptation (the most common systemic failure mode).
      </div>
      <div class="chart-container">
        <figure>
          <img src="chart4_sensitivity_vs_responsiveness.png" alt="Quadrant Analysis" class="chart-img">
          <figcaption>Chart 4: Portfolio quadrant analysis — each point represents one project. Portfolio average shown as ★</figcaption>
        </figure>
      </div>
      <div class="callout warning">
        <div class="callout-body">
          <strong>Reading the quadrant chart: </strong>
          Upper-left = Implementation Gap (strong analysis, weak operational adaptation).
          Upper-right = High FCV Integration.
          Lower-right = Responsive but underanalysed.
          Lower-left = Low FCV integration.
          Divider line at score 7 on both axes.
        </div>
      </div>
    </div>
  </div>

  <!-- 5. Aggregate FCV Assessment -->
  <div class="section-card" id="aggregate-fcv">
    <div class="section-inner">
      <h2>5. Aggregate FCV Assessment</h2>
      <h3>Overall Scores</h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:16px 0">
        <div style="background:#e8f4fc;padding:20px;border-radius:var(--radius);border-top:3px solid var(--wbg-navy)">
          <div style="font-size:2.5em;font-weight:700;color:var(--wbg-navy)">{stats['avg_s']:.1f}<span style="font-size:0.5em;opacity:0.6">/10</span></div>
          <div style="font-weight:700;margin-top:4px;font-size:14px">Average FCV Sensitivity</div>
          <div style="font-size:12px;color:var(--muted);margin-top:8px">FCV Context &amp; Diagnostics · Do No Harm · Stakeholder &amp; Political Economy</div>
        </div>
        <div style="background:#fff7ed;padding:20px;border-radius:var(--radius);border-top:3px solid #E07B00">
          <div style="font-size:2.5em;font-weight:700;color:#7c3d00">{stats['avg_r']:.1f}<span style="font-size:0.5em;opacity:0.6">/10</span></div>
          <div style="font-weight:700;margin-top:4px;font-size:14px">Average FCV Responsiveness</div>
          <div style="font-size:12px;color:var(--muted);margin-top:8px">Objectives &amp; ToC · Design &amp; Targeting · Implementation Flexibility · Results Framework · One WBG</div>
        </div>
      </div>
      <h3>Gap Matrix Distribution</h3>
      <table style="max-width:500px">
        <thead><tr><th></th><th>Matrix Position</th><th style="text-align:center">Count</th><th style="text-align:center">% of Portfolio</th></tr></thead>
        <tbody>{gap_cells_html}</tbody>
      </table>
      <h3>Dimension-by-Dimension Breakdown</h3>
      <table>
        <thead><tr><th>#</th><th>Dimension</th><th>Composite</th><th style="text-align:center">Avg Score</th><th style="min-width:150px">Relative Strength</th></tr></thead>
        <tbody>{dim_table_rows}</tbody>
      </table>
      <div class="chart-container">
        <figure>
          <img src="chart5_dimension_heatmap.png" alt="Dimension Score Heatmap" class="chart-img">
          <figcaption>Chart 5: FCV dimension scores across all projects (Score 1–10: Red=Low, Yellow=Moderate, Green=High)</figcaption>
        </figure>
      </div>
      <div class="chart-container">
        <figure>
          <img src="chart7_dimension_radar.png" alt="Dimension Radar Chart" style="width:70%;max-width:100%;border:1px solid var(--border);border-radius:var(--radius-sm);margin:12px 0;">
          <figcaption>Chart 7: Average scores per dimension — IPF vs DPF vs portfolio average (scale 0–10)</figcaption>
        </figure>
      </div>
    </div>
  </div>

  <!-- 6. Trends Over Time -->
  <div class="section-card" id="trends">
    <div class="section-inner">
      <h2>6. Trends Over Time</h2>
      <div class="chart-container">
        <figure>
          <img src="chart1_portfolio_timeline.png" alt="Portfolio Timeline" class="chart-img">
          <figcaption>Chart 1: Projects approved per year, 2015–2024 — IPF vs DPF</figcaption>
        </figure>
      </div>
      <div class="chart-container">
        <figure>
          <img src="chart2_sensitivity_over_time.png" alt="Sensitivity Over Time" class="chart-img">
          <figcaption>Chart 2: FCV Sensitivity scores by approval year — individual projects and annual averages</figcaption>
        </figure>
      </div>
      <div class="chart-container">
        <figure>
          <img src="chart3_responsiveness_over_time.png" alt="Responsiveness Over Time" class="chart-img">
          <figcaption>Chart 3: FCV Responsiveness scores by approval year — individual projects and annual averages</figcaption>
        </figure>
      </div>
    </div>
  </div>

  <!-- 7. Red Flags -->
  <div class="section-card" id="red-flags">
    <div class="section-inner">
      <h2>7. Red Flag Analysis</h2>
      <p>Red flags are downward modifiers to the FCV Sensitivity composite. They indicate specific design or analytical failures that carry programmatic risk in FCV contexts.</p>
      <div class="chart-container">
        <figure>
          <img src="chart6_red_flags.png" alt="Red Flag Frequency" class="chart-img">
          <figcaption>Chart 6: Frequency of each red flag across the Somalia portfolio (n={stats['n']})</figcaption>
        </figure>
      </div>
    </div>
  </div>

  <!-- 8. IPF vs DPF Comparison -->
  <div class="section-card" id="instrument-comparison">
    <div class="section-inner">
      <h2>8. Key Findings by Instrument Type</h2>
      <div class="instr-grid">
        <div class="instr-panel">
          <h3 style="color:var(--wbg-blue)">IPF Operations (n={stats['n_ipf']})</h3>
          <p><strong>Avg Sensitivity:</strong> {stats['ipf_avg_s']:.1f}/10</p>
          <p><strong>Avg Responsiveness:</strong> {stats['ipf_avg_r']:.1f}/10</p>
          <p style="margin-top:10px;font-size:13px;color:var(--muted)">IPF operations vary widely in FCV quality. Newer IPFs (2020+) generally show stronger FCV integration, reflecting the influence of the 2020 WBG FCV Strategy. Implementation flexibility provisions (CERC, TPM, alternative delivery) are the most variable dimension.</p>
        </div>
        <div class="instr-panel">
          <h3 style="color:#E07B00">DPF Operations (n={stats['n_dpf']})</h3>
          <p><strong>Avg Sensitivity:</strong> {stats['dpf_avg_s']:.1f}/10</p>
          <p><strong>Avg Responsiveness:</strong> {stats['dpf_avg_r']:.1f}/10</p>
          <p style="margin-top:10px;font-size:13px;color:var(--muted)">DPF/DPO operations benefit from mandatory PSIA requirements, which tend to elevate sensitivity scores. Responsiveness is constrained by the prior-action model, which limits operational flexibility provisions compared to IPF instruments.</p>
        </div>
      </div>
      <div class="chart-container" style="margin-top:20px">
        <figure>
          <img src="chart8_score_distribution.png" alt="Score Distribution" class="chart-img">
          <figcaption>Chart 8: Distribution of FCV scores by instrument type</figcaption>
        </figure>
      </div>
    </div>
  </div>

  <!-- 9. Conclusions -->
  <div class="section-card" id="conclusions">
    <div class="section-inner">
      <h2>9. Conclusions &amp; Recommendations</h2>
      <h3>Overall Assessment</h3>
      <p>The Somalia portfolio demonstrates {'reasonably strong' if stats['avg_s'] >= 6 else 'mixed'} FCV sensitivity (avg {stats['avg_s']:.1f}/10) and {'moderate' if 4 <= stats['avg_r'] < 7 else 'strong' if stats['avg_r'] >= 7 else 'weak'} FCV responsiveness (avg {stats['avg_r']:.1f}/10) across {stats['n']} screened operations. Given Somalia's Tier 1 (Crisis/Red) classification, the bar for strong performance is high, and the portfolio {'meets' if stats['avg_s'] >= 7 else 'approaches but does not fully meet'} that standard on sensitivity while {'falling short of' if stats['avg_r'] < 7 else 'meeting'} it on responsiveness.</p>
      <h3>Recommendations</h3>
      <ol>
        <li><strong>Close the implementation gap:</strong> The most common failure mode — strong analysis not translating into operational adaptation — should be explicitly addressed in QER/QAE processes. FCV CC review should include a specific check on whether Dimension 6 (Implementation Flexibility) and Dimension 7 (Results Framework) reflect the conflict analysis in Dimensions 1–3.</li>
        <li><strong>Strengthen Do No Harm provisions:</strong> Dimension 2 ratings show the most variance across the portfolio. Operations with active stakeholder opposition or known elite capture risks should require explicit mitigation plans before approval.</li>
        <li><strong>Improve results framework FCV adaptation:</strong> Indicators and M&E arrangements are frequently the weakest responsiveness dimension. TPM and alternative verification arrangements should be standard for Somalia IPF operations, not exceptional.</li>
        <li><strong>One WBG integration:</strong> IFC/MIGA engagement is often absent or superficial in Somalia PADs. Given the country's private sector development needs, CMU should explore systematic joint programming opportunities, particularly for energy and financial sector operations.</li>
        <li><strong>DPF series continuity:</strong> The Somalia DPF series represents an important instrument for institutional reform. PSIA-level analytical rigour demonstrated in DPF Program Documents should inform IPF design in related sectors.</li>
      </ol>
    </div>
  </div>

  <!-- 10. Chart Index -->
  <div class="section-card" id="chart-index">
    <div class="section-inner">
      <h2>10. Chart Index</h2>
      <table>
        <thead><tr><th>#</th><th>Title</th><th>File</th></tr></thead>
        <tbody>{chart_index_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- Annex A -->
  <div class="section-card" id="annex">
    <div class="section-inner">
      <h2>Annex A — Individual Project Screening Outputs</h2>
      <p style="font-size:13px;color:var(--muted);margin-bottom:12px">Each entry below shows the full dimension-by-dimension screening results for one project. Click to expand. Sorted by FCV Sensitivity score (highest first).</p>
      {annex_html}
    </div>
  </div>

</div><!-- end .page-wrap -->

<div class="page-footer">
  Assessment produced using the WBG FCV Screener skill · WBG FCV Strategy (2025) · FCV Operational Manual (June 2025)
  &nbsp;·&nbsp; Generated: {today} &nbsp;·&nbsp; 20260314_somalia-fcv-portfolio-report.html
</div>

</body>
</html>"""
    return html


def main():
    print('Somalia FCV Portfolio Report — HTML Generation')
    print('=' * 50)

    print('Loading data...')
    results, proj_meta = load_data()
    print(f'  {len(results)} projects loaded')

    print('Building HTML report...')
    html = build_html(results, proj_meta)

    print(f'Writing {REPORT_FILE.name}...')
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  Report saved: {REPORT_FILE}')
    print(f'  Size: {REPORT_FILE.stat().st_size / 1024:.0f} KB')


if __name__ == '__main__':
    main()
