import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from datetime import datetime
from utils.groq_ai import get_ai_analysis, get_ai_status

st.set_page_config(
    page_title="Operational Excellence | ESG Logistics",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.sidebar import render_sidebar
render_sidebar(active_page="opex")

from utils.Operational_excellence import (
    detect_opex_columns,
    compute_kpis,
    dpmo_to_sigma,
    root_cause_analysis,
    fishbone_categories,
    five_whys,
    build_dmaic,
    build_recommendations,
    business_impact,
    CARBON_PRICE_DEFAULT,
)

# ─────────────────────────────────────────────
# GLOBAL CSS — Gemini HTML design tokens
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  --bg-dark:            #0b1120;
  --card-bg:            #111c38;
  --border-color:       #1e293b;
  --accent-blue:        #38bdf8;
  --accent-purple:      #c084fc;
  --text-main:          #f8fafc;
  --text-muted:         #94a3b8;
  --badge-green-bg:     rgba(16,185,129,0.1);
  --badge-green-text:   #34d399;
  --badge-green-border: rgba(16,185,129,0.2);
  --badge-red-bg:       rgba(239,68,68,0.1);
  --badge-red-text:     #f87171;
  --badge-red-border:   rgba(239,68,68,0.2);
  --badge-orange-bg:    rgba(249,115,22,0.1);
  --badge-orange-text:  #fb923c;
  --badge-orange-border:rgba(249,115,22,0.2);
  --badge-yellow-bg:    rgba(234,179,8,0.1);
  --badge-yellow-text:  #facc15;
  --badge-yellow-border:rgba(234,179,8,0.2);
}

* { font-family: 'Inter', system-ui, sans-serif; box-sizing: border-box; }
.stApp { background: var(--bg-dark) !important; }

/* ── Typography ── */
h1,h2,h3,h4,h5,h6 { color: var(--text-main) !important; }
p, li { color: var(--text-muted); }
[data-testid="stCaptionContainer"] { color: var(--text-muted) !important; font-size: 0.78rem !important; }

/* ── Streamlit chrome overrides ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stVerticalBlock"] > div { gap: 0 !important; }

/* ── Metrics (not used as st.metric — we use custom cards) ── */
[data-testid="stMetric"] {
  background: var(--card-bg) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
  padding: 16px !important;
}

/* ── Tabs — pill style matching Gemini HTML ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: rgba(17,28,56,0.3) !important;
  border-radius: 24px !important;
  border: 1px solid var(--border-color) !important;
  padding: 6px !important;
  gap: 4px !important;
  overflow-x: auto;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  background: var(--card-bg) !important;
  color: var(--text-muted) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 20px !important;
  font-weight: 500 !important;
  font-size: 0.85rem !important;
  padding: 7px 18px !important;
  white-space: nowrap !important;
  transition: all 0.2s !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
  background: #1e293b !important;
  color: var(--accent-blue) !important;
  border-color: rgba(56,189,248,0.3) !important;
  font-weight: 600 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { display: none !important; }
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
  background: transparent !important;
  padding: 20px 0 0 0 !important;
}

/* ── DataFrames ── */
[data-testid="stDataFrame"] {
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
  overflow: hidden;
}
[data-testid="stDataFrame"] th {
  background: #0f172a !important;
  color: var(--text-muted) !important;
  font-size: 0.75rem !important;
  text-transform: uppercase;
  font-weight: 500;
  padding: 12px 0 !important;
  border-bottom: 1px solid var(--border-color) !important;
}
[data-testid="stDataFrame"] td {
  color: var(--text-main) !important;
  font-size: 0.85rem !important;
  padding: 12px 0 !important;
  border-bottom: 1px solid rgba(30,41,59,0.5) !important;
}

/* ── Selects / Inputs ── */
.stSelectbox > div > div {
  background: var(--card-bg) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 8px !important;
  color: var(--text-main) !important;
}

/* ── Buttons ── */
.stButton > button {
  background: transparent !important;
  border: 1px solid var(--border-color) !important;
  color: var(--text-main) !important;
  border-radius: 8px !important;
  font-weight: 500 !important;
  font-size: 0.85rem !important;
  padding: 8px 14px !important;
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  transition: all 0.2s !important;
}
.stButton > button:hover {
  background: rgba(56,189,248,0.08) !important;
  border-color: rgba(56,189,248,0.3) !important;
  color: var(--accent-blue) !important;
}

[data-testid="stDownloadButton"] > button {
  background: transparent !important;
  border: 1px solid var(--border-color) !important;
  color: var(--text-main) !important;
  border-radius: 8px !important;
  font-weight: 500 !important;
  font-size: 0.85rem !important;
  padding: 8px 14px !important;
  width: 100% !important;
  transition: all 0.2s !important;
}
[data-testid="stDownloadButton"] > button:hover {
  background: rgba(56,189,248,0.08) !important;
  border-color: rgba(56,189,248,0.3) !important;
  color: var(--accent-blue) !important;
}

/* ── Containers with border ── */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--card-bg) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 16px !important;
}

hr { border-color: var(--border-color) !important; }

/* ── Tier / real-data badges ── */
.badge-real  { display:inline-block; background:var(--badge-green-bg); color:var(--badge-green-text);   border:1px solid var(--badge-green-border);  padding:2px 8px; border-radius:4px; font-size:0.65rem; font-weight:600; margin-top:8px; }
.badge-part  { display:inline-block; background:var(--badge-yellow-bg); color:var(--badge-yellow-text); border:1px solid var(--badge-yellow-border); padding:2px 8px; border-radius:4px; font-size:0.65rem; font-weight:600; margin-top:8px; }
.badge-est   { display:inline-block; background:var(--badge-orange-bg); color:var(--badge-orange-text); border:1px solid var(--badge-orange-border); padding:2px 8px; border-radius:4px; font-size:0.65rem; font-weight:600; margin-top:8px; }
.badge-none  { display:inline-block; background:rgba(100,116,139,0.1); color:#94a3b8;                   border:1px solid rgba(100,116,139,0.2);      padding:2px 8px; border-radius:4px; font-size:0.65rem; font-weight:600; margin-top:8px; }

/* ── Priority badges ── */
.pri-high   { padding:4px 10px; border-radius:6px; font-size:0.75rem; font-weight:500; background:var(--badge-red-bg);    color:var(--badge-red-text);    border:1px solid var(--badge-red-border); }
.pri-medium { padding:4px 10px; border-radius:6px; font-size:0.75rem; font-weight:500; background:var(--badge-orange-bg); color:var(--badge-orange-text); border:1px solid var(--badge-orange-border); }
.pri-low    { padding:4px 10px; border-radius:6px; font-size:0.75rem; font-weight:500; background:var(--badge-green-bg);  color:var(--badge-green-text);  border:1px solid var(--badge-green-border); }

/* ── Info / alert banners ── */
[data-testid="stAlert"] {
  background: var(--card-bg) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
  color: var(--text-muted) !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
TIER_LABEL = {0: "No Signal", 1: "Real Data", 2: "Partial Signal", 3: "Estimated"}
TIER_CSS   = {0: "badge-none", 1: "badge-real", 2: "badge-part", 3: "badge-est"}

def tier_badge_html(tier):
    css   = TIER_CSS.get(tier, "badge-none")
    label = TIER_LABEL.get(tier, "—")
    return f'<span class="{css}">{label.upper()}</span>'

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8", family="Inter, system-ui"),
    margin=dict(t=20, b=20, l=10, r=10),
)

# ─────────────────────────────────────────────
# NO-DATA STATE
# ─────────────────────────────────────────────
if "uploaded_df" not in st.session_state:
    # ── sticky header
    st.markdown("""
    <div style="padding:20px 0 0 0;border-bottom:1px solid #1e293b;display:flex;
    justify-content:space-between;align-items:center;margin-bottom:30px;">
        <div>
            <h1 style="font-size:1.5rem;display:flex;align-items:center;gap:10px;margin:0;">
                🎯 Operational Excellence</h1>
            <div style="font-size:0.85rem;color:#94a3b8;margin-top:4px;">
                Lean Six Sigma • Root Cause Analysis • DMAIC • Executive Decision Support</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.25);
    border-radius:12px;padding:20px 24px;margin-top:10px;">
        <div style="color:#f87171;font-size:0.9rem;font-weight:600;margin-bottom:6px;">
        ⚠️ No Dataset Loaded</div>
        <div style="color:#94a3b8;font-size:0.84rem;">
        Please upload a logistics dataset from the Upload page to run the Operational Excellence engine.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    if st.button("📤 Go to Upload Page"):
        st.switch_page("upload.py")
    st.stop()


# ─────────────────────────────────────────────
# RUN THE ENGINE
# ─────────────────────────────────────────────
raw_df = st.session_state["uploaded_df"].copy()
cols   = detect_opex_columns(raw_df)
kpis   = compute_kpis(raw_df, cols, carbon_price=CARBON_PRICE_DEFAULT)
df     = kpis["df"]

rca      = root_cause_analysis(df, cols)
fishbone = fishbone_categories(rca["pareto_df"])
whys     = five_whys(rca["top_cause"])
dmaic    = build_dmaic(kpis, rca)
recs     = build_recommendations(rca, kpis)
impact   = business_impact(kpis, recs)


dpmo        = round((kpis["n_delayed"] / kpis["n_shipments"]) * 1_000_000) if kpis["n_shipments"] else 0
sigma_level = dpmo_to_sigma(dpmo)


# ─────────────────────────────────────────────
# BUILD EXECUTIVE REPORT
# ─────────────────────────────────────────────
def build_executive_report():
    buf   = io.BytesIO()
    lines = []
    lines.append("ROUTEIQ — OPERATIONAL EXCELLENCE EXECUTIVE REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 60)
    lines.append("")
    lines.append("1. EXECUTIVE SUMMARY")
    lines.append(f"On-Time Delivery: {kpis['otd_pct']}%")
    lines.append(f"Delayed Shipments: {kpis['n_delayed']} of {kpis['n_shipments']}")
    lines.append(f"Process Sigma Level: {sigma_level} (DPMO {dpmo:,})")
    lines.append(f"Delay Detection Method: {kpis['delay_method']}")
    lines.append("")
    lines.append("2. KPI DASHBOARD")
    lines.append(f"OTD: {kpis['otd_pct']}%")
    lines.append(f"TAT: {kpis['tat_hours']} hrs" if kpis["tat_available"] else "TAT: unavailable")
    lines.append(f"Cost/Shipment: Rs {kpis['cost_per_shipment']:,.0f}" if kpis["cost_available"] else "Cost/Shipment: unavailable")
    lines.append(f"Fleet Utilization: {kpis['util_pct']}%" if kpis["util_available"] else "Fleet Utilization: unavailable")
    lines.append(f"Vehicle Idle Time: {kpis['idle_hours']} hrs" if kpis["idle_available"] else "Vehicle Idle Time: unavailable")
    lines.append(f"Warehouse Throughput: {kpis['throughput']} shipments/day" if kpis["throughput_available"] else "Warehouse Throughput: unavailable")
    lines.append(f"Delay Cost: Rs {kpis['delay_cost']:,.0f}" if kpis["delay_cost_available"] else "Delay Cost: unavailable")
    lines.append(f"Carbon Emissions: {kpis['total_emissions_kg']:,.0f} kg CO2" if kpis["carbon_available"] else "Carbon Emissions: unavailable")
    lines.append(f"ESG Score: {kpis['esg_score']}/100" if kpis["carbon_available"] else "ESG Score: unavailable")
    lines.append("")
    lines.append("3. ROOT CAUSE / PARETO ANALYSIS")
    lines.append(f"Method: {rca['method']}")
    if len(rca["pareto_df"]):
        for _, row in rca["pareto_df"].iterrows():
            lines.append(f"  - {row['Cause']}: {row['Count']} ({row['Pct']}%, cumulative {row['CumulativePct']}%)")
    else:
        lines.append("  No delayed shipments to analyze.")
    lines.append("")
    lines.append("4. FISHBONE (ISHIKAWA) CATEGORIES")
    for bucket, items in fishbone.items():
        lines.append(f"  {bucket}:")
        for it in items:
            lines.append(f"    - {it}")
    lines.append("")
    lines.append("5. FIVE WHYS")
    lines.append(f"Top cause: {rca['top_cause'] or 'N/A'}")
    for i, w in enumerate(whys["whys"], 1):
        lines.append(f"  Why {i}: {w}")
    lines.append(f"  Root cause: {whys['root_cause']}")
    lines.append("")
    lines.append("6. DMAIC SUMMARY")
    for phase in dmaic:
        lines.append(f"  [{phase['phase']}] ({phase['status']}) {phase['desc']}")
        lines.append(f"    -> {phase['result']}")
    lines.append("")
    lines.append("7. AI RECOMMENDATIONS")
    for r in recs:
        lines.append(f"  - ({r['cause']}) {r['text']}  [impact: {r['impact_pct']}% of total delay]")
    lines.append("")
    lines.append("8. BUSINESS IMPACT")
    lines.append(f"Projected Delay Reduction: {impact['delay_reduction_pct']}%")
    lines.append(f"Projected OTD Improvement: +{impact['otd_improvement_pct']} pts")
    lines.append(f"Potential Savings: Rs {impact['potential_savings']:,.0f}" if impact["potential_savings"] else "Potential Savings: unavailable")
    if impact["carbon_reduction_pct"] is not None:
        lines.append(f"Projected Carbon Reduction: {impact['carbon_reduction_pct']}%")
    lines.append("")
    lines.append("9. NEXT STEPS")
    lines.append("  - Instrument a delay-reason / timestamp field to move RCA to Tier 1 accuracy.")
    lines.append("  - Pilot the top recommendation on the highest-impact route/hub for one quarter.")
    lines.append("  - Track OTD, TAT, and delay-cause mix weekly; review against this baseline.")
    buf.write("\n".join(lines).encode())
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────────
# PAGE HEADER  (sticky top bar style)
# ─────────────────────────────────────────────
hdr_l, hdr_r = st.columns([3, 2])

with hdr_l:
    st.markdown("""
    <div style="padding:6px 0 16px 0;">
        <h1 style="font-size:1.5rem;display:flex;align-items:center;gap:10px;margin:0;">
            🎯 Operational Excellence</h1>
        <div style="font-size:0.85rem;color:#94a3b8;margin-top:4px;">
            Lean Six Sigma • Root Cause Analysis • DMAIC • Executive Decision Support</div>
    </div>
    """, unsafe_allow_html=True)

with hdr_r:
    _, btn_col = st.columns([1, 1])
    with btn_col:
        report_bytes = build_executive_report()
        st.download_button(
            label="⬇ Export Executive Report",
            data=report_bytes,
            file_name=f"routeiq_opex_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

st.markdown("<hr style='margin:0 0 24px 0;'>", unsafe_allow_html=True)

# Tier-3 methodology warning banner
if kpis["delay_tier"] == 3:
    st.markdown(f"""
    <div style="background:var(--badge-yellow-bg);border:1px solid var(--badge-yellow-border);
    border-radius:10px;padding:10px 16px;margin-bottom:20px;font-size:0.8rem;">
        <span style="color:var(--badge-yellow-text);font-weight:600;">⚠️ Methodology note: </span>
        <span style="color:#94a3b8;">{kpis['delay_method']}</span>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# KPI CARD HELPER
# ─────────────────────────────────────────────
def kpi_card(col, icon, label, value, sub, icon_color, tier=None):
    badge = tier_badge_html(tier) if tier is not None else ""
    col.markdown(f"""
    <div style="background:var(--card-bg);border:1px solid var(--border-color);
    border-radius:12px;padding:16px;display:flex;flex-direction:column;min-height:130px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
            <span style="font-size:0.75rem;color:var(--text-muted);text-transform:uppercase;
            font-weight:600;letter-spacing:0.04em;">{label}</span>
            <div style="width:28px;height:28px;border-radius:6px;background:{icon_color}1a;
            display:flex;align-items:center;justify-content:center;font-size:0.85rem;">{icon}</div>
        </div>
        <div style="color:var(--text-main);font-size:1.3rem;font-weight:700;margin-bottom:4px;">{value}</div>
        <div style="color:var(--text-muted);font-size:0.75rem;">{sub}</div>
        {badge}
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTION 1 — EXECUTIVE KPI DASHBOARD
# ─────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:10px;color:var(--text-main);
border-left:3px solid var(--accent-blue);padding-left:10px;margin-bottom:15px;">
    <span style="font-size:1.1rem;font-weight:600;">Executive KPI Dashboard</span>
</div>
""", unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)
kpi_card(k1, "⏱️", "On-Time Delivery",
         f"{kpis['otd_pct']}%",
         f"{kpis['n_delayed']} delayed / {kpis['n_shipments']}",
         "#3b82f6", kpis["delay_tier"])
kpi_card(k2, "🔄", "Turnaround Time",
         f"{kpis['tat_hours']} hrs" if kpis["tat_available"] else "N/A",
         "Avg. planned vs actual",
         "#10b981", 1 if kpis["tat_available"] else 0)
kpi_card(k3, "💰", "Cost / Shipment",
         f"₹{kpis['cost_per_shipment']:,.0f}" if kpis["cost_available"] else "N/A",
         "Average freight cost",
         "#f59e0b", 1 if kpis["cost_available"] else 0)
kpi_card(k4, "🚛", "Fleet Utilization",
         f"{kpis['util_pct']}%" if kpis["util_available"] else "N/A",
         "Weight vs. capacity",
         "#6366f1", 1 if kpis["util_available"] else 0)
kpi_card(k5, "📊", "Sigma Level",
         f"{sigma_level} σ",
         f"DPMO {dpmo:,}",
         "#a855f7", kpis["delay_tier"])

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

k6, k7, k8, k9 = st.columns(4)
kpi_card(k6, "⏳", "Vehicle Idle Time",
         f"{kpis['idle_hours']} hrs" if kpis["idle_available"] else "N/A",
         "Avg. per shipment",
         "#ef4444", 1 if kpis["idle_available"] else 0)
kpi_card(k7, "🏭", "Warehouse Throughput",
         f"{kpis['throughput']:,}" if kpis["throughput_available"] else "N/A",
         "Shipments / day",
         "#3b82f6", 1 if kpis["throughput_available"] else 0)
kpi_card(k8, "📉", "Delay Cost",
         f"₹{kpis['delay_cost']:,.0f}" if kpis["delay_cost_available"] else "N/A",
         "Estimated cost of delays",
         "#f43f5e", 1 if kpis["cost_available"] else 2)
kpi_card(k9, "🌱", "Carbon / ESG",
         f"{kpis['esg_score']}/100" if kpis["carbon_available"] else "N/A",
         f"{kpis['total_emissions_kg']:,.0f} kg CO₂" if kpis["carbon_available"] else "Unavailable",
         "#10b981", 1 if kpis["carbon_available"] else 0)

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTION 2 — ROOT CAUSE DIAGNOSTICS (pill tabs)
# ─────────────────────────────────────────────
st.markdown("""
<div style="background:rgba(17,28,56,0.3);border:1px solid var(--border-color);
border-radius:16px;padding:20px 20px 0 20px;margin-bottom:0;">
    <div style="display:flex;align-items:center;gap:10px;color:var(--text-main);
    border-left:3px solid var(--accent-blue);padding-left:10px;margin-bottom:16px;">
        <span style="font-size:1.1rem;font-weight:600;">Root Cause Diagnostics</span>
    </div>
</div>
""", unsafe_allow_html=True)

# wrap diagnostics in a card-like container
with st.container():
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Pareto Analysis",
        "🔍 Fishbone Diagram",
        "❓ 5 Whys",
        "🔄 DMAIC",
        "💡 Recommendations & Impact",
    ])

    pareto_df = rca["pareto_df"]

    # ── TAB 1: PARETO ─────────────────────────────────────────
    with tab1:
        if len(pareto_df) == 0:
            st.info("No delayed shipments detected (or a delay signal isn't available in this dataset).")
        else:
            p1, p2 = st.columns([2, 1])

            with p1:
                with st.container(border=True):
                    st.markdown("""
                    <div style="margin-bottom:4px;">
                        <div style="color:var(--text-main);font-size:1rem;font-weight:600;">
                        Delay Cause Pareto Chart</div>
                        <div style="color:var(--text-muted);font-size:0.8rem;margin-bottom:16px;">
                        Analyzing frequency and cumulative distribution of shipping bottlenecks</div>
                    </div>
                    """, unsafe_allow_html=True)

                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=pareto_df["Cause"], y=pareto_df["Count"],
                        marker=dict(color="#3b82f6", opacity=0.85, line=dict(width=0)),
                        name="Delayed Shipments",
                        text=pareto_df["Count"], textposition="outside",
                        textfont=dict(color="#94a3b8", size=10),
                        yaxis="y1",
                    ))
                    fig.add_trace(go.Scatter(
                        x=pareto_df["Cause"], y=pareto_df["CumulativePct"],
                        mode="lines+markers", name="Cumulative %",
                        line=dict(color="#f97316", width=2),
                        marker=dict(color="#f97316", size=5),
                        yaxis="y2",
                    ))
                    fig.add_hline(y=80, line=dict(color="#ef4444", width=1, dash="dash"),
                                  yref="y2", annotation_text="80% threshold",
                                  annotation_font=dict(color="#ef4444", size=9))
                    fig.update_layout(
                        **PLOT_LAYOUT, height=280,
                        xaxis=dict(tickfont=dict(color="#94a3b8", size=9), showgrid=False),
                        yaxis=dict(title="Count", showgrid=True, gridcolor="#1e293b",
                                   tickfont=dict(color="#94a3b8")),
                        yaxis2=dict(title="Cumulative %", overlaying="y", side="right",
                                    range=[0, 105], showgrid=False,
                                    tickfont=dict(color="#94a3b8")),
                        legend=dict(orientation="h", y=1.15,
                                    font=dict(color="#94a3b8", size=10),
                                    bgcolor="rgba(0,0,0,0)"),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # methodology signal badge
                    tier = rca.get("tier", 0)
                    tier_css = TIER_CSS.get(tier, "badge-none")
                    st.markdown(f"""
                    <div style="display:inline-block;margin-top:4px;padding:6px 12px;
                    border-radius:6px;font-size:0.75rem;"
                    class="{tier_css}">
                    {TIER_LABEL.get(tier,'')} — {rca['method']}
                    </div>
                    """, unsafe_allow_html=True)

            with p2:
                with st.container(border=True):
                    st.markdown("""
                    <div style="color:var(--text-main);font-size:1rem;font-weight:600;margin-bottom:4px;">
                    Critical Few (80/20)</div>
                    <div style="color:var(--text-muted);font-size:0.8rem;margin-bottom:14px;">
                    Top contributors to delay variance</div>
                    """, unsafe_allow_html=True)

                    critical = pareto_df[pareto_df["CumulativePct"] <= 80]
                    if critical.empty:
                        critical = pareto_df.head(1)

                    for _, row in critical.iterrows():
                        st.markdown(f"""
                        <div style="background:rgba(15,23,42,0.6);border:1px solid var(--border-color);
                        padding:12px;border-radius:10px;margin-bottom:10px;
                        display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <div style="color:var(--text-main);font-size:0.9rem;
                                font-weight:600;margin-bottom:2px;">{row['Cause']}</div>
                                <div style="color:var(--text-muted);font-size:0.75rem;">
                                {row['Pct']}% of delayed shipments</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.caption(f"These {len(critical)} cause(s) drive the bulk of delays — fix here first.")

            # ── FIXED ROOT CAUSE BREAKDOWN TABLE ────────────────
            # (single-line HTML strings — no leading indentation, so
            # Streamlit's Markdown parser can't mistake it for a code block)
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("""<div style="color:var(--text-main);font-size:1rem;font-weight:600;margin-bottom:14px;">
                Root Cause Breakdown</div>""", unsafe_allow_html=True)

                cause_colors = ["#38bdf8", "#a855f7", "#f97316", "#f43f5e", "#34d399", "#facc15", "#818cf8"]
                max_count = pareto_df["Count"].max()

                rows_html = ""
                for i, row in pareto_df.reset_index(drop=True).iterrows():
                    color = cause_colors[i % len(cause_colors)]
                    bar_pct = (row["Count"] / max_count) * 100 if max_count else 0
                    is_critical = row["CumulativePct"] <= 80
                    badge = (
                        '<span style="background:rgba(56,189,248,0.12);color:#38bdf8;border:1px solid rgba(56,189,248,0.3);padding:2px 8px;border-radius:4px;font-size:0.65rem;font-weight:600;white-space:nowrap;">CRITICAL FEW</span>'
                        if is_critical else
                        '<span style="color:#475569;font-size:0.7rem;">—</span>'
                    )
                    row_html = (
                        '<tr>'
                        '<td style="padding:14px 10px;border-bottom:1px solid rgba(30,41,59,0.5);">'
                        '<div style="display:flex;align-items:center;gap:10px;">'
                        f'<span style="width:8px;height:8px;border-radius:50%;background:{color};flex-shrink:0;"></span>'
                        f'<span style="color:var(--text-main);font-size:0.85rem;font-weight:500;">{row["Cause"]}</span>'
                        '</div></td>'
                        f'<td style="padding:14px 10px;border-bottom:1px solid rgba(30,41,59,0.5);color:var(--text-main);font-size:0.85rem;text-align:right;">{row["Count"]}</td>'
                        '<td style="padding:14px 10px;border-bottom:1px solid rgba(30,41,59,0.5);min-width:160px;">'
                        '<div style="display:flex;align-items:center;gap:10px;">'
                        '<div style="flex:1;height:6px;background:#1e293b;border-radius:3px;overflow:hidden;">'
                        f'<div style="width:{bar_pct}%;height:100%;background:{color};border-radius:3px;"></div>'
                        '</div>'
                        f'<span style="color:var(--text-muted);font-size:0.8rem;width:38px;text-align:right;">{row["Pct"]}%</span>'
                        '</div></td>'
                        f'<td style="padding:14px 10px;border-bottom:1px solid rgba(30,41,59,0.5);color:var(--text-muted);font-size:0.82rem;text-align:right;">{row["CumulativePct"]}%</td>'
                        f'<td style="padding:14px 10px;border-bottom:1px solid rgba(30,41,59,0.5);text-align:center;">{badge}</td>'
                        '</tr>'
                    )
                    rows_html += row_html

                table_html = (
                    '<div style="overflow-x:auto;">'
                    '<table style="width:100%;border-collapse:collapse;text-align:left;">'
                    '<thead><tr>'
                    '<th style="color:var(--text-muted);font-weight:500;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.04em;padding-bottom:10px;border-bottom:1px solid var(--border-color);">Cause</th>'
                    '<th style="color:var(--text-muted);font-weight:500;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.04em;padding-bottom:10px;border-bottom:1px solid var(--border-color);text-align:right;">Count</th>'
                    '<th style="color:var(--text-muted);font-weight:500;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.04em;padding-bottom:10px;border-bottom:1px solid var(--border-color);">Share of Delays</th>'
                    '<th style="color:var(--text-muted);font-weight:500;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.04em;padding-bottom:10px;border-bottom:1px solid var(--border-color);text-align:right;">Cumulative</th>'
                    '<th style="color:var(--text-muted);font-weight:500;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.04em;padding-bottom:10px;border-bottom:1px solid var(--border-color);text-align:center;">Flag</th>'
                    f'</tr></thead><tbody>{rows_html}</tbody></table></div>'
                )

                st.markdown(table_html, unsafe_allow_html=True)

    # ── TAB 2: FISHBONE ───────────────────────────────────────
    with tab2:
        bucket_icons = {
            "People": "🧑‍💼", "Process": "⚙️", "Machine": "🔧",
            "Material": "📦", "Environment": "🌦️", "Management": "🗂️",
        }
        bucket_colors = {
            "People":      ("#c084fc", "rgba(192,132,252,0.15)"),
            "Process":     ("#fb923c", "rgba(251,146,60,0.15)"),
            "Machine":     ("#34d399", "rgba(52,211,153,0.15)"),
            "Material":    ("#fb7185", "rgba(244,63,94,0.15)"),
            "Environment": ("#38bdf8", "rgba(56,189,248,0.15)"),
            "Management":  ("#e879f9", "rgba(232,121,249,0.15)"),
        }

        # Fishbone "spine" visual
        st.markdown("""
        <div style="position:relative;background:var(--card-bg);border:1px solid var(--border-color);
        border-radius:16px;padding:30px;min-height:340px;margin-bottom:20px;overflow:hidden;">
            <!-- Spine -->
            <div style="position:absolute;top:50%;left:5%;right:18%;height:4px;
            background:linear-gradient(90deg,#38bdf8,#a855f7);transform:translateY(-50%);border-radius:2px;"></div>
            <!-- Head box -->
            <div style="position:absolute;right:24px;top:50%;transform:translateY(-50%);
            background:#1e293b;border:2px solid #38bdf8;padding:14px 18px;border-radius:12px;
            text-align:center;z-index:2;">
                <div style="font-size:0.7rem;color:#94a3b8;margin-bottom:4px;">Analyzing causes of:</div>
                <div style="font-weight:700;color:#38bdf8;font-size:0.9rem;">Delayed Shipments</div>
            </div>
            <!-- Top row label -->
            <div style="position:absolute;top:18px;left:60px;right:160px;display:flex;
            justify-content:space-around;gap:10px;">
        """ + "".join([
            f'<div style="background:{bucket_colors.get(b,("#94a3b8","rgba(148,163,184,0.1)"))[1]};'
            f'color:{bucket_colors.get(b,("#94a3b8","rgba(148,163,184,0.1)"))[0]};padding:5px 12px;'
            f'border-radius:6px;font-size:0.78rem;font-weight:600;text-align:center;">'
            f'{bucket_icons.get(b,"•")} {b}</div>'
            for b in list(fishbone.keys())[:3]
        ]) + """
            </div>
            <!-- Bottom row label -->
            <div style="position:absolute;bottom:18px;left:60px;right:160px;display:flex;
            justify-content:space-around;gap:10px;">
        """ + "".join([
            f'<div style="background:{bucket_colors.get(b,("#94a3b8","rgba(148,163,184,0.1)"))[1]};'
            f'color:{bucket_colors.get(b,("#94a3b8","rgba(148,163,184,0.1)"))[0]};padding:5px 12px;'
            f'border-radius:6px;font-size:0.78rem;font-weight:600;text-align:center;">'
            f'{bucket_icons.get(b,"•")} {b}</div>'
            for b in list(fishbone.keys())[3:]
        ]) + """
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Detail cards — 3 columns
        fb_cols = st.columns(3)
        for i, (bucket, items) in enumerate(fishbone.items()):
            color, bg = bucket_colors.get(bucket, ("#94a3b8", "rgba(148,163,184,0.1)"))
            items_html = "".join(
                f"<div style='color:#94a3b8;font-size:0.73rem;padding:3px 0;'>• {it}</div>"
                for it in items
            )
            with fb_cols[i % 3]:
                st.markdown(f"""
                <div style="background:var(--card-bg);border:1px solid var(--border-color);
                border-radius:12px;padding:14px 16px;margin-bottom:12px;min-height:140px;">
                    <div style="color:{color};font-weight:700;font-size:0.86rem;margin-bottom:8px;">
                    {bucket_icons.get(bucket,'•')} {bucket}</div>
                    {items_html}
                </div>
                """, unsafe_allow_html=True)

    # ── TAB 3: 5 WHYS ─────────────────────────────────────────
    with tab3:
        if not whys["whys"]:
            st.info(whys["root_cause"])
        else:
            wl, wr = st.columns([2, 1])
            with wl:
                st.markdown("""<div style="color:var(--text-main);font-size:1rem;
                font-weight:600;margin-bottom:14px;">5 Whys Analysis</div>""", unsafe_allow_html=True)

                st.markdown(f"""
                <div style="background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.25);
                border-radius:10px;padding:10px 16px;margin-bottom:14px;font-size:0.82rem;">
                    <span style="color:#818cf8;font-weight:600;">Investigating top cause: </span>
                    <span style="color:var(--text-main);font-weight:700;"> {rca['top_cause']}</span>
                </div>
                """, unsafe_allow_html=True)

                for i, why in enumerate(whys["whys"], 1):
                    st.markdown(f"""
                    <div style="background:var(--card-bg);border:1px solid var(--border-color);
                    border-radius:10px;padding:12px 16px;display:flex;align-items:flex-start;
                    gap:14px;margin-bottom:10px;">
                        <div style="background:linear-gradient(135deg,#6366f1,#a855f7);color:white;
                        padding:4px 10px;border-radius:6px;font-size:0.75rem;font-weight:600;
                        white-space:nowrap;">Why {i}</div>
                        <div style="color:var(--text-main);font-size:0.85rem;line-height:1.6;">
                        {why}</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="background:var(--badge-red-bg);border:1px solid var(--badge-red-border);
                border-radius:12px;padding:15px 16px;margin-top:6px;">
                    <div style="color:var(--badge-red-text);font-weight:600;font-size:0.9rem;
                    margin-bottom:5px;">Root Cause</div>
                    <div style="color:var(--text-muted);font-size:0.82rem;">{whys['root_cause']}</div>
                </div>
                """, unsafe_allow_html=True)

            with wr:
                # Impact metric
                top_pct = pareto_df.iloc[0]["Pct"] if len(pareto_df) else "—"
                st.markdown(f"""
                <div style="background:var(--card-bg);border:1px solid var(--border-color);
                border-radius:12px;padding:20px;margin-bottom:14px;">
                    <div style="color:var(--text-muted);font-size:0.8rem;">Impact</div>
                    <div style="color:#38bdf8;font-size:1.8rem;font-weight:700;margin:8px 0;">
                    {top_pct}%</div>
                    <div style="color:var(--text-muted);font-size:0.8rem;">of total delayed shipments</div>
                </div>
                """, unsafe_allow_html=True)

                # Top recommendation
                if recs:
                    top_rec = recs[0]
                    st.markdown(f"""
                    <div style="background:var(--card-bg);border:1px solid rgba(56,189,248,0.3);
                    border-radius:12px;padding:18px;">
                        <div style="color:#38bdf8;font-weight:600;font-size:0.8rem;margin-bottom:8px;">
                        Recommendation</div>
                        <div style="color:var(--text-main);font-size:0.82rem;line-height:1.5;">
                        {top_rec['text']}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # ── TAB 4: DMAIC ──────────────────────────────────────────
    with tab4:
        phase_colors  = {"Define": "#3b82f6", "Measure": "#6366f1", "Analyze": "#8b5cf6",
                         "Improve": "#10b981", "Control": "#06b6d4"}
        phase_letters = {"Define": "D", "Measure": "M", "Analyze": "A",
                         "Improve": "I", "Control": "C"}
        status_colors = {"Completed": "#34d399", "In Progress": "#fb923c"}

        dl, dr = st.columns([2, 1])
        with dl:
            st.markdown("""<div style="color:var(--text-main);font-size:1rem;font-weight:600;
            margin-bottom:14px;">DMAIC Overview — Delays Reduction Project</div>""", unsafe_allow_html=True)

            for phase in dmaic:
                color    = phase_colors.get(phase["phase"], "#64748b")
                st_color = status_colors.get(phase["status"], "#64748b")
                letter   = phase_letters.get(phase["phase"], phase["phase"][0])
                st.markdown(f"""
                <div style="background:var(--card-bg);border:1px solid var(--border-color);
                border-radius:12px;padding:15px;display:flex;align-items:center;
                justify-content:space-between;margin-bottom:12px;">
                    <div style="display:flex;align-items:center;gap:14px;">
                        <div style="width:36px;height:36px;border-radius:8px;background:{color};
                        display:flex;align-items:center;justify-content:center;font-weight:700;
                        color:white;font-size:1rem;">{letter}</div>
                        <div>
                            <div style="color:var(--text-main);font-size:0.9rem;font-weight:600;
                            margin-bottom:2px;">{phase['phase']}</div>
                            <div style="color:var(--text-muted);font-size:0.75rem;">{phase['desc']}</div>
                            <div style="color:var(--text-main);font-size:0.82rem;font-weight:500;
                            margin-top:4px;">{phase['result']}</div>
                        </div>
                    </div>
                    <div style="display:inline-block;background:{st_color}22;
                    border:1px solid {st_color}44;color:{st_color};font-size:0.68rem;
                    font-weight:700;border-radius:99px;padding:3px 10px;white-space:nowrap;">
                    {phase['status']}</div>
                </div>
                """, unsafe_allow_html=True)

        with dr:
            # Project summary panel
            st.markdown("""
            <div style="background:var(--card-bg);border:1px solid var(--border-color);
            border-radius:12px;padding:20px;">
                <div style="color:var(--text-main);font-size:1rem;font-weight:600;
                margin-bottom:14px;">Project Summary</div>
            """, unsafe_allow_html=True)

            summary_items = [
                ("Problem", "High delay in shipments impacting service levels and cost."),
                ("Goal",    "Reduce shipment delays by 30% in the next 90 days."),
                ("Scope",   "All road shipments across active warehouses."),
                ("Team",    "Ops, Planning, Fleet, IT, Quality"),
            ]
            items_html = "".join(f"""
            <div style="margin-bottom:14px;">
                <div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:3px;">{h}</div>
                <div style="font-size:0.85rem;color:var(--text-main);">{b}</div>
            </div>
            """ for h, b in summary_items)
            st.markdown(items_html + "</div>", unsafe_allow_html=True)

    # ── TAB 5: RECOMMENDATIONS + IMPACT ───────────────────────
    with tab5:
        # ── Recommendations table
        with st.container(border=True):
            st.markdown("""<div style="color:var(--text-main);font-size:1rem;font-weight:600;
            margin-bottom:14px;">Recommendations & Impact</div>""", unsafe_allow_html=True)

            if not recs:
                st.info("No delay data available to generate recommendations.")
            else:
                # Build priority label based on impact_pct
                def priority_badge(pct):
                    if pct >= 15:
                        return '<span class="pri-high">High</span>'
                    elif pct >= 7:
                        return '<span class="pri-medium">Medium</span>'
                    return '<span class="pri-low">Low</span>'

                # Render as styled HTML table (single-line rows to avoid Markdown code-fence issue)
                rows_html = ""
                for i, rec in enumerate(recs, 1):
                    rows_html += (
                        '<tr>'
                        f'<td style="padding:13px 8px;border-bottom:1px solid rgba(30,41,59,0.5);color:var(--text-muted);font-size:0.85rem;">{i}</td>'
                        f'<td style="padding:13px 8px;border-bottom:1px solid rgba(30,41,59,0.5);color:var(--text-main);font-size:0.85rem;">{rec["text"]}</td>'
                        f'<td style="padding:13px 8px;border-bottom:1px solid rgba(30,41,59,0.5);color:var(--text-muted);font-size:0.82rem;">{rec["cause"]}</td>'
                        f'<td style="padding:13px 8px;border-bottom:1px solid rgba(30,41,59,0.5);color:var(--badge-red-text);font-size:0.82rem;">−{rec["impact_pct"]}% delay</td>'
                        f'<td style="padding:13px 8px;border-bottom:1px solid rgba(30,41,59,0.5);">{priority_badge(rec["impact_pct"])}</td>'
                        '</tr>'
                    )

                table_html = (
                    '<div style="overflow-x:auto;">'
                    '<table style="width:100%;border-collapse:collapse;text-align:left;font-size:0.85rem;">'
                    '<thead><tr>'
                    '<th style="color:var(--text-muted);font-weight:500;padding-bottom:12px;border-bottom:1px solid var(--border-color);width:4%;">#</th>'
                    '<th style="color:var(--text-muted);font-weight:500;padding-bottom:12px;border-bottom:1px solid var(--border-color);width:42%;">Recommendation</th>'
                    '<th style="color:var(--text-muted);font-weight:500;padding-bottom:12px;border-bottom:1px solid var(--border-color);width:18%;">Category</th>'
                    '<th style="color:var(--text-muted);font-weight:500;padding-bottom:12px;border-bottom:1px solid var(--border-color);width:18%;">Impact Value</th>'
                    '<th style="color:var(--text-muted);font-weight:500;padding-bottom:12px;border-bottom:1px solid var(--border-color);width:18%;">Priority</th>'
                    f'</tr></thead><tbody>{rows_html}</tbody></table></div>'
                )

                st.markdown(table_html, unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # ── Business Impact summary grid (4 cards)
        bi1, bi2, bi3, bi4 = st.columns(4)
        impact_cards = [
            (bi1, "Total Expected Reduction",
             f"{impact['delay_reduction_pct']}%",
             "in overall delays",
             "#38bdf8"),
            (bi2, "Potential Savings",
             f"₹{impact['potential_savings']:,.0f}" if impact["potential_savings"] else "N/A",
             "estimated annually",
             "#34d399"),
            (bi3, "OTD Improvement",
             f"+{impact['otd_improvement_pct']} pts",
             "projected increase",
             "#c084fc"),
            (bi4, "Carbon Reduction",
             f"{impact['carbon_reduction_pct']}%" if impact["carbon_reduction_pct"] is not None else "N/A",
             "projected CO₂ reduction",
             "#fb923c"),
        ]
        for col, title, val, sub, color in impact_cards:
            col.markdown(f"""
            <div style="background:var(--card-bg);border:1px solid var(--border-color);
            border-radius:12px;padding:20px;">
                <div style="color:var(--text-muted);font-size:0.8rem;margin-bottom:8px;">{title}</div>
                <div style="color:{color};font-size:1.4rem;font-weight:700;">{val}</div>
                <div style="color:var(--text-muted);font-size:0.75rem;margin-top:4px;">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""<div style="margin-top:10px;">""", unsafe_allow_html=True)
        st.caption("Projections are modeled from the recommendation set above and are directional, not guaranteed.")

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#1e293b;font-size:0.7rem;">
ESG Logistics Control Tower · Operational Excellence Module
</div>
""", unsafe_allow_html=True)