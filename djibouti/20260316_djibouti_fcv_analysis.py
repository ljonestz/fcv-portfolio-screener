"""
Djibouti FCV Portfolio Analysis — Chart Generation Script
Date: 2026-03-16
Purpose: Reads FCV screening results JSON and generates 8 analytical charts
         for the Djibouti World Bank Portfolio FCV Assessment Report.

All paths are relative to this script's directory (Path(__file__).parent).

Inputs:
  - 20260316_djibouti_screening_results_normalized.json
  - filtered_djibouti_portfolio.json

Outputs (8 PNG charts at 150 dpi):
  - chart1_portfolio_timeline.png
  - chart2_sensitivity_over_time.png
  - chart3_responsiveness_over_time.png
  - chart4_sensitivity_vs_responsiveness.png
  - chart5_dimension_heatmap.png
  - chart6_red_flags.png
  - chart7_dimension_radar.png
  - chart8_score_distribution.png
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

# ─── Configuration ─────────────────────────────────────────────────────────────

SCRIPT_DIR     = Path(__file__).parent
RESULTS_FILE   = SCRIPT_DIR / '20260316_djibouti_screening_results_normalized.json'
PORTFOLIO_FILE = SCRIPT_DIR / 'filtered_djibouti_portfolio.json'

# World Bank colour palette
WB_BLUE   = '#002244'
WB_CYAN   = '#009FE3'
WB_ORANGE = '#F7941E'
WB_GREEN  = '#76BC21'
WB_RED    = '#C8102E'
WB_GREY   = '#6D6E71'
WB_LIGHT  = '#E8F4FD'

SENSITIVITY_COLOR    = WB_BLUE
RESPONSIVENESS_COLOR = WB_ORANGE
IPF_COLOR = WB_CYAN

DIM_NAMES_SHORT = [
    'FCV Context\n& Diagnostics',
    'Do No\nHarm',
    'Stakeholder &\nPol. Economy',
    'Objectives &\nToC',
    'Design &\nTargeting',
    'Implementation\n& Flexibility',
    'Results &\nAdaptive Mgmt',
    'One WBG\nIntegration',
]

RATING_TO_NUM = {
    'Strong': 3,
    'Substantially Addressed': 2,
    'Partially Addressed': 1,
    'Not Addressed': 0,
    'Not Applicable': np.nan,
}

RATING_COLORS = {
    'Strong': WB_GREEN,
    'Substantially Addressed': WB_CYAN,
    'Partially Addressed': WB_ORANGE,
    'Not Addressed': WB_RED,
}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def load_data():
    with open(RESULTS_FILE, encoding='utf-8') as f:
        results = json.load(f)
    with open(PORTFOLIO_FILE, encoding='utf-8') as f:
        portfolio = json.load(f)

    proj_meta = {p['id']: p for p in portfolio}

    rows = []
    for r in results:
        pid = r['project_id']
        meta = proj_meta.get(pid, {})
        row = {
            'project_id':   pid,
            'project_name': r.get('project_name', ''),
            'instrument':   r.get('instrument_category', 'IPF'),
            'year':         r.get('approval_year'),
            'status':       meta.get('status', ''),
            'sector':       meta.get('sector1', {}).get('Name', '') if isinstance(meta.get('sector1'), dict) else '',
            'sensitivity':  r.get('sensitivity_score') or 0,
            'responsiveness': r.get('responsiveness_score') or 0,
            'gap_cell':     r.get('gap_matrix_cell', ''),
            'key_finding':  r.get('key_finding', ''),
        }
        for d in r.get('dimensions', []):
            row[f"d{d['id']}_score"]  = d.get('numeric_score', 0)
            row[f"d{d['id']}_rating"] = d.get('rating', 'Not Addressed')
        rf = r.get('red_flags', {})
        for k, v in rf.items():
            row[f'rf_{k.lower()}'] = v
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


def setup_style():
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 10,
        'axes.titlesize': 13,
        'axes.labelsize': 11,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'grid.alpha': 0.3,
        'grid.linestyle': '--',
    })


def save_chart(fig, name):
    path = SCRIPT_DIR / name
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'  Saved: {name}')
    return str(path)


# ─── Chart 1: Portfolio Timeline ───────────────────────────────────────────────

def chart1_portfolio_timeline(df):
    """Stacked bar: projects approved per year (all IPF for Djibouti)."""
    fig, ax = plt.subplots(figsize=(12, 5))

    year_instr = df.groupby(['year', 'instrument']).size().unstack(fill_value=0)
    for col in ['IPF', 'DPF', 'P4R']:
        if col not in year_instr.columns:
            year_instr[col] = 0

    years = year_instr.index.tolist()
    x = np.arange(len(years))
    width = 0.6

    bars_ipf = ax.bar(x, year_instr['IPF'], width, label='IPF', color=IPF_COLOR, alpha=0.9)
    bars_dpf = ax.bar(x, year_instr['DPF'], width, bottom=year_instr['IPF'],
                      label='DPF', color=WB_ORANGE, alpha=0.9)
    bars_p4r = ax.bar(x, year_instr['P4R'], width,
                      bottom=year_instr['IPF'] + year_instr['DPF'],
                      label='P4R', color=WB_GREEN, alpha=0.9)

    for i, (y_ipf, y_dpf, y_p4r) in enumerate(zip(year_instr['IPF'], year_instr['DPF'], year_instr['P4R'])):
        total = y_ipf + y_dpf + y_p4r
        if y_ipf > 0:
            ax.text(x[i], y_ipf / 2, str(int(y_ipf)), ha='center', va='center',
                    color='white', fontweight='bold', fontsize=9)
        if y_dpf > 0:
            ax.text(x[i], y_ipf + y_dpf / 2, str(int(y_dpf)), ha='center', va='center',
                    color='white', fontweight='bold', fontsize=9)
        if y_p4r > 0:
            ax.text(x[i], y_ipf + y_dpf + y_p4r / 2, str(int(y_p4r)), ha='center', va='center',
                    color='white', fontweight='bold', fontsize=9)
        ax.text(x[i], total + 0.05, str(int(total)), ha='center', va='bottom',
                color=WB_GREY, fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years])
    ax.set_xlabel('Approval Year')
    ax.set_ylabel('Number of Projects')
    ax.set_title('Chart 1: Djibouti World Bank Portfolio — Projects Approved per Year (2015–2024)', pad=15)

    # Only show legend entries with non-zero totals
    handles, labels = [], []
    for bar, lbl in [(bars_ipf[0], 'IPF'), (bars_dpf[0], 'DPF'), (bars_p4r[0], 'P4R')]:
        if year_instr[lbl].sum() > 0:
            handles.append(bar)
            labels.append(lbl)
    if handles:
        ax.legend(handles, labels, frameon=False)

    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.set_ylim(0, year_instr.sum(axis=1).max() + 1.5)
    ax.grid(axis='y', alpha=0.3)

    total_ipf = int(year_instr['IPF'].sum())
    total_dpf = int(year_instr['DPF'].sum())
    total_p4r = int(year_instr['P4R'].sum())
    total_all = total_ipf + total_dpf + total_p4r
    breakdown = ', '.join([f'{n} {t}' for t, n in [('IPF', total_ipf), ('DPF', total_dpf), ('P4R', total_p4r)] if n > 0])
    ax.text(0.98, 0.97, f'Total: {total_all} projects\n({breakdown})',
            transform=ax.transAxes, ha='right', va='top', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.4', facecolor=WB_LIGHT, edgecolor=WB_BLUE, alpha=0.8))

    fig.tight_layout()
    return save_chart(fig, 'chart1_portfolio_timeline.png')


# ─── Chart 2: Sensitivity Over Time ────────────────────────────────────────────

def chart2_sensitivity_over_time(df):
    fig, ax = plt.subplots(figsize=(12, 5))

    for _, row in df.iterrows():
        ax.scatter(row['year'], row['sensitivity'], marker='o', s=60,
                   color=IPF_COLOR, alpha=0.7, zorder=3)

    yearly_avg = df.groupby('year')['sensitivity'].mean()
    ax.plot(yearly_avg.index, yearly_avg.values, color=SENSITIVITY_COLOR,
            linewidth=2.5, marker='D', markersize=8, label='Annual average', zorder=4)

    years_arr = df['year'].values.astype(float)
    scores_arr = df['sensitivity'].values
    if len(years_arr) > 2:
        z = np.polyfit(years_arr, scores_arr, 1)
        p = np.poly1d(z)
        x_trend = np.linspace(years_arr.min(), years_arr.max(), 100)
        ax.plot(x_trend, p(x_trend), '--', color=WB_GREY, linewidth=1.5,
                alpha=0.7, label=f'Trend (slope: {z[0]:+.2f}/yr)')

    ax.axhspan(7, 10, alpha=0.08, color=WB_GREEN, label='High sensitivity zone (>=7)')
    ax.axhspan(4, 7,  alpha=0.05, color=WB_ORANGE)
    ax.axhspan(1, 4,  alpha=0.05, color=WB_RED)

    ipf_patch = mpatches.Patch(color=IPF_COLOR, alpha=0.7, label='IPF project')
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles + [ipf_patch], labels + ['IPF project'],
              frameon=False, loc='lower right', fontsize=9)

    ax.set_xlabel('Approval Year')
    ax.set_ylabel('FCV Sensitivity Score (1-10)')
    ax.set_title('Chart 2: FCV Sensitivity Scores by Approval Year\nDjibouti Portfolio (2015-2024)', pad=15)
    ax.set_ylim(0, 10.5)
    ax.grid(axis='y', alpha=0.3)
    ax.set_xticks(sorted(df['year'].unique()))

    fig.tight_layout()
    return save_chart(fig, 'chart2_sensitivity_over_time.png')


# ─── Chart 3: Responsiveness Over Time ─────────────────────────────────────────

def chart3_responsiveness_over_time(df):
    fig, ax = plt.subplots(figsize=(12, 5))

    for _, row in df.iterrows():
        ax.scatter(row['year'], row['responsiveness'], marker='o', s=60,
                   color=IPF_COLOR, alpha=0.7, zorder=3)

    yearly_avg = df.groupby('year')['responsiveness'].mean()
    ax.plot(yearly_avg.index, yearly_avg.values, color=RESPONSIVENESS_COLOR,
            linewidth=2.5, marker='D', markersize=8, label='Annual average', zorder=4)

    years_arr = df['year'].values.astype(float)
    scores_arr = df['responsiveness'].values
    if len(years_arr) > 2:
        z = np.polyfit(years_arr, scores_arr, 1)
        p = np.poly1d(z)
        x_trend = np.linspace(years_arr.min(), years_arr.max(), 100)
        ax.plot(x_trend, p(x_trend), '--', color=WB_GREY, linewidth=1.5,
                alpha=0.7, label=f'Trend (slope: {z[0]:+.2f}/yr)')

    ax.axhspan(7, 10, alpha=0.08, color=WB_GREEN, label='High responsiveness zone (>=7)')
    ax.axhspan(4, 7,  alpha=0.05, color=WB_ORANGE)
    ax.axhspan(1, 4,  alpha=0.05, color=WB_RED)

    ipf_patch = mpatches.Patch(color=IPF_COLOR, alpha=0.7, label='IPF project')
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles + [ipf_patch], labels + ['IPF project'],
              frameon=False, loc='lower right', fontsize=9)

    ax.set_xlabel('Approval Year')
    ax.set_ylabel('FCV Responsiveness Score (1-10)')
    ax.set_title('Chart 3: FCV Responsiveness Scores by Approval Year\nDjibouti Portfolio (2015-2024)', pad=15)
    ax.set_ylim(0, 10.5)
    ax.grid(axis='y', alpha=0.3)
    ax.set_xticks(sorted(df['year'].unique()))

    fig.tight_layout()
    return save_chart(fig, 'chart3_responsiveness_over_time.png')


# ─── Chart 4: Quadrant Scatter ─────────────────────────────────────────────────

def chart4_sensitivity_vs_responsiveness(df):
    fig, ax = plt.subplots(figsize=(13, 11))

    ax.fill_betweenx([6, 10.5], 0.5, 6,    alpha=0.08, color=WB_ORANGE)
    ax.fill_betweenx([6, 10.5], 6,   10.5, alpha=0.08, color=WB_GREEN)
    ax.fill_betweenx([0.5, 6],  0.5, 6,    alpha=0.05, color=WB_RED)
    ax.fill_betweenx([0.5, 6],  6,   10.5, alpha=0.06, color=WB_CYAN)

    ax.axhline(5.5, color=WB_GREY, linewidth=1, linestyle='--', alpha=0.6)
    ax.axvline(6.0, color=WB_GREY, linewidth=1, linestyle='--', alpha=0.6)

    ax.text(3.25, 8.5, 'IMPLEMENTATION GAP\n(Strong analysis,\nweak operational adaptation)',
            ha='center', va='center', fontsize=8, color=WB_ORANGE, style='italic', alpha=0.8)
    ax.text(8.25, 8.5, 'HIGH FCV INTEGRATION\n(Strong analysis\n+ operational adaptation)',
            ha='center', va='center', fontsize=8, color=WB_GREEN, style='italic', alpha=0.8)
    ax.text(3.25, 3.0, 'LOW FCV INTEGRATION\n(Weak analysis\n+ weak adaptation)',
            ha='center', va='center', fontsize=8, color=WB_RED, style='italic', alpha=0.8)
    ax.text(8.25, 3.0, 'RESPONSIVE BUT\nUNDERANALYSED\n(Weak analysis,\nstrong adaptation)',
            ha='center', va='center', fontsize=8, color=WB_CYAN, style='italic', alpha=0.8)

    for _, row in df.iterrows():
        ax.scatter(row['sensitivity'], row['responsiveness'], s=80,
                   color=IPF_COLOR, marker='o', zorder=5, alpha=0.85,
                   edgecolors='white', linewidth=0.8)
        ax.annotate(row['project_id'], (row['sensitivity'], row['responsiveness']),
                    xytext=(3, 3), textcoords='offset points',
                    fontsize=6.5, color=WB_GREY, alpha=0.9)

    avg_s = df['sensitivity'].mean()
    avg_r = df['responsiveness'].mean()
    ax.scatter(avg_s, avg_r, s=200, color='black', marker='*', zorder=6,
               label=f'Portfolio average ({avg_s:.1f}, {avg_r:.1f})')
    ax.annotate(f'Portfolio avg\n({avg_s:.1f}, {avg_r:.1f})',
                (avg_s, avg_r), xytext=(8, 6), textcoords='offset points',
                fontsize=9, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='black', lw=1.2))

    ipf_patch = mpatches.Patch(color=IPF_COLOR, alpha=0.85, label='IPF')
    star_patch = mpatches.Patch(color='black', label='Portfolio average')
    ax.legend(handles=[ipf_patch, star_patch], frameon=False, fontsize=9)

    ax.set_xlabel('FCV Sensitivity Score (1-10)', labelpad=10)
    ax.set_ylabel('FCV Responsiveness Score (1-10)', labelpad=10)
    ax.set_title('Chart 4: FCV Sensitivity vs Responsiveness — Portfolio Quadrant Analysis\nDjibouti World Bank Portfolio (2015-2024)', pad=15)
    ax.set_xlim(0.5, 10.5)
    ax.set_ylim(0.5, 10.5)
    ax.grid(alpha=0.2)

    fig.tight_layout()
    return save_chart(fig, 'chart4_sensitivity_vs_responsiveness.png')


# ─── Chart 5: Dimension Heatmap ────────────────────────────────────────────────

def chart5_dimension_heatmap(df):
    dim_cols = [f'd{i}_score' for i in range(1, 9)]
    mat = df[['project_id'] + dim_cols].set_index('project_id')
    mat.columns = [f'D{i}' for i in range(1, 9)]
    mat = mat.sort_values('D1', ascending=False)

    pid_map = dict(zip(df['project_id'], df['project_name'].str[:40]))
    mat.index = [f"{pid} | {pid_map.get(pid,'')[:35]}" for pid in mat.index]

    fig_h = max(8, len(mat) * 0.38)
    fig, ax = plt.subplots(figsize=(11, fig_h))

    sns.heatmap(mat.astype(float), ax=ax, cmap='RdYlGn',
                vmin=1, vmax=10, linewidths=0.5, linecolor='white',
                annot=True, fmt='.0f', annot_kws={'size': 7},
                cbar_kws={'label': 'Score (1-10)', 'shrink': 0.6})

    dim_labels = ['D1\nFCV Context', 'D2\nDo No Harm', 'D3\nStakeholder',
                  'D4\nToC', 'D5\nDesign', 'D6\nImplement.', 'D7\nResults', 'D8\nOne WBG']
    ax.set_xticklabels(dim_labels, rotation=0, ha='center', fontsize=9)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=7.5)
    ax.set_title('Chart 5: FCV Dimension Scores — All Projects Heatmap\n'
                 '(Score 1-10: Red=Low, Yellow=Moderate, Green=High)',
                 pad=15, fontsize=12)

    ax.axvline(3, color='black', linewidth=2, linestyle='-')
    ax.text(1.5, -0.6, 'SENSITIVITY', ha='center', va='top', fontsize=9,
            fontweight='bold', color=SENSITIVITY_COLOR, transform=ax.get_xaxis_transform())
    ax.text(5.5, -0.6, 'RESPONSIVENESS', ha='center', va='top', fontsize=9,
            fontweight='bold', color=RESPONSIVENESS_COLOR, transform=ax.get_xaxis_transform())

    fig.tight_layout()
    return save_chart(fig, 'chart5_dimension_heatmap.png')


# ─── Chart 6: Red Flags ────────────────────────────────────────────────────────

def chart6_red_flags(df):
    rf_labels = {
        'rf_rf1': 'RF1: Unmitigated conflict risk',
        'rf_rf2': 'RF2: Missing distributional analysis',
        'rf_rf3': 'RF3: OP 7.30 weakly handled',
        'rf_rf4': 'RF4: Elite capture / stakeholder opposition unmitigated',
        'rf_rf5': 'RF5: Macro/programmatic framework unrealistic for FCV',
    }

    fig, ax = plt.subplots(figsize=(11, 5))

    rf_cols = [c for c in df.columns if c.startswith('rf_rf')]
    counts = {}
    for col in rf_cols:
        if col in df.columns:
            counts[rf_labels.get(col, col)] = int(df[col].sum())

    if not counts:
        ax.text(0.5, 0.5, 'No red flag data available', ha='center', va='center',
                transform=ax.transAxes)
        return save_chart(fig, 'chart6_red_flags.png')

    labels = list(counts.keys())
    values = list(counts.values())
    pcts   = [v / len(df) * 100 for v in values]
    colors = [WB_RED if v > len(df) * 0.3 else WB_ORANGE if v > len(df) * 0.15 else WB_GREY
              for v in values]

    bars = ax.barh(labels, values, color=colors, alpha=0.85, height=0.6)
    for bar, v, pct in zip(bars, values, pcts):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                f'{v} ({pct:.0f}%)', va='center', fontsize=10)

    ax.set_xlabel('Number of Projects')
    ax.set_title(f'Chart 6: Red Flag Frequency Across Djibouti Portfolio\n(n={len(df)} screened projects)', pad=15)
    ax.set_xlim(0, max(values) + 4 if values else 5)
    ax.grid(axis='x', alpha=0.3)

    any_rf = df[[c for c in df.columns if c.startswith('rf_')]].any(axis=1).sum()
    ax.text(0.98, 0.02, f'{any_rf} of {len(df)} projects have >=1 red flag ({any_rf/len(df)*100:.0f}%)',
            transform=ax.transAxes, ha='right', va='bottom', fontsize=9, style='italic', color=WB_GREY)

    fig.tight_layout()
    return save_chart(fig, 'chart6_red_flags.png')


# ─── Chart 7: Radar Chart ──────────────────────────────────────────────────────

def chart7_dimension_radar(df):
    """Radar: portfolio average per dimension (no instrument split since all IPF)."""
    dim_cols = [f'd{i}_score' for i in range(1, 9)]
    avg_scores = [df[col].mean() if col in df.columns else 0 for col in dim_cols]

    n = len(avg_scores)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    avg_scores_plot = avg_scores + [avg_scores[0]]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))

    for level in [2, 4, 6, 8, 10]:
        ax.plot(angles, [level] * len(angles), color=WB_GREY, linewidth=0.5, alpha=0.3)

    # Early portfolio (2015-2019)
    early_df = df[df['year'] <= 2019]
    late_df  = df[df['year'] >= 2020]

    if len(early_df) > 0:
        early_avg = [early_df[f'd{i}_score'].mean() for i in range(1, 9)]
        early_plot = early_avg + [early_avg[0]]
        ax.fill(angles, early_plot, color=WB_CYAN, alpha=0.15)
        ax.plot(angles, early_plot, color=WB_CYAN, linewidth=2,
                label=f'Early cohort 2015-2019 (n={len(early_df)})')

    if len(late_df) > 0:
        late_avg = [late_df[f'd{i}_score'].mean() for i in range(1, 9)]
        late_plot = late_avg + [late_avg[0]]
        ax.fill(angles, late_plot, color=WB_ORANGE, alpha=0.15)
        ax.plot(angles, late_plot, color=WB_ORANGE, linewidth=2,
                label=f'Later cohort 2020-2024 (n={len(late_df)})')

    ax.fill(angles, avg_scores_plot, color=WB_BLUE, alpha=0.12)
    ax.plot(angles, avg_scores_plot, color=WB_BLUE, linewidth=3, label='Portfolio avg')

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([f'D{i}: {name}' for i, name in enumerate(DIM_NAMES_SHORT, 1)], fontsize=9)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=8)
    ax.set_rlabel_position(22.5)

    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), frameon=False, fontsize=10)
    ax.set_title('Chart 7: Average FCV Dimension Scores — Radar View\nEarly (2015-2019) vs Later (2020-2024) Cohorts vs Portfolio Average',
                 pad=20, fontsize=12)

    fig.tight_layout()
    return save_chart(fig, 'chart7_dimension_radar.png')


# ─── Chart 8: Score Distribution Box Plot ──────────────────────────────────────

def chart8_score_distribution(df):
    """Box plot: distribution by approval cohort (early vs late) since all are IPF."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    early = df[df['year'] <= 2019]
    late  = df[df['year'] >= 2020]
    groups  = ['All', '2015-2019', '2020-2024']
    palette = [WB_BLUE, WB_CYAN, WB_ORANGE]

    for ax, score_col, title in [
        (axes[0], 'sensitivity',    'FCV Sensitivity'),
        (axes[1], 'responsiveness', 'FCV Responsiveness')
    ]:
        data_groups = [
            df[score_col].values,
            early[score_col].values if len(early) else np.array([]),
            late[score_col].values  if len(late)  else np.array([]),
        ]
        data_groups_nonempty = [d for d in data_groups if len(d) > 0]
        labels_nonempty      = [g for g, d in zip(groups, data_groups) if len(d) > 0]
        palette_nonempty     = [c for c, d in zip(palette, data_groups) if len(d) > 0]

        bp = ax.boxplot(data_groups_nonempty, tick_labels=labels_nonempty,
                        patch_artist=True,
                        medianprops=dict(color='white', linewidth=2),
                        whiskerprops=dict(color=WB_GREY),
                        capprops=dict(color=WB_GREY),
                        flierprops=dict(marker='o', markerfacecolor=WB_GREY, markersize=5))

        for patch, color in zip(bp['boxes'], palette_nonempty):
            patch.set_facecolor(color)
            patch.set_alpha(0.75)

        for i, data in enumerate(data_groups_nonempty):
            if len(data) > 0:
                ax.scatter(i + 1, np.mean(data), marker='D', s=50,
                           color='black', zorder=5, label='Mean' if i == 0 else '')
                ax.text(i + 1 + 0.12, np.mean(data), f'{np.mean(data):.1f}',
                        va='center', fontsize=9)

        ax.axhline(7, color=WB_GREEN,  linewidth=1.2, linestyle='--', alpha=0.7, label='High threshold (7)')
        ax.axhline(4, color=WB_ORANGE, linewidth=1.2, linestyle='--', alpha=0.7, label='Moderate threshold (4)')

        for i, (grp, data) in enumerate(zip(labels_nonempty, data_groups_nonempty)):
            ax.text(i + 1, 0.3, f'n={len(data)}', ha='center', fontsize=8, color=WB_GREY)

        ax.set_ylabel(f'{title} Score (1-10)')
        ax.set_title(f'{title}\nby Approval Cohort', pad=10)
        ax.set_ylim(0, 11)
        ax.grid(axis='y', alpha=0.3)
        ax.legend(frameon=False, fontsize=8)

    fig.suptitle('Chart 8: Distribution of FCV Scores by Approval Cohort\nDjibouti Portfolio (2015-2024)',
                 fontsize=13, y=1.01)
    fig.tight_layout()
    return save_chart(fig, 'chart8_score_distribution.png')


# ─── Main ───────────────────────────────────────────────────────────────────────

def main():
    print('Djibouti FCV Portfolio Analysis — Chart Generation')
    print('=' * 52)

    print('\nLoading data...')
    df = load_data()
    print(f'  Projects loaded: {len(df)}')
    print(f'  Instrument types: {df["instrument"].unique().tolist()}')
    print(f'  Year range: {df["year"].min()} - {df["year"].max()}')
    print(f'  Avg sensitivity:    {df["sensitivity"].mean():.2f}')
    print(f'  Avg responsiveness: {df["responsiveness"].mean():.2f}')

    setup_style()
    print('\nGenerating charts...')
    chart1_portfolio_timeline(df)
    chart2_sensitivity_over_time(df)
    chart3_responsiveness_over_time(df)
    chart4_sensitivity_vs_responsiveness(df)
    chart5_dimension_heatmap(df)
    chart6_red_flags(df)
    chart7_dimension_radar(df)
    chart8_score_distribution(df)

    print('\nAll 8 charts generated successfully.')
    print(f'Output directory: {SCRIPT_DIR}')


if __name__ == '__main__':
    main()
