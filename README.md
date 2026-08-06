# 🚚 RouteIQ
### AI-Powered ESG Supply Chain Intelligence & Operational Excellence Platform

<p align="center">

AI • ESG • Logistics • Lean Six Sigma • Route Optimization • Business Intelligence

</p>

---

## 📌 Overview

RouteIQ is an AI-powered logistics intelligence platform that helps organizations optimize transportation operations, improve ESG performance, reduce carbon emissions, and identify operational bottlenecks using Lean Six Sigma methodologies.

The platform combines:

- 🌱 ESG Analytics
- 🚛 Intelligent Route Optimization
- 📊 Operational Excellence Analytics
- 🤖 AI-Powered Root Cause Analysis
- ♻️ Sustainability Intelligence
- 🚗 Mobility Recommendations

into a single interactive analytics platform built with Streamlit.

---

# ✨ Core Modules

## 🌱 ESG Analytics

Analyze logistics sustainability using internationally accepted carbon estimation methodologies.

### Features

- Carbon Emission Analysis
- ESG Performance Score
- Carbon Cost Estimation
- Sustainability KPIs
- Environmental Impact Dashboard
- Emission Trends
- Vehicle-wise Carbon Analysis
- Carbon Optimization Potential

---

## 🚛 Route Optimization

An intelligent multimodal transportation planning engine capable of finding the optimal logistics route based on business objectives.

### Optimization Strategies

- Cheapest Route
- Fastest Route
- Greenest Route
- Balanced Route

### Supported Transport Modes

- Road
- Rail
- Sea
- Air

### Dynamic Features

Unlike traditional static route planners, RouteIQ integrates real-world data.

✔ Live Road Distances (OSRM)

✔ Weather-aware ETA Adjustment

✔ Dynamic Fuel Cost Multiplier

✔ Ocean Route Approximation

✔ Port Waiting Time Estimation

✔ Corridor Disruption Simulation

✔ Automatic Road Network Expansion

---

## 📊 Operational Excellence (NEW)

A complete Lean Six Sigma analytics engine for logistics operations.

The Operational Excellence module transforms logistics data into executive-level operational insights.

### Executive KPI Dashboard

The dashboard automatically calculates KPIs including:

- On-Time Delivery
- Turnaround Time (TAT)
- Cost per Shipment
- Fleet Utilization
- Sigma Level
- DPMO
- Vehicle Idle Time
- Warehouse Throughput
- Delay Cost
- Carbon / ESG Score

---

### Root Cause Diagnostics

The platform automatically identifies operational bottlenecks using multiple Lean Six Sigma techniques.

#### 📈 Pareto Analysis

- Top delay contributors
- Cumulative impact
- 80/20 visualization

---

#### 🐟 Fishbone Diagram

Automatically categorizes delays into:

- People
- Process
- Machine
- Material
- Environment
- Management

---

#### ❓ 5 Whys Analysis

Automatically drills down from the primary issue to the root operational cause.

Example:

```
Weather

↓

Dispatch planning

↓

No weather contingency

↓

No fallback strategy

↓

Root Cause
```

---

#### 🔄 DMAIC Framework

Automatically generates:

- Define
- Measure
- Analyze
- Improve
- Control

recommendations for the selected operational issue.

---

#### 💡 AI Recommendations

Business recommendations include:

- Expected delay reduction
- Operational improvements
- ESG impact
- Business impact
- Priority actions

---

## 🤖 AI Operational Intelligence

Operational Excellence is enhanced using **Groq LLMs**.

The AI engine automatically generates:

- Executive summaries
- Fishbone explanations
- 5 Whys
- DMAIC recommendations
- Business improvement plans
- Root cause narratives

while maintaining transparent confidence levels and graceful fallbacks when AI services are unavailable.

---

## 🚗 Mobility Assistant

Personal sustainability advisor providing:

- Fuel-efficient travel suggestions
- Sustainable commuting plans
- Carbon footprint estimation
- Vehicle utilization guidance
- Green mobility recommendations

---

# 🧠 Intelligent Data Validation

RouteIQ automatically validates uploaded datasets before analysis.

The validation engine supports all analytics modules simultaneously.

It detects:

- Missing columns
- Incorrect datatypes
- Low-quality data
- Missing KPI fields
- Proxy estimation opportunities

Each field is categorized as:

- ✅ Present
- ⚠ Partial
- ❌ Missing
- 📌 Estimated

ensuring complete transparency throughout the analytics pipeline.

---

# 🌍 ESG Methodology

Carbon emissions are calculated using internationally accepted methodologies.

### Standards

- ISO 14083:2023
- GLEC Framework v3.2
- Well-to-Wheel (WTW)
- AR6 GWP-100

The platform also supports multiple confidence tiers depending on available shipment information.

---

# 🤖 AI + Data Transparency

RouteIQ follows a transparent analytics philosophy.

Every KPI and recommendation indicates how it was generated.

### Tier 1

Real observed logistics data

### Tier 2

Partially inferred operational signals

### Tier 3

Illustrative industry benchmark

Users always know whether an insight comes from actual data or estimated values.

---

# 📊 Interactive Dashboards

The platform includes:

- Executive KPI Cards
- ESG Dashboard
- Carbon Analytics
- Cost Analytics
- Delay Analytics
- Fleet Analytics
- Interactive Plotly Charts
- Route Maps
- Operational Intelligence Dashboard

---

# ⚙ Technology Stack

| Category | Technologies |
|------------|----------------------------|
| Language | Python |
| Dashboard | Streamlit |
| Data Processing | Pandas, NumPy |
| Visualization | Plotly |
| AI | Groq API, Google Gemini |
| Optimization | NetworkX |
| Mapping | Folium |
| Routing | OSRM |
| Weather | Open-Meteo |
| Marine Weather | Stormglass |
| Carbon Analytics | GLEC Framework |
| Data Source | Excel / CSV |
| Version Control | Git & GitHub |

---

# 📂 Project Structure

```
RouteIQ/

│

├── pages/

│ ├── 1_ESG_Analysis.py

│ ├── 2_Route_Optimization.py

│ ├── 3_Operational_Excellence.py

│ └── 4_Mobility_Assistant.py

│

├── utils/

│ ├── route_engine.py

│ ├── routing_api.py

│ ├── operational_excellence.py

│ ├── groq_ai.py

│ ├── emission_factors.py

│ ├── data_validation.py

│ ├── roi_analysis.py

│ └── sidebar.py

│

├── upload.py

├── requirements.txt

└── README.md

```

---

# 🚀 Getting Started

## Clone Repository

```bash
git clone https://github.com/Kshitij250/RouteIQ.git

cd RouteIQ
```

---

## Create Virtual Environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run Application

```bash
streamlit run upload.py
```

---

# 🔄 Application Workflow

```
Upload Dataset

↓

Automatic Data Validation

↓

ESG Analytics

↓

Route Optimization

↓

Operational Excellence

↓

AI Root Cause Analysis

↓

Mobility Assistant

↓

Executive Report
```

---

# 📈 Business Applications

- ESG Reporting
- Carbon Accounting
- Logistics Optimization
- Fleet Management
- Lean Six Sigma
- Operational Excellence
- Supply Chain Analytics
- Sustainability Consulting
- Transportation Planning
- Executive Decision Support

---

# 🔮 Future Roadmap

- FastAPI Backend
- PostgreSQL Integration
- Authentication & RBAC
- Cloud Deployment (Azure / AWS)
- Docker Support
- CI/CD Pipelines
- Predictive Delay Forecasting
- IoT Integration
- GPS Tracking
- Real-Time Fleet Monitoring
- Digital Twin Simulation
- SAP TM Integration

---

# 📸 Screenshots

## ESG Dashboard

<img src="screenshots/esg_dashboard.png" width="100%">

---

## Route Optimization

<img src="screenshots/route_optimization.png" width="100%">

---

## Operational Excellence

<img src="screenshots/operational_excellence.png" width="100%">

---

## Fishbone Analysis

<img src="screenshots/fishbone.png" width="100%">

---

## 5 Whys Analysis

<img src="screenshots/5whys.png" width="100%">

---

# 🎓 Learning Outcomes

This project demonstrates practical experience in:

- Supply Chain Analytics
- ESG Reporting
- Lean Six Sigma
- Root Cause Analysis
- Operational Excellence
- Artificial Intelligence Integration
- Business Intelligence
- Carbon Accounting
- Route Optimization
- Dashboard Development
- Data Analytics
- Python Development
- Interactive Visualization

---

# 👨‍💻 Author

**Kshitij Singh**

B.Tech — Electronics & Communication Engineering

Birla Institute of Technology, Mesra

🔗 GitHub: https://github.com/Kshitij250

---

⭐ If you found this project useful, consider giving it a star!
