import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime
import requests

st.set_page_config(
    page_title="Mobility Assistant | ESG Logistics",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.sidebar import render_sidebar
render_sidebar() 



genai.configure(
    api_key="AIzaSyBKIOck8kS4A14PMiajDBDz5-Idx2xzbnU"
)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)


st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

.stApp {
    background-color: #0B1120;
    color: #E2E8F0;
}

[data-testid="stSidebar"] {
    background-color: #0D1526 !important;
    border-right: 1px solid #1E293B;
}

[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stTextInput label {
    color: #94A3B8 !important;
    font-size: 0.78rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

[data-testid="stSidebar"] input,
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #141E33 !important;
    border: 1px solid #1E293B !important;
    border-radius: 8px !important;
    color: #E2E8F0 !important;
}

[data-testid="stMetric"] {
    background: linear-gradient(135deg, #141E33 0%, #1A2640 100%);
    border: 1px solid #1E293B;
    border-radius: 12px;
    padding: 16px 20px;
}

[data-testid="stMetricLabel"] {
    color: #64748B !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

[data-testid="stMetricValue"] {
    color: #F1F5F9 !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(135deg, #111827 0%, #141E33 100%) !important;
    border: 1px solid #1E293B !important;
    border-radius: 14px !important;
    padding: 4px !important;
}

h3 {
    color: #F1F5F9 !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em;
}

[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 0.85rem !important;
}

.stButton > button {
    background: linear-gradient(135deg, #7C3AED, #4F46E5) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 12px 20px !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.02em;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #6D28D9, #4338CA) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(124, 58, 237, 0.4) !important;
}

[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #10B981, #059669) !important;
    border-radius: 10px !important;
}

h1 {
    color: #F8FAFC !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}

hr { border-color: #1E293B !important; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

[data-testid="stCaptionContainer"] { color: #64748B !important; }

p, li, span { color: #CBD5E1; }

.section-heading {
    font-size: 0.85rem;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 16px 0 8px 0;
}

</style>
""", unsafe_allow_html=True)

# =====================================
# WEATHER HELPER — Open-Meteo (FREE, no API key)
# =====================================

WMO_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌦️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "🌨️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}

WMO_DESC = {
    0: "Clear", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Foggy", 48: "Foggy",
    51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
    61: "Rain", 63: "Rain", 65: "Heavy Rain",
    71: "Snow", 73: "Snow", 75: "Heavy Snow",
    80: "Showers", 81: "Showers", 82: "Heavy Showers",
    95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm",
}

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_weather(city: str):
    """
    Fetch live weather for a city using:
    1. Open-Meteo Geocoding API  → lat/lon from city name (free, no key)
    2. Open-Meteo Forecast API   → current temp + weather code (free, no key)
    Returns dict with temp, icon, description, city_name or None on failure.
    """
    try:
        city = city.strip()
        if not city:
            return None

        # Step 1: Geocode city → lat/lon
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {"name": city, "count": 1, "language": "en", "format": "json"}
        geo_resp = requests.get(geo_url, params=geo_params, timeout=5)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return None

        result = geo_data["results"][0]
        lat = result["latitude"]
        lon = result["longitude"]
        city_name = result.get("name", city)
        country = result.get("country_code", "")

        # Step 2: Fetch current weather
        wx_url = "https://api.open-meteo.com/v1/forecast"
        wx_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weathercode",
            "temperature_unit": "celsius",
            "timezone": "auto",
        }
        wx_resp = requests.get(wx_url, params=wx_params, timeout=5)
        wx_resp.raise_for_status()
        wx_data = wx_resp.json()

        current = wx_data.get("current", {})
        temp = current.get("temperature_2m")
        code = current.get("weathercode", 0)

        if temp is None:
            return None

        return {
            "temp": round(temp),
            "icon": WMO_ICONS.get(code, "🌡️"),
            "desc": WMO_DESC.get(code, ""),
            "city": f"{city_name}, {country}" if country else city_name,
        }

    except Exception:
        return None


# =====================================
# PAGE HEADER
# =====================================

today = datetime.now().strftime("%d %B %Y")

col_logo, col_title, col_meta = st.columns([0.5, 3, 2])

with col_logo:
    st.markdown("## 🚗")

with col_title:
    st.markdown("# Mobility Assistant ✨")
    st.caption("Make smarter mobility choices for a sustainable future.")

# Weather card is rendered after sidebar inputs are read,
# so we use a placeholder and fill it once 'city' is known.
weather_placeholder = col_meta.empty()

# =====================================
# SIDEBAR — INPUT PANEL
# =====================================

with st.sidebar:

    st.markdown("""
    <div style="display:flex; align-items:center; gap:10px; padding:12px 0 20px 0;
    border-bottom:1px solid #1E293B; margin-bottom:16px;">
        <span style="font-size:1.6rem;">🌿</span>
        <div>
            <div style="color:#F1F5F9; font-weight:700; font-size:0.95rem;">ESG Control Tower</div>
            <div style="color:#64748B; font-size:0.72rem;">Mobility Module</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-heading">📋 Mobility Analysis Inputs</div>', unsafe_allow_html=True)

    vehicle_type = st.selectbox(
        "Vehicle Type",
        ["Petrol Car", "Diesel Car", "Hybrid", "EV", "Motorcycle"]
    )

    daily_distance = st.number_input(
        "Daily Travel Distance (km)",
        min_value=1,
        value=30
    )

    fuel_price = st.number_input(
        "Fuel Price (₹ / Litre)",
        min_value=1,
        value=105
    )

    travel_days = st.number_input(
        "Travel Days Per Month",
        min_value=1,
        value=22
    )

    mileage = st.number_input(
        "Mileage (km/L)",
        min_value=1.0,
        value=15.0
    )

    priority = st.selectbox(
        "Travel Priority",
        ["Balanced (Cost + Sustainability)", "Cheapest", "Fastest", "Greenest"]
    )

    st.markdown('<div class="section-heading">👤 User Profile</div>', unsafe_allow_html=True)

    user_name = st.text_input("Name", placeholder="Enter your name")

    profession = st.selectbox(
        "Profession",
        ["Student", "Working Professional", "Business Owner"]
    )

    city = st.text_input("City", placeholder="e.g. Mumbai", value="Mumbai")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if "analyze_clicked" not in st.session_state:
        st.session_state.analyze_clicked = False

    if st.button("🚀 Analyze Mobility", use_container_width=True):
        st.session_state.analyze_clicked = True

    st.markdown("---")

    st.markdown("""
    <div style="background:linear-gradient(135deg,#1E1040,#2D1B69); border:1px solid #4C1D95;
    border-radius:12px; padding:16px;">
        <div style="color:#A78BFA; font-weight:700; font-size:0.9rem; margin-bottom:6px;">🤖 AI Mobility Coach</div>
        <div style="color:#94A3B8; font-size:0.78rem; line-height:1.5;">Get personalized advice on how to travel smarter, cheaper and greener.</div>
    </div>
    """, unsafe_allow_html=True)

# =====================================
# RENDER WEATHER CARD (after city input is available)
# =====================================

weather = get_weather(city) if city.strip() else None

with weather_placeholder:
    if weather:
        weather_display = f"{weather['icon']} {weather['temp']}°C"
        weather_label   = weather['desc']
        city_label      = weather['city']
    else:
        weather_display = "🌡️ N/A"
        weather_label   = "Enter city above"
        city_label      = city.strip() or "—"

    st.markdown(f"""
    <div style="display:flex; gap:12px; justify-content:flex-end; align-items:center; padding-top:8px;">
        <div style="background:#141E33; border:1px solid #1E293B; border-radius:10px; padding:8px 16px; text-align:center;">
            <div style="color:#64748B; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.05em;">Today's Date</div>
            <div style="color:#F1F5F9; font-weight:700; font-size:0.9rem;">{today}</div>
        </div>
        <div style="background:#141E33; border:1px solid #1E293B; border-radius:10px; padding:8px 16px; text-align:center; min-width:110px;">
            <div style="color:#64748B; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.05em;">{city_label}</div>
            <div style="color:#F1F5F9; font-weight:700; font-size:0.9rem;">{weather_display}</div>
            <div style="color:#94A3B8; font-size:0.68rem;">{weather_label}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# =====================================
# HELPER FUNCTIONS
# =====================================

def get_mobility_advice(vehicle_type, monthly_cost, monthly_co2, priority):
    prompt = f"""
You are an ESG mobility consultant.
Vehicle: {vehicle_type}
Monthly Cost: ₹{monthly_cost:.0f}
Monthly CO2: {monthly_co2:.1f} kg
Priority: {priority}

Provide 3 short bullet points:
1. Best Option for You (one line recommendation)
2. Expected Monthly Savings (estimate ₹ amount)
3. CO2 Reduction % possible

Keep each point under 15 words. Use ₹ symbol.
"""
    response = model.generate_content(prompt)
    return response.text


def generate_weekly_plan(vehicle_type, daily_distance, priority):
    prompt = f"""
Create a weekly sustainable commute plan.
Vehicle: {vehicle_type}
Daily Distance: {daily_distance} km
Priority: {priority}

Return exactly 5 lines, one per day:
Monday: [plan]
Tuesday: [plan]
Wednesday: [plan]
Thursday: [plan]
Friday: [plan]

Keep each line under 12 words.
"""
    response = model.generate_content(prompt)
    return response.text


def generate_improvement_roadmap(mobility_score):
    prompt = f"""
Current Mobility Score: {mobility_score}/100
Create a 3-step improvement roadmap. Label each: Step 1, Step 2, Step 3.
Keep it under 70 words total.
"""
    response = model.generate_content(prompt)
    return response.text


def get_persona_description(persona, monthly_cost, monthly_co2):
    prompt = f"""
Commute Persona: {persona}
Monthly Cost: ₹{monthly_cost:.0f}
Monthly CO2: {monthly_co2:.1f} kg

Write 2 sentences describing this commuter's style and one motivational tip.
Under 40 words total.
"""
    response = model.generate_content(prompt)
    return response.text


# =====================================
# CALCULATIONS & DASHBOARD
# =====================================

if st.session_state.analyze_clicked:

    monthly_distance = daily_distance * travel_days
    fuel_used = monthly_distance / mileage
    monthly_cost = fuel_used * fuel_price

    co2_factors = {
        "Petrol Car": 2.31,
        "Diesel Car": 2.68,
        "Hybrid": 1.50,
        "EV": 0.50,
        "Motorcycle": 1.80
    }
    co2_factor = co2_factors.get(vehicle_type, 2.31)
    monthly_co2 = fuel_used * co2_factor

    cost_score = max(0, 100 - (monthly_cost / 100))
    sustainability_score = max(0, 100 - monthly_co2)
    health_score = 80
    convenience_score = 90

    mobility_score = round(
        (cost_score + sustainability_score + health_score + convenience_score) / 4
    )

    esg_score = round(
        sustainability_score * 0.6 + health_score * 0.2 + cost_score * 0.2
    )

    savings_potential = monthly_cost - 600

    if mobility_score >= 75:
        score_label = "Great Job! 🎉"
        score_color = "#10B981"
        score_pct = "76%"
    elif mobility_score >= 50:
        score_label = "Good Progress 👍"
        score_color = "#F59E0B"
        score_pct = "50%"
    else:
        score_label = "Needs Improvement ⚠️"
        score_color = "#EF4444"
        score_pct = "30%"

    if monthly_co2 < 20:
        persona = "🌱 Eco Explorer"
        persona_color = "#10B981"
    elif monthly_cost < 3000:
        persona = "💰 Cost Saver"
        persona_color = "#F59E0B"
    elif mobility_score >= 70:
        persona = "⚡ The Efficient Commuter"
        persona_color = "#8B5CF6"
    else:
        persona = "🚗 Daily Commuter"
        persona_color = "#64748B"

    # =====================================
    # ROW 1 — KPI METRICS
    # =====================================

    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        with st.container(border=True):
            st.markdown(f"""
            <div style="padding:4px 0;">
                <div style="color:#64748B; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">📊 Mobility Score</div>
                <div style="color:{score_color}; font-size:2rem; font-weight:800; line-height:1;">{mobility_score}</div>
                <div style="color:{score_color}; font-size:0.75rem; margin-top:4px;">{score_label}</div>
                <div style="color:#64748B; font-size:0.7rem;">Better than {score_pct} of users</div>
            </div>
            """, unsafe_allow_html=True)

    with m2:
        with st.container(border=True):
            st.markdown(f"""
            <div style="padding:4px 0;">
                <div style="color:#64748B; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">💰 Monthly Cost</div>
                <div style="color:#F1F5F9; font-size:2rem; font-weight:800; line-height:1;">₹{monthly_cost:,.0f}</div>
                <div style="color:#64748B; font-size:0.72rem; margin-top:4px;">Total Estimated Cost</div>
            </div>
            """, unsafe_allow_html=True)

    with m3:
        with st.container(border=True):
            st.markdown(f"""
            <div style="padding:4px 0;">
                <div style="color:#64748B; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">☁️ Monthly CO₂</div>
                <div style="color:#F1F5F9; font-size:2rem; font-weight:800; line-height:1;">{monthly_co2:.1f} <span style="font-size:1rem;">kg</span></div>
                <div style="color:#64748B; font-size:0.72rem; margin-top:4px;">Total Emission</div>
            </div>
            """, unsafe_allow_html=True)

    with m4:
        with st.container(border=True):
            st.markdown(f"""
            <div style="padding:4px 0;">
                <div style="color:#64748B; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">📍 Distance / Month</div>
                <div style="color:#F1F5F9; font-size:2rem; font-weight:800; line-height:1;">{monthly_distance:.0f} <span style="font-size:1rem;">km</span></div>
                <div style="color:#64748B; font-size:0.72rem; margin-top:4px;">Total Distance</div>
            </div>
            """, unsafe_allow_html=True)

    with m5:
        with st.container(border=True):
            st.markdown(f"""
            <div style="padding:4px 0;">
                <div style="color:#64748B; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">🐷 Savings Potential</div>
                <div style="color:#10B981; font-size:2rem; font-weight:800; line-height:1;">₹{max(0,savings_potential):,.0f}</div>
                <div style="color:#64748B; font-size:0.72rem; margin-top:4px;">vs Metro per month</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    # =====================================
    # ROW 2 — Comparison | AI Rec | What-If
    # =====================================

    row2_a, row2_b, row2_c = st.columns([2.5, 1.8, 2.2])

    with row2_a:
        with st.container(border=True):

            st.markdown("### 🚘 Transport Alternatives Comparison")

            alt_modes = ["Current Car", "Metro", "Electric Vehicle", "Hybrid Car", "Bicycle"]
            alt_costs = [
                round(monthly_cost), 600,
                round(monthly_cost * 0.21),
                round(monthly_cost * 0.66), 0
            ]
            alt_co2 = [
                round(monthly_co2), 4,
                round(monthly_co2 * 0.09),
                round(monthly_co2 * 0.60), 0
            ]
            alt_scores = [
                max(0, min(100, round(100 - monthly_co2 * 0.5))),
                95, 97, 88, 100
            ]
            score_colors_list = ["#EF4444", "#10B981", "#10B981", "#F59E0B", "#10B981"]

            comparison_df = pd.DataFrame({
                "Mode": alt_modes,
                "Monthly Cost (₹)": alt_costs,
                "CO₂ (kg/mo)": alt_co2,
            })

            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True
            )

            cols_scores = st.columns(5)
            for i, (sc, color) in enumerate(zip(alt_scores, score_colors_list)):
                with cols_scores[i]:
                    st.markdown(f"""
                    <div style="background:{color}22; border:1px solid {color}44; border-radius:20px;
                    text-align:center; padding:3px 0; color:{color}; font-size:0.78rem; font-weight:700;">
                        {sc}
                    </div>""", unsafe_allow_html=True)

    with row2_b:
        with st.container(border=True):

            st.markdown("### 🤖 AI Recommendation")

            with st.spinner("Analyzing..."):
                advice = get_mobility_advice(
                    vehicle_type, monthly_cost, monthly_co2, priority
                )

            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.25);
            border-radius:10px; padding:14px; margin-bottom:10px;">
                <div style="color:#10B981; font-weight:700; font-size:0.82rem; margin-bottom:6px;">✅ Best Option For You</div>
                <div style="color:#D1FAE5; font-size:0.82rem; line-height:1.6;">{advice}</div>
            </div>
            """, unsafe_allow_html=True)

            est_savings = round(max(0, monthly_cost - 900))

            st.markdown(f"""
            <div style="display:flex; flex-direction:column; gap:6px;">
                <div style="background:#141E33; border-radius:8px; padding:8px 12px; display:flex; justify-content:space-between;">
                    <span style="color:#94A3B8; font-size:0.78rem;">💸 Expected Savings</span>
                    <span style="color:#34D399; font-size:0.78rem; font-weight:700;">₹{est_savings:,}/mo</span>
                </div>
                <div style="background:#141E33; border-radius:8px; padding:8px 12px; display:flex; justify-content:space-between;">
                    <span style="color:#94A3B8; font-size:0.78rem;">🌿 CO₂ Reduction</span>
                    <span style="color:#34D399; font-size:0.78rem; font-weight:700;">~68%</span>
                </div>
                <div style="background:#141E33; border-radius:8px; padding:8px 12px; display:flex; justify-content:space-between;">
                    <span style="color:#94A3B8; font-size:0.78rem;">❤️ Health Impact</span>
                    <span style="color:#FCD34D; font-size:0.78rem; font-weight:700;">Moderate</span>
                </div>
                <div style="background:#141E33; border-radius:8px; padding:8px 12px; display:flex; justify-content:space-between;">
                    <span style="color:#94A3B8; font-size:0.78rem;">📈 Score Increase</span>
                    <span style="color:#34D399; font-size:0.78rem; font-weight:700;">+12 Points</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with row2_c:
        with st.container(border=True):

            st.markdown("### 🔮 What-If Simulator")

            wfh_days = st.slider("Work From Home Days / Week", 0, 5, 2)
            future_fuel = st.slider("Fuel Price (₹ / Litre)", 80, 150, int(fuel_price))
            future_distance = st.slider("Daily Distance (km)", 5, 100, int(daily_distance))
            sim_vehicle = st.selectbox(
                "Vehicle Type",
                ["Petrol Car", "Diesel Car", "Hybrid", "EV", "Motorcycle"],
                key="sim_veh"
            )

            adjusted_days = travel_days - (wfh_days * 4)
            future_monthly_distance = future_distance * adjusted_days
            future_fuel_used = future_monthly_distance / mileage
            future_monthly_cost = future_fuel_used * future_fuel
            money_saved = monthly_cost - future_monthly_cost
            co2_saved_annual = (monthly_co2 - (future_fuel_used * co2_factor)) * 12
            time_saved = wfh_days * 4 * (daily_distance / 30)

            st.markdown(f"""
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:8px;">
                <div style="background:rgba(124,58,237,0.1); border:1px solid rgba(124,58,237,0.25); border-radius:8px; padding:10px;">
                    <div style="color:#A78BFA; font-size:0.7rem; margin-bottom:2px;">💰 Money Saved</div>
                    <div style="color:#F1F5F9; font-weight:700; font-size:0.95rem;">₹{abs(money_saved)*12:,.0f}/yr</div>
                </div>
                <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.25); border-radius:8px; padding:10px;">
                    <div style="color:#6EE7B7; font-size:0.7rem; margin-bottom:2px;">🌿 CO₂ Reduced</div>
                    <div style="color:#F1F5F9; font-weight:700; font-size:0.95rem;">{abs(co2_saved_annual):.0f} kg/yr</div>
                </div>
                <div style="background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.25); border-radius:8px; padding:10px; grid-column:span 2;">
                    <div style="color:#FCD34D; font-size:0.7rem; margin-bottom:2px;">⏱ Time Saved</div>
                    <div style="color:#F1F5F9; font-weight:700; font-size:0.95rem;">{abs(time_saved)*60:.0f} hours/year</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    # =====================================
    # ROW 3 — Hidden Costs | Future Impact | Persona
    # =====================================

    row3_a, row3_b, row3_c = st.columns([1.5, 2.2, 1.5])

    with row3_a:
        with st.container(border=True):

            st.markdown(f"### 💰 Hidden Cost Breakdown ({vehicle_type})")

            fuel_cost = round(monthly_cost)
            parking_cost = 1200
            maintenance_cost = round(monthly_cost * 0.20)
            insurance_cost = 800
            total_hidden = fuel_cost + parking_cost + maintenance_cost + insurance_cost

            st.metric("Total / Month", f"₹{total_hidden:,}")

            hidden_fig = go.Figure(data=[go.Pie(
                labels=["Fuel", "Parking", "Maintenance", "Insurance"],
                values=[fuel_cost, parking_cost, maintenance_cost, insurance_cost],
                hole=0.62,
                marker=dict(colors=["#6366F1", "#EF4444", "#F59E0B", "#06B6D4"]),
                textinfo="none",
                hovertemplate="%{label}: ₹%{value} (%{percent})<extra></extra>"
            )])

            hidden_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10, b=10, l=10, r=10),
                height=200,
                showlegend=True,
                legend=dict(
                    font=dict(color="#94A3B8", size=10),
                    bgcolor="rgba(0,0,0,0)",
                    orientation="v",
                    x=0.72,
                    y=0.5
                ),
                annotations=[dict(
                    text=f"₹{total_hidden:,}",
                    x=0.34, y=0.5,
                    font=dict(size=13, color="#F1F5F9", family="Inter"),
                    showarrow=False
                )]
            )

            st.plotly_chart(hidden_fig, use_container_width=True)

    with row3_b:
        with st.container(border=True):

            st.markdown("### 📈 Future Impact")

            years = st.selectbox("Projection Period", [1, 3, 5], index=2)

            future_total_cost = monthly_cost * 12 * years
            future_total_co2 = monthly_co2 * 12 * years
            metro_total_cost = 600 * 12 * years
            savings_if_metro = future_total_cost - metro_total_cost
            co2_if_metro = 4 * 12 * years

            f_col1, f_col2 = st.columns(2)

            with f_col1:
                st.markdown(f"""
                <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2);
                border-radius:10px; padding:14px; height:100%;">
                    <div style="color:#EF4444; font-weight:700; font-size:0.8rem; margin-bottom:10px;">
                        🔴 If you continue current habits
                    </div>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        <div>
                            <div style="color:#94A3B8; font-size:0.7rem;">Total Spend</div>
                            <div style="color:#FCA5A5; font-weight:700; font-size:1.1rem;">₹{future_total_cost/100000:.1f} Lakhs</div>
                        </div>
                        <div>
                            <div style="color:#94A3B8; font-size:0.7rem;">CO₂ Emission</div>
                            <div style="color:#FCA5A5; font-weight:700; font-size:1.1rem;">{future_total_co2/1000:.1f} Tonnes</div>
                        </div>
                        <div>
                            <div style="color:#94A3B8; font-size:0.7rem;">Time in Traffic</div>
                            <div style="color:#FCA5A5; font-weight:700; font-size:1.1rem;">{travel_days * 12 * years * 1.2:.0f} Hours</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with f_col2:
                st.markdown(f"""
                <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.2);
                border-radius:10px; padding:14px; height:100%;">
                    <div style="color:#10B981; font-weight:700; font-size:0.8rem; margin-bottom:10px;">
                        🟢 If you switch to Metro
                    </div>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        <div>
                            <div style="color:#94A3B8; font-size:0.7rem;">Total Savings</div>
                            <div style="color:#6EE7B7; font-weight:700; font-size:1.1rem;">₹{savings_if_metro/100000:.1f} Lakhs</div>
                        </div>
                        <div>
                            <div style="color:#94A3B8; font-size:0.7rem;">CO₂ Reduction</div>
                            <div style="color:#6EE7B7; font-weight:700; font-size:1.1rem;">{round((1 - co2_if_metro/max(future_total_co2,1))*100)}%</div>
                        </div>
                        <div>
                            <div style="color:#94A3B8; font-size:0.7rem;">Time Saved</div>
                            <div style="color:#6EE7B7; font-weight:700; font-size:1.1rem;">{travel_days * 12 * years * 0.4:.0f} Hours</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

            with st.spinner("Generating insight..."):
                future_summary = model.generate_content(f"""
Future Cost over {years} years: ₹{future_total_cost:,.0f}
Future CO2: {future_total_co2:.0f} kg
Explain long-term impact in 45 words. Be specific and actionable.
""")
            st.info(future_summary.text)

    with row3_c:
        with st.container(border=True):

            st.markdown("### 🎭 Your Commute Persona")

            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1E1040,#2D1B69); border:1px solid #4C1D95;
            border-radius:12px; padding:20px; text-align:center; margin-bottom:12px;">
                <div style="font-size:2.5rem; margin-bottom:8px;">🚴</div>
                <div style="color:#94A3B8; font-size:0.75rem; margin-bottom:4px;">You are</div>
                <div style="color:{persona_color}; font-size:1.1rem; font-weight:800; letter-spacing:-0.01em;">{persona}</div>
            </div>
            """, unsafe_allow_html=True)

            with st.spinner(""):
                persona_desc = get_persona_description(persona, monthly_cost, monthly_co2)

            st.markdown(f"""
            <div style="color:#CBD5E1; font-size:0.82rem; line-height:1.6; text-align:center; padding:0 4px;">
                {persona_desc}
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

            if st.button("🔄 Retake Assessment", use_container_width=True):
                st.session_state.analyze_clicked = False
                st.rerun()

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    # =====================================
    # ROW 4 — Weekly Plan | Roadmap
    # =====================================

    row4_a, row4_b = st.columns([2, 1.5])

    with row4_a:
        with st.container(border=True):

            st.markdown("### 🗓 Smart Weekly Mobility Plan")

            with st.spinner("Building your plan..."):
                weekly_plan = generate_weekly_plan(vehicle_type, daily_distance, priority)

            lines = weekly_plan.strip().split("\n")
            day_icons = {
                "Monday": "🟣", "Tuesday": "🔵",
                "Wednesday": "🟢", "Thursday": "🟡", "Friday": "🟠"
            }

            for line in lines:
                if ":" in line:
                    day, plan = line.split(":", 1)
                    icon = day_icons.get(day.strip(), "📅")
                    st.markdown(f"""
                    <div style="display:flex; align-items:flex-start; gap:10px; padding:8px 12px;
                    background:#141E33; border-radius:8px; margin-bottom:6px;">
                        <span style="font-size:1rem;">{icon}</span>
                        <div>
                            <span style="color:#A78BFA; font-weight:600; font-size:0.82rem;">{day.strip()}</span>
                            <span style="color:#CBD5E1; font-size:0.82rem;"> — {plan.strip()}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    with row4_b:
        with st.container(border=True):

            st.markdown("### 📈 Improvement Roadmap")

            with st.spinner(""):
                roadmap = generate_improvement_roadmap(mobility_score)

            steps = roadmap.strip().split("\n")
            step_colors = ["#8B5CF6", "#06B6D4", "#10B981"]
            step_num = 0

            for line in steps:
                if line.strip():
                    color = step_colors[min(step_num, 2)]
                    st.markdown(f"""
                    <div style="display:flex; gap:10px; padding:10px 12px;
                    background:{color}11; border-left:3px solid {color};
                    border-radius:0 8px 8px 0; margin-bottom:8px;">
                        <div style="color:{color}; font-size:0.82rem; line-height:1.5;">{line.strip()}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    step_num += 1

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    # =====================================
    # ROW 5 — Risk Alerts | Opportunities | ESG
    # =====================================

    row5_a, row5_b, row5_c = st.columns([1.5, 1.5, 2])

    with row5_a:
        with st.container(border=True):

            st.markdown("### 🚨 Mobility Risk Alerts")

            risks = []
            if monthly_cost > 5000:
                risks.append(("High commuting expenditure detected.", "#EF4444"))
            if monthly_co2 > 100:
                risks.append(("High carbon footprint exposure.", "#EF4444"))
            if fuel_price > 120:
                risks.append(("Fuel price volatility risk.", "#F59E0B"))

            if risks:
                for msg, color in risks:
                    st.markdown(f"""
                    <div style="display:flex; align-items:center; gap:8px; padding:10px 14px;
                    background:{color}11; border:1px solid {color}33; border-radius:8px; margin-bottom:6px;">
                        <span>⚠️</span>
                        <span style="color:{color}; font-size:0.82rem;">{msg}</span>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="display:flex; align-items:center; gap:8px; padding:10px 14px;
                background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.25);
                border-radius:8px;">
                    <span>✅</span>
                    <span style="color:#6EE7B7; font-size:0.82rem;">No major mobility risks detected.</span>
                </div>""", unsafe_allow_html=True)

    with row5_b:
        with st.container(border=True):

            st.markdown("### 🌱 Improvement Opportunities")

            opportunities = [
                "Use public transport 2 days/week.",
                "Reduce fuel usage by 20%.",
                "Improve ESG score by 10 points.",
                "Reduce annual CO₂ emissions."
            ]

            for opp in opportunities:
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:8px; padding:8px 12px;
                background:rgba(16,185,129,0.07); border:1px solid rgba(16,185,129,0.18);
                border-radius:8px; margin-bottom:6px;">
                    <span style="color:#10B981;">✓</span>
                    <span style="color:#6EE7B7; font-size:0.82rem;">{opp}</span>
                </div>""", unsafe_allow_html=True)

    with row5_c:
        with st.container(border=True):

            st.markdown("### 🌱 ESG Sustainability Score")

            esg_col1, esg_col2 = st.columns([1, 2])

            with esg_col1:
                esg_color = "#10B981" if esg_score >= 80 else "#F59E0B" if esg_score >= 60 else "#EF4444"
                st.markdown(f"""
                <div style="text-align:center; padding:12px;">
                    <div style="font-size:2.5rem; font-weight:800; color:{esg_color};">{esg_score}</div>
                    <div style="color:#64748B; font-size:0.72rem;">/100</div>
                    <div style="color:{esg_color}; font-size:0.75rem; margin-top:4px; font-weight:600;">ESG Score</div>
                </div>
                """, unsafe_allow_html=True)

            with esg_col2:
                st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
                st.progress(esg_score / 100)

                breakdown_items = [
                    ("🌿 Sustainability", round(sustainability_score * 0.6), "#10B981"),
                    ("❤️ Health", round(health_score * 0.2), "#F472B6"),
                    ("💰 Cost", round(cost_score * 0.2), "#60A5FA"),
                ]

                for label, val, color in breakdown_items:
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center;
                    padding:3px 0; font-size:0.75rem;">
                        <span style="color:#94A3B8;">{label}</span>
                        <span style="color:{color}; font-weight:600;">{val}</span>
                    </div>""", unsafe_allow_html=True)

                if esg_score >= 80:
                    st.success("Excellent sustainability profile.")
                elif esg_score >= 60:
                    st.warning("Moderate sustainability profile.")
                else:
                    st.error("Significant improvement required.")

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    # =====================================
    # ROW 6 — Quick Actions
    # =====================================

    st.markdown("""
    <div style="background:#141E33; border:1px solid #1E293B; border-radius:12px;
    padding:14px 20px; margin-bottom:16px;">
        <span style="color:#94A3B8; font-size:0.75rem; text-transform:uppercase;
        letter-spacing:0.08em; font-weight:600;">⚡ Quick Actions</span>
    </div>
    """, unsafe_allow_html=True)

    qa1, qa2, qa3, qa4 = st.columns(4)

    with qa1:
        if st.button("📄 Generate Mobility Report", use_container_width=True):
            st.info("Report generation coming soon!")

    with qa2:
        if st.button("📅 Plan My Week", use_container_width=True):
            st.info("Week planning coming soon!")

    with qa3:
        if st.button("📍 Find Nearby Options", use_container_width=True):
            st.info("Nearby options coming soon!")

    with qa4:
        if st.button("🚗 Compare Vehicles", use_container_width=True):
            st.info("Vehicle comparison coming soon!")

    st.markdown("---")

# =====================================
# AI MOBILITY COACH
# =====================================

with st.container(border=True):

    st.markdown("### 🤖 Ask AI Mobility Coach")
    st.caption("Get personalized advice on your commute, fuel cost, ESG score or sustainability.")

    coach_col1, coach_col2 = st.columns([4, 1])

    with coach_col1:
        user_question = st.text_input(
            "Your question",
            placeholder="e.g. How can I reduce my monthly commute cost by 30%?",
            label_visibility="collapsed"
        )

    with coach_col2:
        ask_btn = st.button("💬 Get Advice", use_container_width=True)

    if ask_btn and user_question:

        if st.session_state.analyze_clicked:
            ctx = f"""
Vehicle Type: {vehicle_type}
Daily Distance: {daily_distance} km
Monthly Cost: ₹{monthly_cost:,.0f}
Monthly CO2: {monthly_co2:.1f} kg
Mobility Score: {mobility_score}
ESG Score: {esg_score}
Priority: {priority}
"""
        else:
            ctx = "User has not run analysis yet."

        prompt = f"""
You are an AI Mobility Sustainability Advisor.

User Profile:
{ctx}

User Question:
{user_question}

Provide a practical, specific answer in under 120 words.
"""
        with st.spinner("Thinking..."):
            response = model.generate_content(prompt)

        st.markdown(f"""
        <div style="background:rgba(99,102,241,0.08); border:1px solid rgba(99,102,241,0.25);
        border-radius:10px; padding:16px; margin-top:8px;">
            <div style="color:#818CF8; font-weight:700; font-size:0.8rem; margin-bottom:6px;">🤖 AI Coach Response</div>
            <div style="color:#E2E8F0; font-size:0.88rem; line-height:1.7;">{response.text}</div>
        </div>
        """, unsafe_allow_html=True)

    elif ask_btn and not user_question:
        st.warning("Please type a question first.")