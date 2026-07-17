import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from datetime import datetime

st.set_page_config(
    page_title="Route Optimization | ESG Logistics",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.sidebar import render_sidebar
render_sidebar()

import folium
from streamlit_folium import st_folium

from utils.route_engine import (
    load_data,
    build_multimodal_graph,
    discover_route,
    build_route_segments,
    get_segment_modes,
    get_assets_by_mode,
    calculate_custom_route,
    find_cheapest_route,
    find_fastest_route,
    find_greenest_route,
    build_auto_selection,
    get_city_coordinates,
)

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
  --border-light:   #243556;
  --text-primary:   #e8f0fe;
  --text-secondary: #7d9bc0;
  --text-muted:     #4a6080;
  --green:          #22c55e;
  --blue:           #3b82f6;
  --purple:         #8b5cf6;
  --amber:          #f59e0b;
  --red:            #ef4444;
  --cyan:           #06b6d4;
  --font-head:      'Space Grotesk', sans-serif;
  --font-body:      'DM Sans', sans-serif;
}

* { font-family: var(--font-body); box-sizing: border-box; }
.stApp { background: var(--bg-base) !important; }

[data-testid="stSidebar"] {
  background: var(--bg-surface) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text-secondary) !important; }
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stNumberInput input {
  background: #0a1222 !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text-primary) !important;
  font-size: 0.88rem !important;
}
[data-testid="stSidebar"] label {
  color: var(--text-muted) !important;
  font-size: 0.72rem !important;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-weight: 600 !important;
}

h1, h2, h3 { font-family: var(--font-head) !important; color: var(--text-primary) !important; }
h1 { font-size: 1.5rem !important; font-weight: 700 !important; }
h2 { font-size: 1.1rem !important; font-weight: 600 !important; }
h3 { font-size: 0.92rem !important; font-weight: 600 !important; }

[data-testid="stMetric"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  padding: 16px 18px !important;
}
[data-testid="stMetricLabel"] { color: var(--text-muted) !important; font-size: 0.7rem !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.07em; }
[data-testid="stMetricValue"] { color: var(--text-primary) !important; font-family: var(--font-head) !important; font-size: 1.6rem !important; font-weight: 700 !important; }

[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
}

.stButton > button {
  background: linear-gradient(135deg, #1a3a6b, #1e4080) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-light) !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
  padding: 10px 20px !important;
  transition: all 0.2s !important;
}
.stButton > button:hover {
  background: linear-gradient(135deg, #2a52a0, #1e4080) !important;
  border-color: var(--blue) !important;
  box-shadow: 0 4px 18px rgba(59,130,246,0.3) !important;
}

[data-testid="stDownloadButton"] > button {
  background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
  color: white !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
  padding: 10px 20px !important;
  letter-spacing: 0.02em;
  transition: all 0.2s !important;
  width: 100% !important;
}
[data-testid="stDownloadButton"] > button:hover {
  background: linear-gradient(135deg, #6d28d9, #4338ca) !important;
  box-shadow: 0 4px 18px rgba(124,58,237,0.4) !important;
}

[data-testid="stDownloadButton"] > button:disabled {
  opacity: 0.4 !important;
  cursor: not-allowed !important;
}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: var(--bg-surface) !important;
  border-radius: 10px !important;
  border: 1px solid var(--border) !important;
  padding: 4px !important;
  gap: 4px !important;
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

[data-testid="stDataFrame"] { border: 1px solid var(--border) !important; border-radius: 10px !important; overflow: hidden; }
[data-testid="stDataFrame"] th { background: var(--bg-surface) !important; color: var(--text-muted) !important; font-size: 0.7rem !important; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stDataFrame"] td { color: var(--text-primary) !important; font-size: 0.84rem !important; }

[data-testid="stAlert"] { border-radius: 10px !important; font-size: 0.85rem !important; }
.stSuccess { background: rgba(34,197,94,0.08) !important; border: 1px solid rgba(34,197,94,0.25) !important; }
.stInfo    { background: rgba(59,130,246,0.08) !important; border: 1px solid rgba(59,130,246,0.25) !important; }

.stSelectbox > div > div, .stNumberInput input {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text-primary) !important;
}
.stSelectbox label, .stNumberInput label {
  color: var(--text-muted) !important;
  font-size: 0.72rem !important;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-weight: 600 !important;
}

hr { border-color: var(--border) !important; }
p, li { color: var(--text-secondary); }
[data-testid="stCaptionContainer"] { color: var(--text-muted) !important; font-size: 0.78rem !important; }
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# DATA & GRAPH
# ─────────────────────────────────────────────
DATA_PATH = "data/ESG_Logistics_Final_Master_Dataset.xlsx"
data = load_data(DATA_PATH)
G    = build_multimodal_graph(data)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
for key, default in {
    "discovered_route": None,
    "segments":         None,
    "results":          None,
    "route_plan":       None,
    "_source":          None,
    "_destination":     None,
    "_cargo_weight":    1,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────────
# HELPER — build Excel export bytes
# ─────────────────────────────────────────────
def build_excel_report(results, route, route_plan,
                        cheapest_results, fastest_results, greenest_results,
                        source, destination, cargo_weight):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:

        summary = pd.DataFrame({
            "Metric": ["Source", "Destination", "Cargo Weight (T)",
                       "Distance (km)", "Transport Cost (₹)", "ETA (hrs)",
                       "CO₂ Emission (kg)", "Carbon Tax (₹)",
                       "Diesel (L)", "Marine (L)", "Jet Fuel (L)", "Total Fuel (L)"],
            "Value": [source, destination, cargo_weight,
                      results["distance"], results["cost"], results["eta"],
                      results["co2"], results["carbon_tax"],
                      results["diesel"], results["marine"], results["jet"], results["fuel"]],
        })
        summary.to_excel(writer, sheet_name="KPI Summary", index=False)

        pd.DataFrame(route_plan).to_excel(writer, sheet_name="Route Plan", index=False)

        comp = pd.DataFrame({
            "Metric":   ["Distance (km)", "Cost (₹)", "ETA (hrs)",
                         "Fuel (L)", "CO₂ (kg)", "Carbon Tax (₹)"],
            "Custom":   [results["distance"],          results["cost"],          results["eta"],          results["fuel"],          results["co2"],          results["carbon_tax"]],
            "Cheapest": [cheapest_results["distance"], cheapest_results["cost"], cheapest_results["eta"], cheapest_results["fuel"], cheapest_results["co2"], cheapest_results["carbon_tax"]],
            "Fastest":  [fastest_results["distance"],  fastest_results["cost"],  fastest_results["eta"],  fastest_results["fuel"],  fastest_results["co2"],  fastest_results["carbon_tax"]],
            "Greenest": [greenest_results["distance"], greenest_results["cost"], greenest_results["eta"], greenest_results["fuel"], greenest_results["co2"], greenest_results["carbon_tax"]],
        })
        comp.to_excel(writer, sheet_name="Strategy Comparison", index=False)

        pd.DataFrame({"Stop #": list(range(1, len(route)+1)), "City": route})\
          .to_excel(writer, sheet_name="Route Sequence", index=False)

    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────────
# TOP BAR
# ─────────────────────────────────────────────
top_l, top_r = st.columns([3, 2])

with top_l:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:14px;padding:6px 0 4px 0;">
        <div style="width:44px;height:44px;background:linear-gradient(135deg,#1e3a8a,#1d4ed8);
        border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.4rem;">🚚</div>
        <div>
            <div style="color:#e8f0fe;font-size:1.4rem;font-weight:700;
            font-family:'Space Grotesk',sans-serif;line-height:1.2;">Route Optimization</div>
            <div style="color:#4a6080;font-size:0.78rem;margin-top:2px;">
                AI-powered routes for efficiency &amp; sustainability
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_r:
    st.markdown("<div style='padding-top:8px;'></div>", unsafe_allow_html=True)
    _, btn_col = st.columns([1, 1])

    with btn_col:

        # ── EXPORT FIX — check all required keys ──
        has_results = (
            st.session_state.get("results") is not None
            and st.session_state.get("discovered_route") is not None
            and st.session_state.get("route_plan") is not None
            and st.session_state.get("_source") is not None
            and st.session_state.get("_destination") is not None
        )

        if has_results:
            _r   = st.session_state.results
            _rp  = st.session_state.route_plan
            _rt  = st.session_state.discovered_route
            _src = st.session_state.get("_source")
            _dst = st.session_state.get("_destination")
            _cw  = st.session_state.get("_cargo_weight", 1)

            try:
                _cr   = find_cheapest_route(G, _src, _dst)
                _cs   = build_auto_selection(G, _cr)
                _cres = calculate_custom_route(G, _cr, _cs, _cw)

                _fr   = find_fastest_route(G, _src, _dst)
                _fs   = build_auto_selection(G, _fr)
                _fres = calculate_custom_route(G, _fr, _fs, _cw)

                _gr   = find_greenest_route(G, _src, _dst)
                _gs   = build_auto_selection(G, _gr)
                _gres = calculate_custom_route(G, _gr, _gs, _cw)

                xlsx_bytes = build_excel_report(
                    _r, _rt, _rp,
                    _cres, _fres, _gres,
                    _src, _dst, _cw
                )
                ts = datetime.now().strftime("%Y%m%d_%H%M")

                st.download_button(
                    label="⬇ Export Report (.xlsx)",
                    data=xlsx_bytes,
                    file_name=f"route_report_{_src}_{_dst}_{ts}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            except Exception as e:
                st.download_button(
                    label="⬇ Export Report (.xlsx)",
                    data=b"",
                    file_name="export_error.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    disabled=True,
                    help=f"Export error: {str(e)}",
                )
        else:
            st.download_button(
                label="⬇ Export Report (.xlsx)",
                data=b"",
                file_name="export_pending.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                disabled=True,
                help="Calculate a logistics plan first to enable export",
            )

st.markdown("<hr style='margin:8px 0 16px 0;border-color:#1e2f4d;'>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ROUTE PLANNING INPUTS
# ─────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
    <span style="color:#3b82f6;font-size:1rem;">📍</span>
    <span style="color:#e8f0fe;font-size:0.95rem;font-weight:600;
    font-family:'Space Grotesk',sans-serif;">Route Planning</span>
</div>
""", unsafe_allow_html=True)

cities = sorted(list(G.nodes()))

with st.container(border=True):
    inp1, inp2, inp3, inp4 = st.columns([2, 2, 1.5, 1])

    with inp1:
        source = st.selectbox("🟢 Source City", cities, key="source_city")
    with inp2:
        destination = st.selectbox("🔴 Destination City", cities, key="dest_city")
    with inp3:
        cargo_weight = st.number_input("📦 Cargo Weight (Tons)", min_value=0.1, max_value=10000.0, value=10.0, step=0.1, format="%.2f")
    with inp4:
        st.markdown("<div style='height:27px'></div>", unsafe_allow_html=True)
        discover = st.button("🔍 Discover Route", use_container_width=True)

if discover:
    with st.spinner("🔍 Discovering optimal path..."):
        route = discover_route(G, source, destination)
        st.session_state.discovered_route = route
        st.session_state.segments         = build_route_segments(route)
        st.session_state.results          = None
        st.session_state.route_plan       = None
        st.session_state["_source"]       = source
        st.session_state["_destination"]  = destination
        st.session_state["_cargo_weight"] = cargo_weight


# ─────────────────────────────────────────────
# MODE SELECTION
# ─────────────────────────────────────────────
if st.session_state.discovered_route:
    route    = st.session_state.discovered_route
    segments = st.session_state.segments

    st.markdown(f"""
    <div style="background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.25);
    border-radius:10px;padding:11px 18px;margin:10px 0;">
        <div style="color:#86efac;font-size:0.66rem;text-transform:uppercase;
        letter-spacing:0.07em;font-weight:600;margin-bottom:3px;">✅ Discovered Route</div>
        <div style="color:#e8f0fe;font-size:0.92rem;font-weight:600;
        font-family:'Space Grotesk',sans-serif;">{"  →  ".join(route)}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin:14px 0 10px 0;">
        <span style="color:#f59e0b;">🚚</span>
        <span style="color:#e8f0fe;font-size:0.95rem;font-weight:600;
        font-family:'Space Grotesk',sans-serif;">Transport Mode Selection</span>
    </div>
    """, unsafe_allow_html=True)

    selected_modes = {}
    n_seg = len(segments)

    if n_seg == 0:
        st.warning("No segments found for this route. Please try a different source/destination pair.")
    else:
        cols_per_row = min(n_seg, 4)
        mode_cols    = st.columns(cols_per_row)

        for idx, segment in enumerate(segments):
            src_city        = segment["from"]
            dst_city        = segment["to"]
            available_modes = get_segment_modes(data, src_city, dst_city)

            col = mode_cols[idx % cols_per_row]
            with col:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style="background:#0a1222;border:1px solid #1e2f4d;border-radius:8px;
                    padding:8px 12px;margin-bottom:8px;">
                        <div style="color:#4a6080;font-size:0.64rem;text-transform:uppercase;
                        letter-spacing:0.07em;font-weight:600;">Segment {idx+1}</div>
                        <div style="color:#e8f0fe;font-size:0.82rem;font-weight:600;">
                        {src_city} → {dst_city}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    mode = st.selectbox(
                        "Transport Mode",
                        available_modes,
                        key=f"mode_{src_city}_{dst_city}"
                    )
                    asset = st.selectbox(
                        "Vehicle / Asset",
                        get_assets_by_mode(mode),
                        key=f"asset_{src_city}_{dst_city}"
                    )

            selected_modes[(src_city, dst_city)] = {"mode": mode, "asset": asset}

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        calculate_plan = st.button("📊 Calculate Logistics Plan", use_container_width=True)

        if calculate_plan:
            with st.spinner("⚙️ Calculating plan..."):
                results = calculate_custom_route(G, route, selected_modes, cargo_weight)
                route_plan = [
                    {
                        "Source":      route[i],
                        "Destination": route[i + 1],
                        "Mode":        selected_modes[(route[i], route[i+1])]["mode"],
                        "Vehicle":     selected_modes[(route[i], route[i+1])]["asset"],
                    }
                    for i in range(len(route) - 1)
                ]
                st.session_state.results          = results
                st.session_state.route_plan       = route_plan
                st.session_state["_source"]       = source
                st.session_state["_destination"]  = destination
                st.session_state["_cargo_weight"] = cargo_weight
                st.rerun()


# ─────────────────────────────────────────────
# FULL DASHBOARD (visible after Calculate)
# ─────────────────────────────────────────────
if st.session_state.results is not None:

    results       = st.session_state.results
    route         = st.session_state.discovered_route
    route_plan    = st.session_state.route_plan
    route_plan_df = pd.DataFrame(route_plan)

    source       = st.session_state.get("_source", source)
    destination  = st.session_state.get("_destination", destination)
    cargo_weight = st.session_state.get("_cargo_weight", cargo_weight)

    cheapest_route     = find_cheapest_route(G, source, destination)
    cheapest_selection = build_auto_selection(G, cheapest_route)
    cheapest_results   = calculate_custom_route(G, cheapest_route, cheapest_selection, cargo_weight)

    fastest_route     = find_fastest_route(G, source, destination)
    fastest_selection = build_auto_selection(G, fastest_route)
    fastest_results   = calculate_custom_route(G, fastest_route, fastest_selection, cargo_weight)

    greenest_route     = find_greenest_route(G, source, destination)
    greenest_selection = build_auto_selection(G, greenest_route)
    greenest_results   = calculate_custom_route(G, greenest_route, greenest_selection, cargo_weight)

    def pct_delta(val, ref):
        return round((val - ref) / ref * 100, 1) if ref else 0.0

    cost_delta = pct_delta(results["cost"], cheapest_results["cost"])
    eta_delta  = pct_delta(results["eta"],  fastest_results["eta"])
    co2_delta  = pct_delta(results["co2"],  greenest_results["co2"])

    MODE_COLORS = {"Road": "#f59e0b", "Rail": "#22c55e", "Sea": "#3b82f6", "Air": "#8b5cf6"}

    # ── KPI TILES ──────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin:4px 0 10px 0;">
        <span style="color:#3b82f6;">📊</span>
        <span style="color:#e8f0fe;font-size:0.95rem;font-weight:600;
        font-family:'Space Grotesk',sans-serif;">Logistics KPI Dashboard</span>
    </div>
    """, unsafe_allow_html=True)

    def kpi_card(col, icon, label, value, note, accent):
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
            <div style="color:{accent};font-size:0.7rem;font-weight:600;margin-top:5px;">{note}</div>
        </div>
        """, unsafe_allow_html=True)

    k1, k2, k3, k4, k5 = st.columns(5)
    kpi_card(k1, "📍", "Total Distance",  f"{results['distance']:,.0f} km",  "Route distance",                 "#3b82f6")
    kpi_card(k2, "💰", "Transport Cost",  f"₹{results['cost']:,.0f}",        f"{cost_delta:+.1f}% vs cheapest", "#f59e0b")
    kpi_card(k3, "⏱",  "ETA",            f"{results['eta']:.1f} hrs",       f"{eta_delta:+.1f}% vs fastest",   "#8b5cf6")
    kpi_card(k4, "🌿", "CO₂ Emission",   f"{results['co2']:,.0f} kg",       f"{co2_delta:+.1f}% vs greenest",  "#22c55e")
    kpi_card(k5, "🏭", "Carbon Tax",      f"₹{results['carbon_tax']:,.0f}", "Regulatory cost",                 "#ef4444")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── MAP + ROUTE STOPS ──────────────────────────────────────
    map_col, stops_col = st.columns([2.6, 1.4])

    with map_col:
        with st.container(border=True):
            st.markdown("""
            <div style="display:flex;align-items:center;margin-bottom:8px;gap:8px;">
                <span>🗺</span>
                <span style="color:#e8f0fe;font-size:0.9rem;font-weight:600;
                font-family:'Space Grotesk',sans-serif;">Multimodal Route Map</span>
            </div>
            """, unsafe_allow_html=True)

            legend_html = "<div style='display:flex;gap:14px;margin-bottom:8px;'>"
            for m, c in MODE_COLORS.items():
                legend_html += f"<div style='display:flex;align-items:center;gap:5px;'><span style='color:{c};font-size:1rem;'>━</span><span style='color:#7d9bc0;font-size:0.7rem;'>{m}</span></div>"
            legend_html += "</div>"
            st.markdown(legend_html, unsafe_allow_html=True)

            coords     = get_city_coordinates(data)
            first_city = route[0]
            lat, lon   = coords.get(first_city, (20.59, 78.96))

            india_map = folium.Map(location=[lat, lon], zoom_start=5, tiles="CartoDB dark_matter")

            for city in route:
                if city not in coords:
                    continue
                clat, clon = coords[city]
                if city == route[0]:
                    ic, col = "play", "green"
                elif city == route[-1]:
                    ic, col = "flag", "red"
                else:
                    ic, col = "building", "blue"
                folium.Marker(
                    [clat, clon], tooltip=city, popup=city,
                    icon=folium.Icon(color=col, icon=ic, prefix="fa")
                ).add_to(india_map)

            for row in route_plan:
                sc, dc = row["Source"], row["Destination"]
                if sc not in coords or dc not in coords:
                    continue
                slat, slon = coords[sc]
                elat, elon = coords[dc]
                folium.PolyLine(
                    [[slat, slon], [elat, elon]],
                    color=MODE_COLORS.get(row["Mode"], "gray"),
                    weight=5, opacity=0.9, popup=row["Mode"]
                ).add_to(india_map)

            st_folium(india_map, width=None, height=430)

    with stops_col:
        with st.container(border=True):
            st.markdown("""
            <div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
            font-family:'Space Grotesk',sans-serif;margin-bottom:12px;">
            📍 Route Stops (Optimized)</div>
            """, unsafe_allow_html=True)

            for idx, city in enumerate(route):
                is_first  = idx == 0
                is_last   = idx == len(route) - 1
                dot_c     = "#22c55e" if is_first else ("#ef4444" if is_last else "#3b82f6")
                lbl       = "Start" if is_first else ("End" if is_last else f"Hub {idx}")
                connector = ("" if is_last else
                    "<div style='width:2px;height:16px;background:#1e2f4d;margin:2px 0 2px 11px;'></div>")
                st.markdown(f"""
                <div>
                  <div style="display:flex;align-items:center;gap:10px;">
                    <div style="width:24px;height:24px;background:{dot_c}22;border:2px solid {dot_c};
                    border-radius:50%;display:flex;align-items:center;justify-content:center;
                    font-size:0.62rem;font-weight:800;color:{dot_c};flex-shrink:0;">{idx+1}</div>
                    <div>
                      <div style="color:#e8f0fe;font-size:0.8rem;font-weight:600;">{city}</div>
                      <div style="color:#4a6080;font-size:0.68rem;">{lbl}</div>
                    </div>
                  </div>
                  {connector}
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="margin-top:10px;background:#0a1222;border-radius:8px;padding:8px 12px;
            display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="color:#4a6080;font-size:0.7rem;">Total Distance</span>
                <span style="color:#e8f0fe;font-size:0.7rem;font-weight:600;">{results['distance']:,.0f} km</span>
            </div>
            <div style="background:#0a1222;border-radius:8px;padding:8px 12px;
            display:flex;justify-content:space-between;">
                <span style="color:#4a6080;font-size:0.7rem;">Total ETA</span>
                <span style="color:#e8f0fe;font-size:0.7rem;font-weight:600;">{results['eta']:.1f} hrs</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── CHARTS ROW ─────────────────────────────────────────────
    ch1, ch2, ch3 = st.columns([1.3, 1.3, 1.4])

    with ch1:
        with st.container(border=True):
            st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
            font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
            ⛽ Distance by Mode</div>""", unsafe_allow_html=True)

            mode_dist = {}
            for row in route_plan:
                mode_dist[row["Mode"]] = mode_dist.get(row["Mode"], 0) + (
                    results["distance"] / max(len(route_plan), 1)
                )

            donut = go.Figure(data=[go.Pie(
                labels=list(mode_dist.keys()),
                values=list(mode_dist.values()),
                hole=0.65,
                marker=dict(colors=["#3b82f6","#22c55e","#f59e0b","#8b5cf6"]),
                textinfo="none",
                hovertemplate="%{label}: %{value:.0f} km (%{percent})<extra></extra>"
            )])
            donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=5,b=5,l=5,r=5), height=200, showlegend=True,
                legend=dict(font=dict(color="#7d9bc0",size=10),
                            bgcolor="rgba(0,0,0,0)", orientation="v", x=0.75, y=0.5),
                annotations=[dict(
                    text=f"{results['distance']:,.0f}<br>km",
                    x=0.35, y=0.5,
                    font=dict(size=13, color="#e8f0fe", family="Space Grotesk"),
                    showarrow=False, align="center"
                )]
            )
            st.plotly_chart(donut, use_container_width=True)

    with ch2:
        with st.container(border=True):
            st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
            font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
            🌱 Environmental Impact</div>""", unsafe_allow_html=True)

            st.markdown(f"""
            <div style="text-align:center;padding:8px 0 4px 0;">
                <div style="color:#e8f0fe;font-size:1.9rem;font-weight:800;
                font-family:'Space Grotesk',sans-serif;">{results['co2']:,.1f} kg</div>
                <div style="color:#4a6080;font-size:0.7rem;">CO₂ Emissions</div>
                <div style="display:inline-block;background:rgba(34,197,94,0.12);
                border:1px solid rgba(34,197,94,0.3);border-radius:99px;
                padding:3px 10px;margin-top:6px;">
                    <span style="color:#86efac;font-size:0.7rem;font-weight:700;">
                    {co2_delta:+.0f}% vs greenest</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            env_bar = go.Figure(data=[go.Bar(
                x=["Current Route", "Optimized"],
                y=[results["co2"] * 1.25, results["co2"]],
                marker=dict(color=["#374151", "#22c55e"], line=dict(width=0)),
                text=[f"{results['co2']*1.25:,.0f} kg", f"{results['co2']:,.0f} kg"],
                textposition="outside",
                textfont=dict(color="#7d9bc0", size=10),
            )])
            env_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10,b=5,l=5,r=5), height=110, showlegend=False,
                xaxis=dict(tickfont=dict(color="#4a6080",size=10), showgrid=False),
                yaxis=dict(visible=False),
            )
            st.plotly_chart(env_bar, use_container_width=True)

    with ch3:
        with st.container(border=True):
            st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
            font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
            🚛 Route Execution Plan</div>""", unsafe_allow_html=True)

            for i, row in enumerate(route_plan):
                mc = MODE_COLORS.get(row["Mode"], "#64748b")
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:7px 10px;
                background:#0a1222;border-radius:8px;margin-bottom:5px;">
                    <div style="width:22px;height:22px;background:{mc}22;border-radius:6px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:0.66rem;font-weight:800;color:{mc};flex-shrink:0;">{i+1}</div>
                    <div style="flex:1;min-width:0;">
                        <div style="color:#e8f0fe;font-size:0.76rem;font-weight:600;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        {row['Source']} → {row['Destination']}</div>
                        <div style="color:#4a6080;font-size:0.66rem;">{row.get('Vehicle','—')}</div>
                    </div>
                    <div style="background:{mc}22;border:1px solid {mc}44;border-radius:99px;
                    padding:2px 8px;color:{mc};font-size:0.66rem;font-weight:700;white-space:nowrap;">
                    {row['Mode']}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── FUEL BREAKDOWN ─────────────────────────────────────────
    with st.container(border=True):
        st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
        font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
        ⛽ Fuel Consumption Analysis</div>""", unsafe_allow_html=True)

        fc1, fc2, fc3, fc4 = st.columns(4)
        for col, lbl, val, color in [
            (fc1, "⛽ Diesel",    results["diesel"],  "#f59e0b"),
            (fc2, "⚓ Marine",    results["marine"],  "#3b82f6"),
            (fc3, "✈️ Jet Fuel", results["jet"],     "#8b5cf6"),
            (fc4, "📊 Total",     results["fuel"],    "#22c55e"),
        ]:
            col.markdown(f"""
            <div style="background:#0a1222;border:1px solid #1e2f4d;border-radius:10px;
            padding:14px 16px;text-align:center;">
                <div style="color:#4a6080;font-size:0.66rem;text-transform:uppercase;
                letter-spacing:0.07em;font-weight:600;">{lbl}</div>
                <div style="color:{color};font-size:1.35rem;font-weight:800;
                font-family:'Space Grotesk',sans-serif;margin:4px 0;">{val:,.0f}</div>
                <div style="color:#4a6080;font-size:0.68rem;">litres</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── STRATEGY TABS ──────────────────────────────────────────
    st.markdown("""<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <span style="color:#22c55e;">🎯</span>
        <span style="color:#e8f0fe;font-size:0.95rem;font-weight:600;
        font-family:'Space Grotesk',sans-serif;">Optimization Strategies</span>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["💰 Cheapest", "⚡ Fastest", "🌱 Greenest"])

    def strategy_tab(res, route_data, accent):
        c1, c2, c3 = st.columns(3)
        for col, lbl, val in [
            (c1, "Cost",  f"₹{res['cost']:,.0f}"),
            (c2, "ETA",   f"{res['eta']:.1f} hrs"),
            (c3, "CO₂",   f"{res['co2']:,.0f} kg"),
        ]:
            col.markdown(f"""
            <div style="background:#0a1222;border:1px solid {accent}33;border-radius:10px;
            padding:12px 16px;border-top:3px solid {accent};">
                <div style="color:#4a6080;font-size:0.66rem;text-transform:uppercase;
                letter-spacing:0.07em;font-weight:600;">{lbl}</div>
                <div style="color:#e8f0fe;font-size:1.25rem;font-weight:700;
                font-family:'Space Grotesk',sans-serif;">{val}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);
        border-radius:8px;padding:10px 14px;margin-top:8px;">
            <span style="color:#86efac;font-size:0.84rem;font-weight:600;">
            {"  →  ".join(route_data)}</span>
        </div>
        """, unsafe_allow_html=True)

    with tab1:
        strategy_tab(cheapest_results, cheapest_route, "#f59e0b")
    with tab2:
        strategy_tab(fastest_results,  fastest_route,  "#8b5cf6")
    with tab3:
        strategy_tab(greenest_results, greenest_route, "#22c55e")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── STRATEGY COMPARISON TABLE + BAR CHART ─────────────────
    with st.container(border=True):
        tbl_col, bar_col = st.columns([1.4, 1])

        with tbl_col:
            st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
            font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
            📈 Strategy Comparison</div>""", unsafe_allow_html=True)

            comp_df = pd.DataFrame({
                "Metric":   ["Distance (km)","Cost (₹)","ETA (hrs)","Fuel (L)","CO₂ (kg)","Carbon Tax (₹)"],
                "Custom":   [results["distance"],          results["cost"],          results["eta"],          results["fuel"],          results["co2"],          results["carbon_tax"]],
                "Cheapest": [cheapest_results["distance"], cheapest_results["cost"], cheapest_results["eta"], cheapest_results["fuel"], cheapest_results["co2"], cheapest_results["carbon_tax"]],
                "Fastest":  [fastest_results["distance"],  fastest_results["cost"],  fastest_results["eta"],  fastest_results["fuel"],  fastest_results["co2"],  fastest_results["carbon_tax"]],
                "Greenest": [greenest_results["distance"], greenest_results["cost"], greenest_results["eta"], greenest_results["fuel"], greenest_results["co2"], greenest_results["carbon_tax"]],
            })
            st.dataframe(comp_df, use_container_width=True, hide_index=True)

        with bar_col:
            st.markdown("""<div style="color:#e8f0fe;font-size:0.88rem;font-weight:600;
            font-family:'Space Grotesk',sans-serif;margin-bottom:8px;">
            💰 Cost Comparison</div>""", unsafe_allow_html=True)

            bar = go.Figure(data=[go.Bar(
                x=["Custom","Cheapest","Fastest","Greenest"],
                y=[results["cost"],cheapest_results["cost"],fastest_results["cost"],greenest_results["cost"]],
                marker=dict(color=["#3b82f6","#f59e0b","#8b5cf6","#22c55e"], line=dict(width=0)),
                text=[f"₹{v:,.0f}" for v in [results["cost"],cheapest_results["cost"],fastest_results["cost"],greenest_results["cost"]]],
                textposition="outside", textfont=dict(color="#7d9bc0", size=10),
            )])
            bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10,b=5,l=5,r=5), height=230, showlegend=False,
                xaxis=dict(tickfont=dict(color="#4a6080",size=11), showgrid=False),
                yaxis=dict(visible=False), bargap=0.35,
            )
            st.plotly_chart(bar, use_container_width=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center;color:#1e2f4d;font-size:0.7rem;">
    ESG Logistics Control Tower · Route Optimization Module
    </div>
    """, unsafe_allow_html=True)