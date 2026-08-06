import streamlit as st
import pandas as pd
from datetime import datetime
from utils.groq_ai import get_ai_analysis, get_ai_status

st.set_page_config(
    page_title="Upload | ESG Logistics",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.sidebar import render_sidebar
render_sidebar(active_page="upload")

from utils.data_validation import (
    validate_dataset,
    clean_dataset,
    detect_column,
    analyse_domain_coverage,
    get_supplement_suggestions,
    make_dataset_entry,
    merge_datasets,
    get_merged_df,
    DATASET_REGISTRY_KEY,
    DOMAIN_SCHEMA,
)


# =========================================================
# GLOBAL CSS
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }
.stApp { background-color: #0b132b !important; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1600px; }

/* TOP BAR */
.rq-topbar {
    display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;
    padding: 10px 4px 18px 4px; border-bottom: 1px solid rgba(148,163,184,0.15); margin-bottom: 20px;
}
.rq-topbar h2 { font-size: 20px; font-weight: 700; color: white; margin: 0; }
.rq-topbar-sub { font-size: 12px; color: #94a3b8; margin-top: 2px; }
.rq-pill-row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.rq-status-pill {
    display:flex; align-items:center; gap:8px; background:#111c38; border:1px solid #1e293b;
    padding:7px 12px; border-radius:10px; font-size:12px; font-weight:500;
}
.rq-pulse-dot {
    width:8px; height:8px; border-radius:50%; background:#10b981;
    animation: rq-pulse 1.8s infinite;
}
@keyframes rq-pulse { 0% {opacity:1;} 50% {opacity:0.4;} 100% {opacity:1;} }

/* UPLOAD HERO */
.rq-upload-hero { text-align:center; margin-bottom: 6px; }
.rq-upload-hero h3 { font-size:24px; font-weight:800; color:white; margin:0 0 6px 0; }
.rq-upload-hero p { font-size:13.5px; color:#94a3b8; max-width:640px; margin:0 auto; }

.rq-uploader-card {
    background:radial-gradient(circle at center, #111c38 0%, #080d1a 100%);
    border:2px dashed rgba(16,185,129,0.4); border-radius:24px;
    padding:44px 24px 20px 24px; text-align:center;
}
.rq-uploader-card:hover { border-color: rgba(16,185,129,0.85); }

[data-testid="stFileUploader"] {
    background:transparent !important; border:none !important; padding:10px 24px 24px 24px !important;
}
[data-testid="stFileUploaderDropzone"] { background:transparent !important; border:none !important; }
[data-testid="stFileUploader"] section { background:transparent !important; }
[data-testid="stFileUploader"] small { color:#64748b !important; }
[data-testid="stFileUploader"] button {
    background:#10b981 !important; color:#052e21 !important; border:none !important;
    border-radius:10px !important; font-weight:700 !important;
}

/* META CARDS */
.rq-meta-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
.rq-meta-card {
    background:#111c38; border:1px solid rgba(30,41,59,0.8); border-radius:14px; padding:14px;
    display:flex; align-items:center; gap:12px;
}
.rq-meta-icon { padding:9px; border-radius:10px; font-size:14px; }
.rq-meta-title { font-size:12.5px; font-weight:600; color:white; }
.rq-meta-sub { font-size:11px; color:#94a3b8; }

/* SUCCESS BANNER */
.rq-success-banner {
    background:#111c38; border:1px solid rgba(16,185,129,0.3); border-radius:18px; padding:20px;
    display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:16px;
    box-shadow: 0 20px 25px -20px rgba(0,0,0,0.5);
}
.rq-success-left { display:flex; align-items:center; gap:16px; }
.rq-success-icon {
    width:48px; height:48px; background:rgba(16,185,129,0.10); border:1px solid rgba(16,185,129,0.3);
    border-radius:14px; display:flex; align-items:center; justify-content:center; color:#34d399; font-size:18px;
    flex-shrink:0;
}
.rq-success-title { font-size:15px; font-weight:700; color:#34d399; margin:0; }
.rq-success-filename { font-size:13.5px; font-weight:600; color:#e2e8f0; margin-top:1px; }
.rq-success-filesize { font-size:11px; color:#64748b; margin-top:1px; }
.rq-stat-pill {
    background:#0b132b; border:1px solid #1e293b; padding:10px 16px; border-radius:14px;
    display:flex; align-items:center; gap:12px;
}
.rq-stat-pill-icon { padding:8px; border-radius:10px; font-size:13px; }
.rq-stat-pill-label { font-size:10px; text-transform:uppercase; font-weight:600; letter-spacing:0.05em; color:#64748b; }
.rq-stat-pill-value { font-size:13.5px; font-weight:700; color:white; }

/* DOMAIN HEALTH CARD */
.dh-card {
    background:#111c38; border:1px solid #1e293b; border-radius:16px;
    padding:16px; margin-bottom:10px; position:relative; overflow:hidden;
}
.dh-card-header { display:flex; align-items:center; gap:10px; margin-bottom:12px; }
.dh-card-icon { font-size:18px; }
.dh-card-title { font-size:13px; font-weight:700; color:#e2e8f0; }
.dh-score-pill {
    margin-left:auto; padding:3px 10px; border-radius:99px; font-size:11px; font-weight:700;
}
.dh-score-great  { background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3); }
.dh-score-good   { background:rgba(96,165,250,0.15); color:#60a5fa; border:1px solid rgba(96,165,250,0.3); }
.dh-score-warn   { background:rgba(251,191,36,0.15); color:#fbbf24; border:1px solid rgba(251,191,36,0.3); }
.dh-score-poor   { background:rgba(244,63,94,0.15);  color:#fb7185; border:1px solid rgba(244,63,94,0.3); }
.dh-field-row {
    display:flex; align-items:center; gap:8px; padding:6px 0;
    border-bottom:1px solid rgba(30,41,59,0.5); font-size:11.5px;
}
.dh-field-row:last-child { border-bottom:none; }
.dh-field-name { color:#94a3b8; flex:1; font-weight:500; }
.dh-field-col { color:#e2e8f0; font-size:11px; font-family:monospace; flex:1.2; }
.status-present { color:#34d399; font-weight:700; }
.status-partial  { color:#fbbf24; font-weight:700; }
.status-missing  { color:#fb7185; font-weight:700; }
.status-poor     { color:#f97316; font-weight:700; }
.rq-badge-req    {
    background:rgba(244,63,94,0.10); color:#fb7185; border:1px solid rgba(244,63,94,0.2);
    padding:1px 6px; border-radius:4px; font-size:9.5px; font-weight:700;
}

/* SUPPLEMENT SUGGESTION CARD */
.sup-card {
    background:#0d1829; border:1px solid rgba(251,191,36,0.25); border-radius:14px;
    padding:14px 16px; margin-bottom:10px;
}
.sup-card-title { font-size:12.5px; font-weight:700; color:#fbbf24; margin-bottom:4px; }
.sup-card-domains { font-size:11px; color:#94a3b8; margin-bottom:6px; }
.sup-card-fallback { font-size:11px; color:#64748b; font-style:italic; }
.sup-aliases { font-size:10.5px; color:#34d399; font-family:monospace; background:#111c38; padding:4px 8px; border-radius:6px; margin-top:6px; }

/* DATASET REGISTRY CARD */
.reg-card {
    background:#111c38; border:1px solid #1e293b; border-radius:14px; padding:14px 16px;
    margin-bottom:8px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px;
}
.reg-card-primary { border-color:rgba(16,185,129,0.4); }
.reg-card-name { font-size:13px; font-weight:600; color:#e2e8f0; }
.reg-card-meta { font-size:11px; color:#64748b; }
.reg-badge-primary { background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3); padding:2px 8px; border-radius:6px; font-size:10px; font-weight:700; }
.reg-badge-supplement { background:rgba(96,165,250,0.12); color:#60a5fa; border:1px solid rgba(96,165,250,0.25); padding:2px 8px; border-radius:6px; font-size:10px; font-weight:700; }

/* PREVIEW CARD */
.rq-preview-card { background:#111c38; border:1px solid #1e293b; border-radius:18px; overflow:hidden; box-shadow:0 20px 25px -20px rgba(0,0,0,0.5); }
.rq-preview-head { padding:16px 24px; border-bottom:1px solid #1e293b; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; }
.rq-preview-head h3 { font-size:15px; font-weight:700; color:white; margin:0; letter-spacing:0.01em; }
.rq-preview-badge { background:#1e293b; color:#cbd5e1; font-size:11px; padding:3px 10px; border-radius:999px; font-weight:500; }
.rq-table-scroll { overflow-x:auto; }
.rq-table { width:100%; text-align:left; font-size:11.5px; color:#cbd5e1; white-space:nowrap; border-collapse:collapse; }
.rq-table thead { background:#0b132b; color:#94a3b8; text-transform:uppercase; font-weight:600; border-bottom:1px solid #1e293b; }
.rq-table th { padding:11px 16px; }
.rq-table td { padding:11px 16px; }
.rq-table tbody tr { border-bottom:1px solid rgba(30,41,59,0.6); }
.rq-table tbody tr:hover { background:rgba(30,41,59,0.4); }
.rq-idx { text-align:center; color:#64748b; }
.rq-mono { font-family: monospace; font-weight:600; color:white; }
.rq-num { text-align:right; }
.rq-badge-ok { background:rgba(16,185,129,0.10); color:#34d399; border:1px solid rgba(16,185,129,0.2); padding:4px 10px; border-radius:6px; font-size:11px; font-weight:500; }
.rq-badge-bad { background:rgba(244,63,94,0.10); color:#fb7185; border:1px solid rgba(244,63,94,0.2); padding:4px 10px; border-radius:6px; font-size:11px; font-weight:500; }
.rq-badge-neutral { background:rgba(245,158,11,0.10); color:#fbbf24; border:1px solid rgba(245,158,11,0.2); padding:4px 10px; border-radius:6px; font-size:11px; font-weight:500; }
.rq-table-footer {
    padding:11px 24px; background:rgba(11,19,43,0.5); border-top:1px solid #1e293b;
    display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;
    font-size:11.5px; color:#94a3b8;
}

/* OVERALL SCORE RING */
.score-ring-wrap { display:flex; flex-direction:column; align-items:center; gap:6px; padding:10px 0; }
.score-ring-num { font-size:2rem; font-weight:800; font-family:'Inter',sans-serif; }
.score-ring-label { font-size:11px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.06em; }

/* BUTTON OVERRIDES */
div[data-testid="stHorizontalBlock"] div[data-testid="column"] .stButton>button {
    background:#1e293b !important; color:white !important; border:1px solid #334155 !important;
    border-radius:10px !important; font-weight:600 !important; font-size:12.5px !important;
    padding:0.5rem 0.9rem !important;
}
div[data-testid="stHorizontalBlock"] div[data-testid="column"] .stButton>button:hover {
    background:#293548 !important; border-color:#475569 !important;
}
.stButton>button {
    background:#10b981 !important; color:#052e21 !important; border-radius:12px !important;
    border:none !important; font-weight:700 !important; font-size:13px !important; padding:0.7rem 1.2rem !important;
}
.stButton>button:hover { background:#0ea371 !important; }
[data-testid="stExpander"] { background:#111c38 !important; border:1px solid #1e293b !important; border-radius:12px !important; }
#MainMenu, footer, header { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


# =========================================================
# HELPERS
# =========================================================
def _html(markup: str) -> str:
    return "\n".join(line.lstrip() for line in markup.strip("\n").splitlines())


def format_bytes(n):
    if n is None:
        return "—"
    if n >= 1024 * 1024:
        return f"{n / (1024*1024):.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


def status_badge_html(val):
    s = str(val).lower()
    if any(k in s for k in ["delay", "late", "fail", "overdue"]):
        cls = "rq-badge-bad"
    elif any(k in s for k in ["time", "delivered", "success", "complete"]):
        cls = "rq-badge-ok"
    else:
        cls = "rq-badge-neutral"
    return f'<span class="{cls}">{val}</span>'


def score_css_class(score: int) -> str:
    if score >= 80:
        return "dh-score-great"
    if score >= 60:
        return "dh-score-good"
    if score >= 35:
        return "dh-score-warn"
    return "dh-score-poor"


def score_color(score: int) -> str:
    if score >= 80:
        return "#34d399"
    if score >= 60:
        return "#60a5fa"
    if score >= 35:
        return "#fbbf24"
    return "#fb7185"


# ─── TABLE RENDERING ─────────────────────────────────────
PAGE_SIZE = 10


def render_table_rows(df_page, cols, status_col, start_index):
    rows_html = []
    for offset, (_, row) in enumerate(df_page.iterrows()):
        abs_idx = start_index + offset
        cells = [f'<td class="rq-idx">{abs_idx}</td>']
        for c in cols:
            val = row[c]
            if pd.isna(val):
                cells.append('<td class="rq-mono">—</td>')
                continue
            if c == status_col:
                cells.append(f"<td>{status_badge_html(val)}</td>")
            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                formatted = f"{val:,.2f}".rstrip("0").rstrip(".") if isinstance(val, float) else f"{val:,}"
                cells.append(f'<td class="rq-num">{formatted}</td>')
            elif c == cols[0]:
                cells.append(f'<td class="rq-mono">{val}</td>')
            else:
                cells.append(f"<td>{val}</td>")
        rows_html.append(f"<tr>{''.join(cells)}</tr>")
    return "".join(rows_html)


def render_table_html(df_page, cols, status_col, start_index):
    header_html = "".join(f"<th>{c}</th>" for c in cols)
    body_html = render_table_rows(df_page, cols, status_col, start_index)
    return _html(f"""
    <div class="rq-table-scroll">
    <table class="rq-table">
    <thead><tr><th style="text-align:center;width:32px;">#</th>{header_html}</tr></thead>
    <tbody>{body_html}</tbody>
    </table>
    </div>
    """)


# =========================================================
# DOMAIN HEALTH DASHBOARD
# =========================================================
def render_domain_health(coverage: dict):
    """Renders the 4-domain column health grid."""
    st.markdown(_html("""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
    <span style="color:#60a5fa;font-size:1rem;">🔬</span>
    <span style="color:#e2e8f0;font-size:0.95rem;font-weight:700;">Column Health Dashboard</span>
    <span style="color:#64748b;font-size:0.75rem;margin-left:4px;">— how well your dataset covers each analytics module</span>
    </div>
    """), unsafe_allow_html=True)

    # Overall score
    all_scores = [v["score"] for v in coverage.values()]
    overall = round(sum(all_scores) / len(all_scores)) if all_scores else 0
    oc = score_color(overall)

    cols_top = st.columns([1, 3])
    with cols_top[0]:
        st.markdown(_html(f"""
        <div style="background:#111c38;border:1px solid #1e293b;border-radius:16px;
        padding:20px;text-align:center;height:100%;">
        <div style="color:{oc};font-size:2.8rem;font-weight:800;line-height:1;">{overall}</div>
        <div style="color:#94a3b8;font-size:11px;text-transform:uppercase;
        letter-spacing:0.07em;margin-top:4px;">Overall Dataset Score</div>
        <div style="height:6px;background:#1e293b;border-radius:99px;margin:10px 0 4px 0;overflow:hidden;">
        <div style="width:{overall}%;height:100%;background:{oc};border-radius:99px;"></div>
        </div>
        <div style="color:#64748b;font-size:10px;">
        {'Excellent' if overall>=80 else 'Good' if overall>=60 else 'Needs supplemental data' if overall>=35 else 'Critical fields missing'}
        </div>
        </div>
        """), unsafe_allow_html=True)

    with cols_top[1]:
        # 4 domain mini-score pills in a row
        domain_cols = st.columns(4)
        for col_obj, (domain_key, domain_result) in zip(domain_cols, coverage.items()):
            s = domain_result["score"]
            sc = score_css_class(s)
            col_obj.markdown(_html(f"""
            <div class="dh-card" style="height:60px;display:flex;align-items:center;gap:10px;">
            <span style="font-size:20px;">{domain_result['icon']}</span>
            <div style="flex:1;">
            <div style="color:#e2e8f0;font-size:12px;font-weight:600;">{domain_result['label']}</div>
            </div>
            <span class="dh-score-pill {sc}">{s}%</span>
            </div>
            """), unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # Detailed per-domain field tables
    dcols = st.columns(2)
    for idx, (domain_key, domain_result) in enumerate(coverage.items()):
        col_obj = dcols[idx % 2]
        with col_obj:
            s = domain_result["score"]
            sc = score_css_class(s)
            fields_html = ""
            for field_name, field_result in domain_result["fields"].items():
                status = field_result["status"]
                col_name = field_result["col"] or "—"
                req_badge = '<span class="rq-badge-req">REQUIRED</span>' if field_result["required"] else ""

                if status == "present":
                    st_span = f'<span class="status-present">✓ Present</span>'
                    null_info = f"({field_result['quality']['null_pct']}% null)" if field_result["quality"] else ""
                elif status == "partial":
                    st_span = f'<span class="status-partial">⚠ Partial</span>'
                    null_info = f"({field_result['quality']['null_pct']}% null)" if field_result["quality"] else ""
                elif status == "poor":
                    st_span = f'<span class="status-poor">⚡ Poor</span>'
                    null_info = f"({field_result['quality']['null_pct']}% null)" if field_result["quality"] else ""
                else:
                    st_span = f'<span class="status-missing">✗ Missing</span>'
                    null_info = ""

                fields_html += _html(f"""
                <div class="dh-field-row">
                <span class="dh-field-name">{field_name.replace('_',' ').title()} {req_badge}</span>
                <span class="dh-field-col" title="{col_name}">{col_name[:22] + '…' if len(col_name)>22 else col_name}</span>
                <span>{st_span}</span>
                <span style="color:#64748b;font-size:10px;min-width:60px;text-align:right;">{null_info}</span>
                </div>
                """)

            col_obj.markdown(_html(f"""
            <div class="dh-card">
            <div class="dh-card-header">
            <span class="dh-card-icon">{domain_result['icon']}</span>
            <span class="dh-card-title">{domain_result['label']}</span>
            <span class="dh-score-pill {sc}">{s}%</span>
            </div>
            {fields_html}
            </div>
            """), unsafe_allow_html=True)


# =========================================================
# SUPPLEMENT SUGGESTIONS PANEL
# =========================================================
def render_supplement_suggestions(coverage: dict):
    suggestions = get_supplement_suggestions(coverage)
    if not suggestions:
        st.markdown(_html("""
        <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);
        border-radius:12px;padding:14px 18px;display:flex;align-items:center;gap:12px;">
        <span style="font-size:1.4rem;">✅</span>
        <div>
        <div style="color:#34d399;font-weight:700;font-size:13px;">All Key Fields Detected</div>
        <div style="color:#94a3b8;font-size:12px;">Your dataset covers all required columns across every analytics module.</div>
        </div>
        </div>
        """), unsafe_allow_html=True)
        return

    required_missing = [s for s in suggestions if s["required"]]
    optional_missing = [s for s in suggestions if not s["required"]]

    if required_missing:
        st.markdown(_html(f"""
        <div style="background:rgba(244,63,94,0.07);border:1px solid rgba(244,63,94,0.25);
        border-radius:12px;padding:12px 18px;margin-bottom:12px;display:flex;align-items:center;gap:10px;">
        <span style="font-size:1.2rem;">🚨</span>
        <div>
        <div style="color:#fb7185;font-weight:700;font-size:13px;">
        {len(required_missing)} Required Field(s) Missing</div>
        <div style="color:#94a3b8;font-size:11.5px;">
        These columns are essential. Upload a supplemental file or map them manually.</div>
        </div>
        </div>
        """), unsafe_allow_html=True)

    if optional_missing:
        st.markdown(_html(f"""
        <div style="background:rgba(251,191,36,0.07);border:1px solid rgba(251,191,36,0.2);
        border-radius:12px;padding:12px 18px;margin-bottom:12px;display:flex;align-items:center;gap:10px;">
        <span style="font-size:1.2rem;">💡</span>
        <div>
        <div style="color:#fbbf24;font-weight:700;font-size:13px;">
        {len(optional_missing)} Optional Field(s) Missing — Analytics Will Use Estimates</div>
        <div style="color:#94a3b8;font-size:11.5px;">
        Adding these columns unlocks more accurate KPIs and removes "ESTIMATED" labels.</div>
        </div>
        </div>
        """), unsafe_allow_html=True)

    with st.expander(f"📋 View {len(suggestions)} Field Supplement Suggestions", expanded=len(required_missing) > 0):
        for sg in suggestions:
            domains_str = " · ".join(sg["domains"])
            aliases_str = ", ".join(sg["aliases"][:5])
            req_label = "🔴 Required" if sg["required"] else "🟡 Optional"
            dtype_icon = {"numeric": "🔢", "categorical": "🏷️", "datetime": "📅"}.get(sg["dtype"], "📊")
            st.markdown(_html(f"""
            <div class="sup-card">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
            <span>{dtype_icon}</span>
            <span class="sup-card-title">{sg['field'].replace('_',' ').title()}</span>
            <span style="font-size:10px;color:#94a3b8;margin-left:auto;">{req_label}</span>
            </div>
            <div class="sup-card-domains">Affects: {domains_str}</div>
            <div class="sup-card-fallback">Current fallback: {sg['fallback']}</div>
            <div class="sup-aliases">Accepted column names: {aliases_str}</div>
            </div>
            """), unsafe_allow_html=True)


# =========================================================
# DATASET REGISTRY PANEL
# =========================================================
def render_dataset_registry():
    registry = st.session_state.get(DATASET_REGISTRY_KEY, [])
    if not registry:
        return

    st.markdown(_html("""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
    <span style="color:#c084fc;font-size:1rem;">🗂️</span>
    <span style="color:#e2e8f0;font-size:0.95rem;font-weight:700;">Dataset Registry</span>
    <span style="color:#64748b;font-size:0.75rem;margin-left:4px;">
    — all uploaded files active in this session</span>
    </div>
    """), unsafe_allow_html=True)

    for i, entry in enumerate(registry):
        is_primary = entry.get("primary", False)
        badge_html = '<span class="reg-badge-primary">PRIMARY</span>' if is_primary else '<span class="reg-badge-supplement">SUPPLEMENT</span>'
        card_cls = "reg-card reg-card-primary" if is_primary else "reg-card"

        score_vals = [v["score"] for v in entry["coverage"].values()]
        avg_score = round(sum(score_vals) / len(score_vals)) if score_vals else 0
        sc = score_color(avg_score)

        domain_pills = "".join(
            f'<span style="background:rgba(255,255,255,0.05);border:1px solid #1e293b;'
            f'padding:2px 7px;border-radius:5px;font-size:9.5px;color:{score_color(v["score"])};">'
            f'{v["icon"]} {v["label"].split()[0]} {v["score"]}%</span>'
            for v in entry["coverage"].values()
        )

        rc1, rc2 = st.columns([5, 1])
        with rc1:
            st.markdown(_html(f"""
            <div class="{card_cls}">
            <div style="display:flex;align-items:center;gap:10px;flex:1;">
            <div style="font-size:1.4rem;">{'📊' if is_primary else '📎'}</div>
            <div style="flex:1;">
            <div style="display:flex;align-items:center;gap:8px;">
            <span class="reg-card-name">{entry['label']}</span>
            {badge_html}
            </div>
            <div class="reg-card-meta">{entry['n_rows']:,} rows · {entry['n_cols']} cols · {format_bytes(entry['file_size'])} · {entry['uploaded_at']}</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;">{domain_pills}</div>
            </div>
            <div style="text-align:center;min-width:56px;">
            <div style="color:{sc};font-size:1.4rem;font-weight:800;">{avg_score}</div>
            <div style="color:#64748b;font-size:9px;text-transform:uppercase;">Score</div>
            </div>
            </div>
            </div>
            """), unsafe_allow_html=True)
        with rc2:
            if st.button("✕ Remove", key=f"remove_ds_{i}", use_container_width=True):
                registry.pop(i)
                # If primary removed, promote next one
                if registry and not any(e["primary"] for e in registry):
                    registry[0]["primary"] = True
                st.session_state[DATASET_REGISTRY_KEY] = registry
                # Update merged df in session
                _sync_merged_to_session(registry)
                st.rerun()

    if len(registry) > 1:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        merged = merge_datasets(registry)
        merged_coverage = {}
        from utils.data_validation import analyse_domain_coverage
        merged_coverage = analyse_domain_coverage(merged)
        merged_scores = [v["score"] for v in merged_coverage.values()]
        merged_overall = round(sum(merged_scores) / len(merged_scores)) if merged_scores else 0
        mc = score_color(merged_overall)

        st.markdown(_html(f"""
        <div style="background:rgba(192,132,252,0.08);border:1px solid rgba(192,132,252,0.25);
        border-radius:12px;padding:12px 18px;display:flex;align-items:center;gap:12px;">
        <span style="font-size:1.2rem;">🔗</span>
        <div style="flex:1;">
        <div style="color:#c084fc;font-weight:700;font-size:13px;">
        Merged Dataset: {merged.shape[0]:,} rows × {merged.shape[1]} columns</div>
        <div style="color:#94a3b8;font-size:11.5px;">
        All analytics modules use this merged view. Combined coverage score:
        <span style="color:{mc};font-weight:700;">{merged_overall}%</span>
        </div>
        </div>
        </div>
        """), unsafe_allow_html=True)


def _sync_merged_to_session(registry):
    """Keep session_state's uploaded_df in sync with registry merge."""
    if not registry:
        for k in ("uploaded_df", "uploaded_filename", "uploaded_filesize", "uploaded_at"):
            st.session_state.pop(k, None)
        return
    merged = merge_datasets(registry)
    primary = next((e for e in registry if e["primary"]), registry[0])
    st.session_state["uploaded_df"] = merged
    st.session_state["uploaded_filename"] = primary["filename"]
    st.session_state["uploaded_filesize"] = primary["file_size"]
    st.session_state["uploaded_at"] = primary["uploaded_at"]


# =========================================================
# DATASET PREVIEW
# =========================================================
def render_dataset_preview(df, filename, file_size_bytes, uploaded_at):
    n_rows, n_cols = len(df), len(df.columns)
    status_col = detect_column(
        ["status", "delivery_status", "ontime", "on_time"], df.columns
    )
    cols = list(df.columns)

    st.session_state.setdefault("_show_all_rows", False)
    st.session_state.setdefault("_preview_page", 1)

    is_expanded = st.session_state["_show_all_rows"]
    total_pages = max(1, -(-n_rows // PAGE_SIZE))
    current_page = min(max(st.session_state["_preview_page"], 1), total_pages)
    st.session_state["_preview_page"] = current_page

    # SUCCESS BANNER
    st.markdown(_html(f"""
    <div class="rq-success-banner">
    <div class="rq-success-left">
    <div class="rq-success-icon">✅</div>
    <div>
    <p class="rq-success-title">Dataset Active</p>
    <div class="rq-success-filename">{filename}</div>
    <div class="rq-success-filesize">{format_bytes(file_size_bytes)}</div>
    </div>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:10px;">
    <div class="rq-stat-pill">
    <div class="rq-stat-pill-icon" style="background:rgba(16,185,129,0.10);color:#34d399;">📋</div>
    <div><div class="rq-stat-pill-label">Rows</div><div class="rq-stat-pill-value">{n_rows:,}</div></div>
    </div>
    <div class="rq-stat-pill">
    <div class="rq-stat-pill-icon" style="background:rgba(96,165,250,0.10);color:#60a5fa;">🗂️</div>
    <div><div class="rq-stat-pill-label">Columns</div><div class="rq-stat-pill-value">{n_cols}</div></div>
    </div>
    <div class="rq-stat-pill">
    <div class="rq-stat-pill-icon" style="background:rgba(251,191,36,0.10);color:#fbbf24;">📄</div>
    <div><div class="rq-stat-pill-label">File Size</div><div class="rq-stat-pill-value">{format_bytes(file_size_bytes)}</div></div>
    </div>
    <div class="rq-stat-pill">
    <div class="rq-stat-pill-icon" style="background:rgba(192,132,252,0.10);color:#c084fc;">🕒</div>
    <div><div class="rq-stat-pill-label">Uploaded</div><div class="rq-stat-pill-value">{uploaded_at}</div></div>
    </div>
    </div>
    </div>
    """), unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # PREVIEW CARD + CONTROLS
    badge_text = f"Full Dataset ({n_rows:,} Rows)" if is_expanded else "Preview — first 5 rows"
    st.markdown(_html(f"""
    <div class="rq-preview-card" style="border-bottom-left-radius:0;border-bottom-right-radius:0;box-shadow:none;">
    <div class="rq-preview-head">
    <div style="display:flex;align-items:center;gap:12px;">
    <h3>Dataset Explorer</h3>
    <span class="rq-preview-badge">{badge_text}</span>
    </div>
    </div>
    </div>
    """), unsafe_allow_html=True)

    hc1, hc2, hc3, _ = st.columns([1.7, 1.6, 1.5, 3.2])
    with hc1:
        toggle_label = "📖 Collapse" if is_expanded else f"👁 View All ({n_rows:,} Rows)"
        if st.button(toggle_label, use_container_width=True, key="_toggle_view_all"):
            st.session_state["_show_all_rows"] = not is_expanded
            st.session_state["_preview_page"] = 1
            st.rerun()
    with hc2:
        st.download_button(
            "⬇ Download Preview",
            data=df.head(5).to_csv(index=False).encode(),
            file_name="dataset_preview.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with hc3:
        if st.button("↺ Clear All Datasets", use_container_width=True, key="_clear_all"):
            for k in ("uploaded_df", "uploaded_filename", "uploaded_filesize",
                      "uploaded_at", "_show_all_rows", "_preview_page",
                      DATASET_REGISTRY_KEY):
                st.session_state.pop(k, None)
            st.rerun()

    if is_expanded:
        start = (current_page - 1) * PAGE_SIZE
        end = min(start + PAGE_SIZE, n_rows)
        df_page = df.iloc[start:end]
        table_html = render_table_html(df_page, cols, status_col, start_index=start + 1)
        footer_info = f"Showing {start + 1} to {end} of {n_rows:,} entries"
    else:
        df_page = df.head(5)
        table_html = render_table_html(df_page, cols, status_col, start_index=1)
        footer_info = f"Showing {min(5, n_rows)} of {n_rows:,} entries"

    st.markdown(_html(f"""
    <div class="rq-preview-card" style="border-radius:0;border-top:none;box-shadow:none;">
    {table_html}
    </div>
    """), unsafe_allow_html=True)

    if is_expanded and total_pages > 1:
        st.markdown(_html(f"""
        <div class="rq-preview-card" style="border-top:none;border-radius:0 0 18px 18px;">
        <div class="rq-table-footer"><span>{footer_info}</span></div>
        </div>
        """), unsafe_allow_html=True)
        fp1, fp2, fp3, _ = st.columns([1, 1.4, 1, 5.6])
        with fp1:
            if st.button("← Prev", disabled=(current_page == 1), use_container_width=True, key="_prev_page"):
                st.session_state["_preview_page"] = max(1, current_page - 1)
                st.rerun()
        with fp2:
            st.markdown(
                f"<div style='text-align:center;color:#94a3b8;font-size:12px;padding-top:8px;'>Page {current_page} of {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with fp3:
            if st.button("Next →", disabled=(current_page == total_pages), use_container_width=True, key="_next_page"):
                st.session_state["_preview_page"] = min(total_pages, current_page + 1)
                st.rerun()
    else:
        st.markdown(_html(f"""
        <div class="rq-preview-card" style="border-top:none;border-radius:0 0 18px 18px;">
        <div class="rq-table-footer"><span>{footer_info}</span></div>
        </div>
        """), unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)


# =========================================================
# FILE PROCESSOR
# =========================================================
def process_uploaded_file(uploaded_file, is_supplement: bool = False, supplement_label: str = ""):
    try:
        if uploaded_file.name.endswith(".csv"):
            try:
                df = pd.read_csv(uploaded_file)
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding="latin1")
        else:
            df = pd.read_excel(uploaded_file)

        report = validate_dataset(df)

        if report["errors"]:
            st.error("❌ This file can't be used:")
            for err in report["errors"]:
                st.markdown(f"- {err}")
            return None

        if report["warnings"]:
            with st.expander(f"⚠️ {len(report['warnings'])} data quality warning(s)", expanded=False):
                for w in report["warnings"]:
                    st.warning(w)

        auto_clean = st.checkbox(
            "🧹 Auto-clean (trim column names, drop fully empty rows/cols)",
            value=True,
            key=f"clean_{uploaded_file.name}_{is_supplement}",
        )
        if auto_clean:
            df = clean_dataset(df)

        return df

    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None


# =========================================================
# TOP BAR
# =========================================================
now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
registry = st.session_state.get(DATASET_REGISTRY_KEY, [])
has_active_dataset = len(registry) > 0

if has_active_dataset:
    primary_entry = next((e for e in registry if e["primary"]), registry[0])
    topbar_title = "Dataset Management &amp; Preview"
    topbar_sub = f"{primary_entry['filename']} active · {len(registry)} file(s) in registry"
else:
    topbar_title = "Upload Your Logistics Dataset"
    topbar_sub = "Upload your logistics data to unlock ESG insights, route optimization, and operational intelligence."

st.markdown(_html(f"""
<div class="rq-topbar">
<div>
<h2>{topbar_title}</h2>
<div class="rq-topbar-sub">{topbar_sub}</div>
</div>
<div class="rq-pill-row">
<div class="rq-status-pill"><span class="rq-pulse-dot"></span><span style="color:#94a3b8;">System:</span><span style="color:#34d399;font-weight:700;">All Systems Operational</span></div>
<div class="rq-status-pill">📅 <span style="color:#e2e8f0;">{now_str}</span></div>
{'<div class="rq-status-pill">🗂️ <span style="color:#c084fc;font-weight:700;">' + str(len(registry)) + ' file(s) loaded</span></div>' if has_active_dataset else ''}
</div>
</div>
"""), unsafe_allow_html=True)


# =========================================================
# MAIN FLOW
# =========================================================
tab_upload, tab_health, tab_supplement = st.tabs([
    "☁️  Upload",
    "🔬  Column Health",
    "➕  Add Supplemental Data",
])

# ── TAB 1: UPLOAD ─────────────────────────────────────────
with tab_upload:
    if not has_active_dataset:
        st.markdown(_html("""
        <div class="rq-upload-hero">
        <h3>Import Data for Processing</h3>
        <p>Upload your logistics data to unlock powerful ESG insights, route optimization, and operational intelligence.</p>
        </div>
        """), unsafe_allow_html=True)

        st.markdown(_html("""
        <div class="rq-uploader-card">
        <div style="font-size:2.5rem;margin-bottom:10px;">☁️</div>
        <div style="font-size:16px;font-weight:700;color:white;">Drop your PRIMARY dataset file here</div>
        <div style="font-size:12.5px;color:#94a3b8;margin-top:4px;">Supports CSV, XLSX — up to 200 MB</div>
        </div>
        """), unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Upload Primary Dataset",
            type=["csv", "xlsx"],
            label_visibility="collapsed",
            key="primary_uploader",
        )

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        st.markdown(_html("""
        <div class="rq-meta-grid">
        <div class="rq-meta-card"><div class="rq-meta-icon" style="background:rgba(16,185,129,0.10);color:#34d399;">📄</div><div><div class="rq-meta-title">CSV, XLSX</div><div class="rq-meta-sub">Supported Formats</div></div></div>
        <div class="rq-meta-card"><div class="rq-meta-icon" style="background:rgba(129,140,248,0.10);color:#818cf8;">🗄️</div><div><div class="rq-meta-title">200 MB</div><div class="rq-meta-sub">Max File Size</div></div></div>
        <div class="rq-meta-card"><div class="rq-meta-icon" style="background:rgba(96,165,250,0.10);color:#60a5fa;">🛡️</div><div><div class="rq-meta-title">Secure</div><div class="rq-meta-sub">In-session only</div></div></div>
        <div class="rq-meta-card"><div class="rq-meta-icon" style="background:rgba(251,191,36,0.10);color:#fbbf24;">⚡</div><div><div class="rq-meta-title">Multi-File</div><div class="rq-meta-sub">Supplement uploads</div></div></div>
        </div>
        """), unsafe_allow_html=True)

    else:
        # Show secondary uploader to add more files
        uploaded_file = st.file_uploader(
            "Upload an additional or replacement dataset",
            type=["csv", "xlsx"],
            help="Uploading a new file adds it to the registry. Mark it as Primary or Supplemental.",
            key="extra_uploader",
        )

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        render_dataset_registry()
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # Show preview using merged df
        merged_df = merge_datasets(registry)
        primary_entry = next((e for e in registry if e["primary"]), registry[0])
        render_dataset_preview(
            merged_df,
            primary_entry["filename"],
            primary_entry["file_size"],
            primary_entry["uploaded_at"],
        )

    # Process new upload
    if uploaded_file is not None:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown(_html("""
        <div style="color:#e2e8f0;font-size:13px;font-weight:600;margin-bottom:8px;">
        ⚙️ Configure Upload
        </div>
        """), unsafe_allow_html=True)

        cfg_c1, cfg_c2 = st.columns([2, 2])
        with cfg_c1:
            is_primary_toggle = st.toggle(
                "Set as PRIMARY dataset (replaces current primary)",
                value=not has_active_dataset,
                key="is_primary_toggle",
            )
        with cfg_c2:
            ds_label = st.text_input(
                "Dataset label (optional)",
                placeholder=f"e.g. 'Q2 2024 Shipments' or 'Weight Supplement'",
                key="ds_label_input",
            )

        if st.button("✅ Process & Add to Registry", use_container_width=False, key="process_btn"):
            df = process_uploaded_file(uploaded_file, is_supplement=not is_primary_toggle, supplement_label=ds_label)
            if df is not None:
                now_ts = datetime.now().strftime("%d %b %Y, %I:%M %p")
                entry = make_dataset_entry(
                    df=df,
                    filename=uploaded_file.name,
                    file_size=getattr(uploaded_file, "size", None),
                    uploaded_at=now_ts,
                    label=ds_label or uploaded_file.name,
                    primary=is_primary_toggle,
                )

                registry = st.session_state.get(DATASET_REGISTRY_KEY, [])

                if is_primary_toggle:
                    # Demote any existing primary
                    for e in registry:
                        e["primary"] = False

                registry.append(entry)
                st.session_state[DATASET_REGISTRY_KEY] = registry

                # Reset explorer state
                st.session_state["_show_all_rows"] = False
                st.session_state["_preview_page"] = 1

                # Sync merged df to session_state for all other pages
                _sync_merged_to_session(registry)

                st.success(f"✅ '{entry['label']}' added to registry as {'PRIMARY' if is_primary_toggle else 'SUPPLEMENT'}.")
                st.rerun()


# ── TAB 2: COLUMN HEALTH ──────────────────────────────────
with tab_health:
    registry = st.session_state.get(DATASET_REGISTRY_KEY, [])
    if not registry:
        st.markdown(_html("""
        <div style="background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.25);
        border-radius:12px;padding:20px 24px;margin-top:10px;">
        <div style="color:#fca5a5;font-size:0.9rem;font-weight:600;margin-bottom:6px;">⚠️ No Dataset Loaded</div>
        <div style="color:#7d9bc0;font-size:0.84rem;">Upload a dataset first to see the Column Health Dashboard.</div>
        </div>
        """), unsafe_allow_html=True)
    else:
        # Show health for merged dataset
        merged_df = merge_datasets(registry)
        coverage = analyse_domain_coverage(merged_df)
        render_domain_health(coverage)

        # Per-file health tabs if multiple files
        if len(registry) > 1:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown(_html("""
            <div style="color:#94a3b8;font-size:12px;font-weight:600;text-transform:uppercase;
            letter-spacing:0.06em;margin-bottom:10px;">Individual File Health</div>
            """), unsafe_allow_html=True)
            file_tabs = st.tabs([f"{'⭐ ' if e['primary'] else '📎 '}{e['label'][:20]}" for e in registry])
            for tab_obj, entry in zip(file_tabs, registry):
                with tab_obj:
                    render_domain_health(entry["coverage"])


# ── TAB 3: SUPPLEMENT ─────────────────────────────────────
with tab_supplement:
    registry = st.session_state.get(DATASET_REGISTRY_KEY, [])
    if not registry:
        st.markdown(_html("""
        <div style="background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.25);
        border-radius:12px;padding:20px 24px;margin-top:10px;">
        <div style="color:#fca5a5;font-size:0.9rem;font-weight:600;margin-bottom:6px;">⚠️ No Dataset Loaded</div>
        <div style="color:#7d9bc0;font-size:0.84rem;">Upload a primary dataset first, then come here to add supplemental files.</div>
        </div>
        """), unsafe_allow_html=True)
    else:
        merged_df = merge_datasets(registry)
        coverage = analyse_domain_coverage(merged_df)

        # What's missing
        st.markdown(_html("""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
        <span style="color:#fbbf24;font-size:1rem;">💡</span>
        <span style="color:#e2e8f0;font-size:0.95rem;font-weight:700;">Missing Field Suggestions</span>
        <span style="color:#64748b;font-size:0.75rem;margin-left:4px;">— upload supplemental files to fill these gaps</span>
        </div>
        """), unsafe_allow_html=True)

        render_supplement_suggestions(coverage)

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        # Supplement uploader
        st.markdown(_html("""
        <div style="background:#111c38;border:1px solid rgba(192,132,252,0.25);border-radius:16px;
        padding:20px 24px;margin-bottom:10px;">
        <div style="color:#c084fc;font-weight:700;font-size:14px;margin-bottom:6px;">
        ➕ Upload Supplemental Dataset</div>
        <div style="color:#94a3b8;font-size:12px;margin-bottom:14px;">
        The supplemental file's NEW columns will be merged into the active dataset by row order.
        Existing columns are never overwritten. Use the column name hints above to name your columns correctly.
        </div>
        </div>
        """), unsafe_allow_html=True)

        sup_file = st.file_uploader(
            "Supplemental file (CSV or XLSX)",
            type=["csv", "xlsx"],
            key="supplement_uploader",
        )
        sup_label = st.text_input(
            "Label for this supplemental file",
            placeholder="e.g. 'Weight Data', 'Delay Reasons', 'TAT Timestamps'",
            key="sup_label",
        )

        if sup_file is not None:
            if st.button("➕ Merge Into Registry", use_container_width=False, key="merge_sup_btn"):
                df = process_uploaded_file(sup_file, is_supplement=True)
                if df is not None:
                    now_ts = datetime.now().strftime("%d %b %Y, %I:%M %p")
                    entry = make_dataset_entry(
                        df=df,
                        filename=sup_file.name,
                        file_size=getattr(sup_file, "size", None),
                        uploaded_at=now_ts,
                        label=sup_label or sup_file.name,
                        primary=False,
                    )
                    registry.append(entry)
                    st.session_state[DATASET_REGISTRY_KEY] = registry
                    _sync_merged_to_session(registry)

                    # Show coverage delta
                    new_merged = merge_datasets(registry)
                    new_coverage = analyse_domain_coverage(new_merged)
                    new_scores = [v["score"] for v in new_coverage.values()]
                    new_overall = round(sum(new_scores) / len(new_scores)) if new_scores else 0

                    old_scores = [v["score"] for v in coverage.values()]
                    old_overall = round(sum(old_scores) / len(old_scores)) if old_scores else 0
                    delta = new_overall - old_overall

                    if delta > 0:
                        st.success(f"✅ Supplemental file merged! Overall coverage improved by +{delta} points → {new_overall}%")
                    else:
                        st.info(f"✅ Supplemental file merged. No new domain coverage added (columns may already exist).")
                    st.rerun()

        # Download template for missing fields
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        suggestions = get_supplement_suggestions(coverage)
        if suggestions:
            template_cols = []
            for sg in suggestions[:8]:
                template_cols.append(sg["aliases"][0])

            template_df = pd.DataFrame(
                {col: pd.Series(dtype="object") for col in ["shipment_id"] + template_cols}
            )
            # Add a few placeholder rows
            for i in range(3):
                template_df.loc[i] = ["" for _ in template_df.columns]

            st.markdown(_html("""
            <div style="color:#94a3b8;font-size:12px;font-weight:600;text-transform:uppercase;
            letter-spacing:0.06em;margin-bottom:8px;">📥 Download Supplement Template</div>
            """), unsafe_allow_html=True)
            st.markdown(_html("""
            <div style="color:#64748b;font-size:11.5px;margin-bottom:8px;">
            Pre-filled with the missing column names — add your data and upload as a supplemental file.
            </div>
            """), unsafe_allow_html=True)
            st.download_button(
                "⬇ Download Supplement Template (.csv)",
                data=template_df.to_csv(index=False).encode(),
                file_name="routeiq_supplement_template.csv",
                mime="text/csv",
                use_container_width=False,
            )