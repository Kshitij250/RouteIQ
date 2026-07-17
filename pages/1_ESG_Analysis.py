import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

st.set_page_config(
    page_title="ESG Analysis | ESG Logistics",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.sidebar import render_sidebar
render_sidebar()

# ─────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
  --bg-base:        #080e1c;
  --bg-surface:     #0d1528;
  --bg-card:        #111d35;
  --border:         #1e2f4d;
  --text-primary:   #e8f0fe;
  --text-secondary: #7d9bc0;
  --text-muted:     #4a6080;
  --green:          #22c55e;
  --blue:           #3b82f6;
  --purple:         #8b5cf6;
  --amber:          #f59e0b;
  --red:            #ef4444;
  --font-head:      'Space Grotesk', sans-serif;
  --font-body:      'DM Sans', sans-serif;
}

* { font-family: var(--font-body); box-sizing: border-box; }
.stApp { background: var(--bg-base) !important; }

[data-testid="stSidebar"] {
  background: var(--bg-surface) !important;
  border-right: 1px solid var(--border) !important;
}

h1,h2,h3 { font-family: var(--font-head) !important; color: var(--text-primary) !important; }

[data-testid="stMetric"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  padding: 16px 18px !important;
}
[data-testid="stMetricLabel"] {
  color: var(--text-muted) !important;
  font-size: 0.7rem !important;
  font-weight: 600 !important;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}
[data-testid="stMetricValue"] {
  color: var(--text-primary) !important;
  font-family: var(--font-head) !important;
  font-size: 1.6rem !important;
  font-weight: 700 !important;
}

[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: var(--bg-surface) !important;
  border-radius: 10px !important;
  border: 1px solid var(--border) !important;
  padding: 4px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--text-secondary) !important;
  border-radius: 8px !important;
  font-weight: 500 !important;
  font-size: 0.85rem !important;
  padding: 6px 16px !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
  background: var(--bg-card) !important;
  color: var(--text-primary) !important;
  font-weight: 700 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { display: none !important; }

[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  overflow: hidden;
}
[data-testid="stDataFrame"] th {
  background: var(--bg-surface) !important;
  color: var(--text-muted) !important;
  font-size: 0.7rem !important;
  text-transform: uppercase;
}
[data-testid="stDataFrame"] td {
  color: var(--text-primary) !important;
  font-size: 0.84rem !important;
}

.stSelectbox > div > div {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text-primary) !important;
}

.stButton > button {
  background: linear-gradient(135deg, #1a3a6b, #1e4080) !important;
  color: var(--text-primary) !important;
  border: 1px solid #243556 !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
}

[data-testid="stDownloadButton"] > button {
  background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
  color: white !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  width: 100% !important;
}

hr { border-color: var(--border) !important; }
p, li { color: var(--text-secondary); }
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# EMISSION ENGINE
# ─────────────────────────────────────────────
def get_emission_factor(vehicle):
    vehicle = str(vehicle).upper()
    if any(x in vehicle for x in ["HCV","AXLE","TRAILER","MULTI"]):
        return 0.22
    elif any(x in vehicle for x in ["LCV","ACE","PICKUP"]):
        return 0.10
    elif any(x in vehicle for x in ["TRUCK","LPT"]):
        return 0.15
    elif any(x in vehicle for x in ["MINI","VAN"]):
        return 0.08
    return 0.12

def detect_column(possible_names, columns):
    for col in columns:
        for name in possible_names:
            if name.lower() in col.lower():
                return col
    return None

CARBON_PRICE = 80


# ─────────────────────────────────────────────
# NO DATA STATE
# ─────────────────────────────────────────────
if "uploaded_df" not in st.session_state:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:14px;padding:6px 0 20px 0;">
        <div style="width:44px;height:44px;background:linear-gradient(135deg,#064e3b,#10B981);
        border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.4rem;">📊</div>
        <div>
            <div style="color:#e8f0fe;font-size:1.4rem;font-weight:700;
            font-family:'Space Grotesk',sans-serif;">ESG Analysis Dashboard</div>
            <div style="color:#4a6080;font-size:0.78rem;margin-top:2px;">
                Sustainability intelligence for logistics operations
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.25);
    border-radius:12px;padding:20px 24px;margin-top:10px;">
        <div style="color:#fca5a5;font-size:0.9rem;font-weight:600;margin-bottom:6px;">
        ⚠️ No Dataset Loaded</div>
        <div style="color:#7d9bc0;font-size:0.84rem;">
        Please upload a logistics dataset from the Upload page to begin ESG analysis.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    if st.button("📤 Go to Upload Page", use_container_width=False):
        st.switch_page("upload.py")

    st.stop()


# ─────────────────────────────────────────────
# LOAD & PREPARE DATA
# ─────────────────────────────────────────────
df = st.session_state["uploaded_df"].copy()

vehicle_col  = detect_column(["vehicle","vehicletype","truck","transport"], df.columns)
distance_col = detect_column(["distance","km","kilometer"], df.columns)
route_col    = detect_column(["route","lane","origin","source","from"], df.columns)
city_col     = detect_column(["city","destination","to","location"], df.columns)
mode_col     = detect_column(["mode","transport_mode","transportmode"], df.columns)
date_col     = detect_column(["date","datetime","shipment_date","created"], df.columns)
weight_col   = detect_column(["weight","cargo","load","tonnage"], df.columns)
cost_col     = detect_column(["cost","price","freight","charge"], df.columns)

if not vehicle_col or not distance_col:
    st.error("Vehicle or Distance column not detected. Please check your dataset columns.")
    st.stop()

df[vehicle_col]  = df[vehicle_col].astype(str).str.upper().str.strip()
df[distance_col] = pd.to_numeric(df[distance_col], errors="coerce").fillna(0)

df["emission_factor"] = df[vehicle_col].apply(get_emission_factor)
df["emission_kgCO2"]  = df[distance_col] * df["emission_factor"]
df["carbon_cost"]     = df["emission_kgCO2"] * CARBON_PRICE

max_emission   = df["emission_kgCO2"].max()
df["esg_score"] = (100 - (df["emission_kgCO2"] / max_emission) * 100) if max_emission > 0 else 100

# ESG score band
def score_band(s):
    if s >= 80: return "Excellent"
    elif s >= 60: return "Good"
    elif s >= 40: return "Average"
    else: return "Poor"

df["esg_band"] = df["esg_score"].apply(score_band)

# ─────────────────────────────────────────────
# COMPUTED KPIs
# ─────────────────────────────────────────────
total_emissions    = df["emission_kgCO2"].sum()
total_carbon_cost  = df["carbon_cost"].sum()
shipment_count     = len(df)
avg_esg_score      = df["esg_score"].mean()
avg_distance       = df[distance_col].mean()
total_distance     = df[distance_col].sum()
emission_per_km    = total_emissions / total_distance if total_distance > 0 else 0
poor_shipments     = (df["esg_band"] == "Poor").sum()
excellent_pct      = (df["esg_band"] == "Excellent").sum() / shipment_count * 100

vehicle_emissions  = (
    df.groupby(vehicle_col)["emission_kgCO2"]
    .sum().sort_values(ascending=False)
    .head(8).reset_index()
)
highest_vehicle  = vehicle_emissions.iloc[0][vehicle_col]
highest_emission = vehicle_emissions.iloc[0]["emission_kgCO2"]


# ─────────────────────────────────────────────
# TOP BAR
# ─────────────────────────────────────────────
top_l, top_r = st.columns([3, 2])

with top_l:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:14px;padding:6px 0 4px 0;">
        <div style="width:44px;height:44px;background:linear-gradient(135deg,#064e3b,#10B981);
        border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.4rem;">📊</div>
        <div>
            <div style="color:#e8f0fe;font-size:1.4rem;font-weight:700;
            font-family:'Space Grotesk',sans-serif;">ESG Analysis Dashboard</div>
            <div style="color:#4a6080;font-size:0.78rem;margin-top:2px;">
                Sustainability intelligence · Carbon tracking · Fleet ESG scoring
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_r:
    st.markdown("<div style='padding-top:8px;'></div>", unsafe_allow_html=True)
    _, dl_col = st.columns([1, 1])
    with dl_col:
        export_df = df[[vehicle_col, distance_col, "emission_kgCO2",
                        "carbon_cost", "esg_score", "esg_band"]].copy()
        export_df.columns = ["Vehicle", "Distance (km)", "CO2 (kg)",
                             "Carbon Cost (₹)", "ESG Score", "ESG Band"]
        csv_bytes = export_df.to_csv(index=False).encode()
        st.download_button(
            label="⬇ Export ESG Report",
            data=csv_bytes,
            file_name="esg_analysis_report.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.markdown("<hr style='margin:8px 0 16px 0;border-color:#1e2f4d;'>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTION 1 — EXECUTIVE KPI TILES
# ─────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
    <span style="color:#22c55e;font-size:1rem;">🌿</span>
    <span style="color:#e8f0fe;font-size:0.95rem;font-weight:600;
    font-family:'Space Grotesk',sans-serif;">Executive ESG Summary</span>
</div>
""", unsafe_allow_html=True)

def kpi_card(col, icon, label, value, note, accent, note_color=None):
    nc = note_color or accent
    col.markdown(f"""
    <div style="background:#111d35;border:1px solid #1e2f4d;border-radius:14px;
    padding:16px 18px;position:relative;overflow:hidden;">
        <div style="position:absolute;top:0;left:0;right:0;height:3px;
        background:{accent};border-radius:14px 14px 0 0;"></div>
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
            <div style="width:30px;height:30px;background:{accent}22;border-radius:8px;
            display:flex;align-items:center;justify-content:center;font-size:0.9rem;">{icon}</div>
            <div style="color:#4a6080;font-size:0.66rem;font-weight:600;
            text-transform:uppercase;letter-spacing:0.07em;">{label}</div>
        </div>
        <div style="color:#e8f0fe;font-size:1.55rem;font-weight:800;
        font-family:'Space Grotesk',sans-serif;line-height:1;">{value}</div>
        <div style="color:{nc};font-size:0.7rem;font-weight:600;margin-top:5px;">{note}</div>
    </div>
    """, unsafe_allow_html=True)

k1, k2, k3, k4, k5, k6 = st.columns(6)
kpi_card(k1, "🌍", "Total CO₂",        f"{total_emissions:,.0f} kg",    f"{emission_per_km:.3f} kg/km",          "#22c55e")
kpi_card(k2, "💸", "Carbon Cost",       f"₹{total_carbon_cost:,.0f}",   f"@ ₹{CARBON_PRICE}/kg CO₂",             "#ef4444")
kpi_card(k3, "📦", "Total Shipments",   f"{shipment_count:,}",           f"Avg {avg_distance:,.0f} km each",       "#3b82f6")
kpi_card(k4, "⭐", "Avg ESG Score",     f"{avg_esg_score:.1f}/100",      f"{excellent_pct:.0f}% excellent fleet",  "#f59e0b")
kpi_card(k5, "⚠️", "Poor ESG Ships",   f"{poor_shipments:,}",           "Need immediate attention",               "#ef4444", "#fca5a5")
kpi_card(k6, "🛣️", "Total Distance",   f"{total_distance:,.0f} km",     f"Fleet-wide coverage",                   "#8b5cf6")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTION 2 — ESG SCORE HEALTH BAND
# ─────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
    <span style="color:#3b82f6;">🎯</span>
    <span style="color:#e8f0fe;font-size:0.95rem;font-weight:600;
    font-family:'Space Grotesk',sans-serif;">Fleet ESG Health Breakdown</span>
</div>
""", unsafe_allow_html=True)

band_counts = df["esg_band"].value_counts()
band_config = {
    "Excellent": ("#22c55e", "80–100", "🟢"),
    "Good":      ("#3b82f6", "60–79",  "🔵"),
    "Average":   ("#f59e0b", "40–59",  "🟡"),
    "Poor":      ("#ef4444", "0–39",   "🔴"),
}

b1, b2, b3, b4 = st.columns(4)
for col, (band, (color, rng, dot)) in zip([b1,b2,b3,b4], band_config.items()):
    count = band_counts.get(band, 0)
    pct   = count / shipment_count * 100
    col.markdown(f"""
    <div style="background:#111d35;border:1px solid #1e2f4d;border-radius:14px;
    padding:16px 18px;text-align:center;">
        <div style="font-size:1.4rem;margin-bottom:6px;">{dot}</div>
        <div style="color:{color};font-size:1.5rem;font-weight:800;
        font-family:'Space Grotesk',sans-serif;">{count:,}</div>
        <div style="color:#e8f0fe;font-size:0.82rem;font-weight:600;margin-top:2px;">{band}</div>
        <div style="color:#4a6080;font-size:0.68rem;">Score {rng}</div>
        <div style="height:4px;background:rgba(255,255,255,0.05);border-radius:99px;
        margin-top:10px;overflow:hidden;">
            <div style="height:100%;width:{pct:.0f}%;background:{color};
            border-radius:99px;"></div>
        </div>
        <div style="color:{color};font-size:0.7rem;font-weight:700;
        margin-top:4px;">{pct:.1f}% of fleet</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTION 3 — MAIN ANALYSIS TABS
# ─────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
    <span style="color:#8b5cf6;">📈</span>
    <span style="color:#e8f0fe;font-size:0.95rem;font-weight:600;
    font-family:'Space Grotesk',sans-serif;">Deep ESG Analysis</span>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "🌿 Carbon Emissions",
    "🚛 Fleet Performance",
    "💰 Cost Intelligence",
    "📋 Shipment Audit"
])

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#7d9bc0", family="DM Sans"),
    margin=dict(t=20, b=20, l=10, r=10),
)

# ── TAB 1: CARBON EMISSIONS ───────────────────
with tab1:
    c1, c2 = st.columns([1.4, 1])

    with c1:
        with st.container(border=True):
            st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
            font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
            🏭 Top Carbon Emitting Vehicles</div>""", unsafe_allow_html=True)

            fig_bar = go.Figure(data=[go.Bar(
                x=vehicle_emissions[vehicle_col],
                y=vehicle_emissions["emission_kgCO2"],
                marker=dict(
                    color=vehicle_emissions["emission_kgCO2"],
                    colorscale=[[0,"#1e3a5f"],[0.5,"#22c55e"],[1,"#ef4444"]],
                    line=dict(width=0)
                ),
                text=[f"{v:,.0f}" for v in vehicle_emissions["emission_kgCO2"]],
                textposition="outside",
                textfont=dict(color="#7d9bc0", size=10),
                hovertemplate="%{x}<br>%{y:,.0f} kg CO₂<extra></extra>"
            )])
            fig_bar.update_layout(
                **PLOT_LAYOUT, height=320,
                xaxis=dict(tickfont=dict(color="#4a6080", size=9), showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#1e2f4d", tickfont=dict(color="#4a6080")),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        with st.container(border=True):
            st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
            font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
            🥧 Emission Share by Vehicle</div>""", unsafe_allow_html=True)

            fig_pie = go.Figure(data=[go.Pie(
                labels=vehicle_emissions[vehicle_col],
                values=vehicle_emissions["emission_kgCO2"],
                hole=0.6,
                marker=dict(colors=["#22c55e","#3b82f6","#f59e0b","#8b5cf6",
                                     "#ef4444","#06b6d4","#ec4899","#84cc16"]),
                textinfo="none",
                hovertemplate="%{label}<br>%{value:,.0f} kg CO₂ (%{percent})<extra></extra>"
            )])
            fig_pie.update_layout(
                **PLOT_LAYOUT, height=320,
                showlegend=True,
                legend=dict(font=dict(color="#7d9bc0", size=9),
                            bgcolor="rgba(0,0,0,0)", x=0.7, y=0.5),
                annotations=[dict(
                    text=f"{total_emissions/1000:.1f}t<br>CO₂",
                    x=0.38, y=0.5,
                    font=dict(size=13, color="#e8f0fe", family="Space Grotesk"),
                    showarrow=False
                )]
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
        font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
        📊 CO₂ Emission Distribution (All Shipments)</div>""", unsafe_allow_html=True)

        fig_hist = go.Figure(data=[go.Histogram(
            x=df["emission_kgCO2"],
            nbinsx=25,
            marker=dict(color="#22c55e", opacity=0.8, line=dict(width=0)),
            hovertemplate="Range: %{x:.0f} kg<br>Count: %{y}<extra></extra>"
        )])
        fig_hist.update_layout(
            **PLOT_LAYOUT, height=200,
            xaxis=dict(title="CO₂ (kg)", tickfont=dict(color="#4a6080"),
                       showgrid=False, title_font=dict(color="#4a6080")),
            yaxis=dict(title="Shipments", tickfont=dict(color="#4a6080"),
                       showgrid=True, gridcolor="#1e2f4d",
                       title_font=dict(color="#4a6080")),
            bargap=0.05,
        )
        st.plotly_chart(fig_hist, use_container_width=True)


# ── TAB 2: FLEET PERFORMANCE ──────────────────
with tab2:
    f1, f2 = st.columns(2)

    with f1:
        with st.container(border=True):
            st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
            font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
            📦 Shipment Volume by Vehicle Type</div>""", unsafe_allow_html=True)

            ship_dist = df[vehicle_col].value_counts().head(6).reset_index()
            ship_dist.columns = ["Vehicle", "Count"]

            fig_vol = go.Figure(data=[go.Bar(
                x=ship_dist["Vehicle"],
                y=ship_dist["Count"],
                marker=dict(color="#3b82f6", opacity=0.85, line=dict(width=0)),
                text=ship_dist["Count"],
                textposition="outside",
                textfont=dict(color="#7d9bc0", size=10),
            )])
            fig_vol.update_layout(
                **PLOT_LAYOUT, height=280,
                xaxis=dict(tickfont=dict(color="#4a6080", size=9), showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#1e2f4d", tickfont=dict(color="#4a6080")),
            )
            st.plotly_chart(fig_vol, use_container_width=True)

    with f2:
        with st.container(border=True):
            st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
            font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
            ⭐ ESG Score Distribution</div>""", unsafe_allow_html=True)

            fig_esg = go.Figure(data=[go.Histogram(
                x=df["esg_score"],
                nbinsx=20,
                marker=dict(
                    color=df["esg_score"].tolist(),
                    colorscale=[[0,"#ef4444"],[0.5,"#f59e0b"],[1,"#22c55e"]],
                    line=dict(width=0)
                ),
                hovertemplate="Score: %{x:.0f}<br>Count: %{y}<extra></extra>"
            )])
            fig_esg.update_layout(
                **PLOT_LAYOUT, height=280,
                xaxis=dict(title="ESG Score", tickfont=dict(color="#4a6080"),
                           showgrid=False, title_font=dict(color="#4a6080")),
                yaxis=dict(title="Shipments", tickfont=dict(color="#4a6080"),
                           showgrid=True, gridcolor="#1e2f4d",
                           title_font=dict(color="#4a6080")),
                bargap=0.05,
            )
            st.plotly_chart(fig_esg, use_container_width=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
        font-family:'Space Grotesk',sans-serif;margin-bottom:10px;">
        🚛 Vehicle-wise ESG Performance Summary</div>""", unsafe_allow_html=True)

        vehicle_summary = df.groupby(vehicle_col).agg(
            Shipments      = (distance_col, "count"),
            Avg_Distance   = (distance_col, "mean"),
            Total_CO2      = ("emission_kgCO2", "sum"),
            Avg_ESG_Score  = ("esg_score", "mean"),
            Carbon_Cost    = ("carbon_cost", "sum"),
        ).reset_index()

        vehicle_summary.columns = [
            "Vehicle", "Shipments", "Avg Distance (km)",
            "Total CO₂ (kg)", "Avg ESG Score", "Carbon Cost (₹)"
        ]

        vehicle_summary["Avg Distance (km)"] = vehicle_summary["Avg Distance (km)"].round(0)
        vehicle_summary["Total CO₂ (kg)"]    = vehicle_summary["Total CO₂ (kg)"].round(0)
        vehicle_summary["Avg ESG Score"]      = vehicle_summary["Avg ESG Score"].round(1)
        vehicle_summary["Carbon Cost (₹)"]   = vehicle_summary["Carbon Cost (₹)"].round(0)
        vehicle_summary = vehicle_summary.sort_values("Total CO₂ (kg)", ascending=False)

        st.dataframe(vehicle_summary, use_container_width=True, hide_index=True, height=260)


# ── TAB 3: COST INTELLIGENCE ──────────────────
with tab3:
    ci1, ci2 = st.columns([1.2, 1])

    with ci1:
        with st.container(border=True):
            st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
            font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
            💰 Carbon Cost by Vehicle Type</div>""", unsafe_allow_html=True)

            cost_by_vehicle = (
                df.groupby(vehicle_col)["carbon_cost"]
                .sum().sort_values(ascending=False)
                .head(8).reset_index()
            )

            fig_cost = go.Figure(data=[go.Bar(
                x=cost_by_vehicle[vehicle_col],
                y=cost_by_vehicle["carbon_cost"],
                marker=dict(color="#ef4444", opacity=0.8, line=dict(width=0)),
                text=[f"₹{v:,.0f}" for v in cost_by_vehicle["carbon_cost"]],
                textposition="outside",
                textfont=dict(color="#7d9bc0", size=9),
            )])
            fig_cost.update_layout(
                **PLOT_LAYOUT, height=300,
                xaxis=dict(tickfont=dict(color="#4a6080", size=9), showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#1e2f4d", tickfont=dict(color="#4a6080")),
            )
            st.plotly_chart(fig_cost, use_container_width=True)

    with ci2:
        with st.container(border=True):
            st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
            font-family:'Space Grotesk',sans-serif;margin-bottom:12px;">
            📊 Cost Breakdown</div>""", unsafe_allow_html=True)

            avg_cost_per_ship = total_carbon_cost / shipment_count
            avg_cost_per_km   = total_carbon_cost / total_distance if total_distance > 0 else 0
            top_cost_vehicle  = cost_by_vehicle.iloc[0][vehicle_col]
            top_cost_val      = cost_by_vehicle.iloc[0]["carbon_cost"]
            top_cost_pct      = top_cost_val / total_carbon_cost * 100

            for lbl, val, color in [
                ("Total Carbon Cost",          f"₹{total_carbon_cost:,.0f}",    "#ef4444"),
                ("Avg Cost per Shipment",       f"₹{avg_cost_per_ship:,.0f}",    "#f59e0b"),
                ("Avg Cost per KM",             f"₹{avg_cost_per_km:,.2f}",      "#3b82f6"),
                ("Highest Cost Vehicle",        top_cost_vehicle,                 "#8b5cf6"),
                ("Top Vehicle Cost Share",      f"{top_cost_pct:.1f}%",           "#ef4444"),
            ]:
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                padding:9px 12px;background:#0a1222;border-radius:8px;margin-bottom:6px;">
                    <span style="color:#4a6080;font-size:0.76rem;">{lbl}</span>
                    <span style="color:{color};font-size:0.82rem;font-weight:700;">{val}</span>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
        font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
        📉 Carbon Cost Distribution</div>""", unsafe_allow_html=True)

        fig_cdist = go.Figure(data=[go.Histogram(
            x=df["carbon_cost"],
            nbinsx=25,
            marker=dict(color="#ef4444", opacity=0.75, line=dict(width=0)),
        )])
        fig_cdist.update_layout(
            **PLOT_LAYOUT, height=180,
            xaxis=dict(title="Carbon Cost (₹)", tickfont=dict(color="#4a6080"),
                       showgrid=False, title_font=dict(color="#4a6080")),
            yaxis=dict(tickfont=dict(color="#4a6080"), showgrid=True, gridcolor="#1e2f4d"),
            bargap=0.05,
        )
        st.plotly_chart(fig_cdist, use_container_width=True)


# ── TAB 4: SHIPMENT AUDIT ─────────────────────
with tab4:

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # Filter controls
    fa1, fa2, fa3 = st.columns([1, 1, 2])
    with fa1:
        band_filter = st.selectbox(
            "Filter by ESG Band",
            ["All", "Excellent", "Good", "Average", "Poor"],
            key="band_filter"
        )
    with fa2:
        vehicle_filter = st.selectbox(
            "Filter by Vehicle",
            ["All"] + sorted(df[vehicle_col].unique().tolist()),
            key="vehicle_filter"
        )

    audit_df = df.copy()
    if band_filter != "All":
        audit_df = audit_df[audit_df["esg_band"] == band_filter]
    if vehicle_filter != "All":
        audit_df = audit_df[audit_df[vehicle_col] == vehicle_filter]

    cols_to_show = [vehicle_col, distance_col, "emission_kgCO2",
                    "carbon_cost", "esg_score", "esg_band"]
    display_df = audit_df[cols_to_show].copy()
    display_df.columns = ["Vehicle", "Distance (km)", "CO₂ (kg)",
                          "Carbon Cost (₹)", "ESG Score", "ESG Band"]
    display_df = display_df.sort_values("CO₂ (kg)", ascending=False)
    display_df["CO₂ (kg)"]        = display_df["CO₂ (kg)"].round(1)
    display_df["Carbon Cost (₹)"] = display_df["Carbon Cost (₹)"].round(0)
    display_df["ESG Score"]        = display_df["ESG Score"].round(1)

    st.markdown(f"""
    <div style="color:#4a6080;font-size:0.75rem;margin-bottom:8px;">
    Showing <span style="color:#10B981;font-weight:700;">{len(display_df):,}</span>
    of {shipment_count:,} shipments
    </div>
    """, unsafe_allow_html=True)

    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTION 4 — ESG INTELLIGENCE INSIGHTS
# ─────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
    <span style="color:#f59e0b;">💡</span>
    <span style="color:#e8f0fe;font-size:0.95rem;font-weight:600;
    font-family:'Space Grotesk',sans-serif;">ESG Intelligence Insights</span>
</div>
""", unsafe_allow_html=True)

savings_if_optimized = total_carbon_cost * 0.20
co2_saved_if_optimized = total_emissions * 0.20

i1, i2, i3 = st.columns(3)

with i1:
    with st.container(border=True):
        st.markdown(f"""
        <div style="padding:4px 0;">
            <div style="color:#fbbf24;font-size:0.7rem;font-weight:700;
            text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">
            ⚠️ Critical Alert</div>
            <div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;margin-bottom:6px;">
            Highest Emitter: {highest_vehicle}</div>
            <div style="color:#7d9bc0;font-size:0.78rem;line-height:1.6;">
            This vehicle type generates
            <span style="color:#ef4444;font-weight:700;">{highest_emission:,.0f} kg CO₂</span>
            total — representing
            <span style="color:#ef4444;font-weight:700;">
            {highest_emission/total_emissions*100:.1f}%</span>
            of your entire fleet emissions.
            Prioritise route optimisation or fleet upgrade for this category.
            </div>
        </div>
        """, unsafe_allow_html=True)

with i2:
    with st.container(border=True):
        st.markdown(f"""
        <div style="padding:4px 0;">
            <div style="color:#22c55e;font-size:0.7rem;font-weight:700;
            text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">
            💰 Cost Saving Opportunity</div>
            <div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;margin-bottom:6px;">
            20% Optimisation Potential</div>
            <div style="color:#7d9bc0;font-size:0.78rem;line-height:1.6;">
            Route and fleet optimisation could save up to
            <span style="color:#22c55e;font-weight:700;">₹{savings_if_optimized:,.0f}</span>
            in carbon costs annually and reduce emissions by
            <span style="color:#22c55e;font-weight:700;">{co2_saved_if_optimized:,.0f} kg CO₂</span>.
            </div>
        </div>
        """, unsafe_allow_html=True)

with i3:
    with st.container(border=True):
        st.markdown(f"""
        <div style="padding:4px 0;">
            <div style="color:#3b82f6;font-size:0.7rem;font-weight:700;
            text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">
            📋 Compliance Status</div>
            <div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;margin-bottom:6px;">
            Fleet ESG Rating: {avg_esg_score:.0f}/100</div>
            <div style="color:#7d9bc0;font-size:0.78rem;line-height:1.6;">
            <span style="color:#f59e0b;font-weight:700;">{poor_shipments}</span> shipments
            are below ESG threshold and at risk of carbon penalty.
            <span style="color:#22c55e;font-weight:700;">{excellent_pct:.0f}%</span>
            of fleet is performing at excellent sustainability levels.
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#1e2f4d;font-size:0.7rem;">
ESG Logistics Control Tower · ESG Analysis Module
</div>
""", unsafe_allow_html=True)