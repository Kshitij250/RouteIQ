"""
Operational Excellence Engine
==============================
Lean Six Sigma analytics layer for RouteIQ: KPI calculation, Root Cause
Analysis (Pareto / Fishbone / 5 Whys), DMAIC, and business-impact
estimation — computed from whatever columns are actually present in the
uploaded dataset.

METHODOLOGY / HONESTY NOTE
---------------------------
Most logistics datasets do NOT ship with a clean "delay reason" column.
Rather than fabricate root causes, this engine is tiered, same spirit as
utils/emission_factors.py:

  Tier 1 - Real data available (status/delay-reason/timestamp columns)
           -> causes and OTD/TAT computed directly from the data.
  Tier 2 - Partial signals available (weather/traffic/warehouse/driver
           columns exist but no explicit reason field)
           -> causes attributed via rule-based matching against those
              columns for delayed shipments only.
  Tier 3 - No usable signal at all
           -> falls back to a labeled, illustrative industry-typical
              delay-cause split, and every KPI/chart that used it is
              flagged "ESTIMATED" in the UI so it's never mistaken for
              a real finding.

Every function returns not just numbers but a `method` / `tier` string
so the UI can show the user exactly how each figure was derived.
"""

import math
import numpy as np
import pandas as pd

from utils.data_validation import detect_column
from utils.emission_factors import calculate_emissions_kg, extract_capacity_tonnes, classify_vehicle
from utils.groq_ai import get_ai_analysis, get_ai_status, FISHBONE_BUCKETS

CARBON_PRICE_DEFAULT = 80  # INR / kg CO2, kept consistent with 1_ESG_Analysis.py

# ─────────────────────────────────────────────
# CAUSE TAXONOMY
# ─────────────────────────────────────────────
DELAY_CAUSE_KEYWORDS = {
    "Warehouse Congestion": ["warehouse", "congestion", "dock", "loading", "dwell", "slot"],
    "Route Planning":       ["route", "planning", "detour", "reroute", "sequence", "path"],
    "Vehicle Breakdown":    ["breakdown", "mechanical", "engine", "tyre", "tire", "maintenance", "repair"],
    "Driver Issues":        ["driver", "fatigue", "absent", "late start", "operator"],
    "Weather":              ["weather", "rain", "storm", "fog", "flood", "cyclone", "snow"],
    "Traffic":              ["traffic", "jam", "road block", "accident"],
}

# Used ONLY as a last-resort, clearly-labeled illustrative split when the
# dataset contains no delay-reason signal whatsoever. Values are a common
# industry rule-of-thumb order of magnitude, NOT derived from this data.
FALLBACK_DISTRIBUTION = {
    "Warehouse Congestion": 0.42,
    "Route Planning":       0.28,
    "Vehicle Breakdown":    0.14,
    "Traffic":              0.09,
    "Driver Issues":        0.05,
    "Weather":              0.02,
}

FISHBONE_MAP = {
    "Warehouse Congestion": "Process",
    "Route Planning":       "Process",
    "Vehicle Breakdown":    "Machine",
    "Driver Issues":        "People",
    "Weather":              "Environment",
    "Traffic":              "Environment",
    "Others":               "Management",
}

FIVE_WHYS_TEMPLATES = {
    "Warehouse Congestion": [
        "Pick and dispatch volumes peak sharply during specific hours.",
        "Too many orders are released for dispatch at the same time.",
        "There is no staggered scheduling for order release.",
        "Dispatch windows are not standardized across shifts.",
        "No formal capacity-planning or slotting process exists for the warehouse.",
    ],
    "Route Planning": [
        "Shipments frequently take longer routes than necessary.",
        "Route sequencing is done manually / on fixed historical lanes.",
        "Real-time traffic and distance data isn't factored into route choice.",
        "No systematic route-optimization step exists before dispatch.",
        "The planning process lacks a data-driven routing tool or policy.",
    ],
    "Vehicle Breakdown": [
        "A meaningful share of delayed shipments involve vehicle issues.",
        "Vehicles are dispatched without a consistent pre-trip check.",
        "Maintenance is largely reactive rather than scheduled.",
        "There is no preventive maintenance calendar tied to vehicle usage.",
        "Fleet maintenance is not owned by a dedicated process/role.",
    ],
    "Driver Issues": [
        "Some delays trace back to driver availability or readiness.",
        "Shift handovers and driver allocation are not tightly scheduled.",
        "There's limited visibility into driver hours and fatigue risk.",
        "No standard driver-readiness checklist exists before dispatch.",
        "Workforce planning is not integrated with the dispatch system.",
    ],
    "Traffic": [
        "Delays cluster on specific high-traffic corridors/time windows.",
        "Dispatch times don't account for known peak-traffic windows.",
        "Live traffic conditions aren't used to adjust ETAs proactively.",
        "There's no dynamic re-routing when congestion is detected.",
        "The routing process doesn't integrate a live traffic feed.",
    ],
    "Weather": [
        "A share of delays coincide with adverse weather conditions.",
        "Dispatch decisions don't currently factor in weather forecasts.",
        "There's no weather-contingency buffer built into ETAs.",
        "Alternate-mode fallback plans aren't defined for bad weather.",
        "Weather risk isn't a formal input to the planning process.",
    ],
    "Others": [
        "Delay causes are spread across several minor, low-frequency factors.",
        "These factors are too fragmented to attribute to one system issue.",
        "No single process currently tracks these long-tail causes.",
        "Root-cause data for these cases isn't captured in detail today.",
        "A structured delay-reason log would be needed to diagnose further.",
    ],
}

ROOT_CAUSE_STATEMENT = {
    "Warehouse Congestion": "Lack of dispatch-capacity planning and order-release scheduling.",
    "Route Planning":       "Absence of a systematic, data-driven route-optimization process.",
    "Vehicle Breakdown":    "Reactive (not preventive) fleet maintenance practice.",
    "Driver Issues":        "Workforce/dispatch scheduling not integrated with driver availability.",
    "Traffic":              "No live-traffic input into dispatch timing or routing decisions.",
    "Weather":              "No weather-contingency buffer in planning or dispatch.",
    "Others":               "Fragmented long-tail causes not tracked at sufficient granularity.",
}

RECOMMENDATION_LIBRARY = {
    "Warehouse Congestion": {
        "text": "Stagger order-release / dispatch windows and optimize warehouse slotting for fast-moving SKUs.",
        "delay_reduction_pct": 0.18,
    },
    "Route Planning": {
        "text": "Adopt systematic route optimization (already available in the Route Optimization module) for all dispatches.",
        "delay_reduction_pct": 0.15,
    },
    "Vehicle Breakdown": {
        "text": "Move to a preventive maintenance schedule tied to vehicle usage/mileage instead of reactive repair.",
        "delay_reduction_pct": 0.10,
    },
    "Driver Issues": {
        "text": "Introduce a driver-readiness checklist and integrate shift/fatigue tracking into dispatch planning.",
        "delay_reduction_pct": 0.07,
    },
    "Traffic": {
        "text": "Integrate live traffic feeds into dispatch timing and enable dynamic re-routing.",
        "delay_reduction_pct": 0.08,
    },
    "Weather": {
        "text": "Build a weather-contingency buffer into ETAs and define alternate-mode fallback plans.",
        "delay_reduction_pct": 0.05,
    },
    "Others": {
        "text": "Instrument a structured delay-reason log to enable future root-cause tracking.",
        "delay_reduction_pct": 0.03,
    },
}


# ─────────────────────────────────────────────
# STEP 1 — COLUMN DETECTION
# ─────────────────────────────────────────────
def detect_opex_columns(df: pd.DataFrame) -> dict:
    cols = df.columns
    return {
        "vehicle":      detect_column(["vehicletype", "vehicle_type", "truck", "lorry", "transport", "vehicle"], cols),
        "distance":     detect_column(["distance", "km", "kilometer"], cols),
        "weight":       detect_column(["weight", "cargo", "load", "tonnage"], cols),
        "capacity":     detect_column(["capacity", "max_load", "payload"], cols),
        "cost":         detect_column(["cost", "price", "freight", "charge"], cols),
        "date":         detect_column(["date", "datetime", "shipment_date", "created", "order_date"], cols),
        "status":       detect_column(["status", "delivery_status", "ontime", "on_time"], cols),
        "delay_flag":   detect_column(["delay", "late", "isdelayed", "is_delayed"], cols),
        "planned_time": detect_column(["promised", "planned", "expected", "scheduled", "eta"], cols),
        "actual_time":  detect_column(["actual", "delivered_time", "arrival", "ata"], cols),
        "warehouse":    detect_column(["warehouse", "hub", "depot", "facility", "dc_"], cols),
        "driver":       detect_column(["driver", "operator"], cols),
        "weather":      detect_column(["weather", "rain", "storm"], cols),
        "traffic":      detect_column(["traffic", "congestion"], cols),
        "idle":         detect_column(["idle", "waiting", "dwell"], cols),
        "reason":       detect_column(["reason", "cause", "delay_reason", "root_cause"], cols),
    }


# ─────────────────────────────────────────────
# STEP 2 — DELAY DETECTION (tiered)
# ─────────────────────────────────────────────
def compute_delay_flags(df: pd.DataFrame, cols: dict):
    df = df.copy()
    df["_tat_hours"] = np.nan

    # ── TAT is independent of *how* we detect delays ─────────────────
    # Previously this was only computed inside the "no status/flag
    # column" branch below, so a dataset with BOTH a status column AND
    # planned/actual timestamps (a very normal case — see the sample
    # test dataset) would use the status column for delay detection
    # and silently never compute TAT at all, showing "N/A" despite the
    # timestamps being right there. Compute it up front whenever the
    # columns exist, independent of which tier below decides delays.
    if cols["planned_time"] and cols["actual_time"]:
        planned = pd.to_datetime(df[cols["planned_time"]], errors="coerce")
        actual  = pd.to_datetime(df[cols["actual_time"]], errors="coerce")
        df["_tat_hours"] = (actual - planned).dt.total_seconds() / 3600

    if cols["status"]:
        s = df[cols["status"]].astype(str).str.lower()
        df["_is_delayed"] = s.str.contains("delay|late|overdue|failed", regex=True, na=False)
        method = f"Tier 1 — delivery status column '{cols['status']}'"
        tier = 1

    elif cols["delay_flag"]:
        col = df[cols["delay_flag"]]
        if col.dtype == bool:
            df["_is_delayed"] = col
        else:
            df["_is_delayed"] = pd.to_numeric(col, errors="coerce").fillna(0) > 0
        method = f"Tier 1 — delay flag column '{cols['delay_flag']}'"
        tier = 1

    elif cols["planned_time"] and cols["actual_time"]:
        # TAT already computed above; just derive delay from it here.
        df["_is_delayed"] = df["_tat_hours"] > 0
        method = f"Tier 1 — planned vs. actual timestamps ('{cols['planned_time']}' / '{cols['actual_time']}')"
        tier = 1

    elif cols["distance"] and cols["cost"]:
        dist = pd.to_numeric(df[cols["distance"]], errors="coerce")
        cost = pd.to_numeric(df[cols["cost"]], errors="coerce")
        cpk  = cost / dist.replace(0, np.nan)
        threshold = cpk.quantile(0.75)
        df["_is_delayed"] = cpk > threshold
        method = ("Tier 3 — PROXY: no status/timestamp columns found, so the top quartile of "
                   "cost-per-km is used as an illustrative stand-in for 'at risk' shipments. "
                   "Add a delivery-status or timestamp column for a real OTD figure.")
        tier = 3

    else:
        df["_is_delayed"] = False
        method = ("Tier 3 — INSUFFICIENT DATA: no status, timestamp, distance, or cost columns "
                   "found to infer delays. All delay-based KPIs below are unavailable.")
        tier = 3

    return df, method, tier


# ─────────────────────────────────────────────
# STEP 3 — EXECUTIVE KPI ENGINE
# ─────────────────────────────────────────────
def compute_kpis(df: pd.DataFrame, cols: dict, carbon_price: float = CARBON_PRICE_DEFAULT) -> dict:
    df, delay_method, delay_tier = compute_delay_flags(df, cols)
    n = len(df)
    n_delayed = int(df["_is_delayed"].sum())
    otd_pct = round((1 - n_delayed / n) * 100, 1) if n else 0.0

    # TAT
    if df["_tat_hours"].notna().any():
        tat_hours = round(df.loc[df["_tat_hours"] > 0, "_tat_hours"].mean(), 1)
        tat_available = True
    else:
        tat_hours = None
        tat_available = False

    # Cost per shipment
    if cols["cost"]:
        cost = pd.to_numeric(df[cols["cost"]], errors="coerce")
        cost_per_shipment = round(cost.mean(), 0)
        total_cost = round(cost.sum(), 0)
        cost_available = True
    else:
        cost_per_shipment = None
        total_cost = None
        cost_available = False

    # Fleet utilization (weight / capacity)
    if cols["weight"] and cols["capacity"]:
        w = pd.to_numeric(df[cols["weight"]], errors="coerce")
        c = pd.to_numeric(df[cols["capacity"]], errors="coerce").replace(0, np.nan)
        util_pct = round((w / c).clip(upper=1).mean() * 100, 1)
        util_available = True
    elif cols["vehicle"] and cols["weight"]:
        # proxy: extract stated capacity from vehicle text, same trick as ESG page
        extracted_cap = df[cols["vehicle"]].astype(str).apply(extract_capacity_tonnes)
        w = pd.to_numeric(df[cols["weight"]], errors="coerce")
        valid = extracted_cap.notna() & (extracted_cap > 0)
        if valid.any():
            util_pct = round((w[valid] / extracted_cap[valid]).clip(upper=1).mean() * 100, 1)
            util_available = True
        else:
            util_pct = None
            util_available = False
    else:
        util_pct = None
        util_available = False

    # Vehicle idle time
    if cols["idle"]:
        idle_hours = round(pd.to_numeric(df[cols["idle"]], errors="coerce").mean(), 1)
        idle_available = True
    else:
        idle_hours = None
        idle_available = False

    # Warehouse throughput (shipments/day)
    if cols["date"]:
        d = pd.to_datetime(df[cols["date"]], errors="coerce")
        n_days = max((d.max() - d.min()).days, 1) if d.notna().any() else 1
        throughput = round(n / n_days, 1)
        throughput_available = True
    else:
        throughput = None
        throughput_available = False

    # Emissions / ESG score (reuse the ESG page's own methodology)
    carbon_available = bool(cols["vehicle"] and cols["distance"])
    total_emissions = None
    esg_score = None
    if carbon_available:
        v = df[cols["vehicle"]].astype(str).str.upper().str.strip()
        dist = pd.to_numeric(df[cols["distance"]], errors="coerce").fillna(0)
        weight_col_for_calc = cols["weight"]
        if weight_col_for_calc:
            weight = pd.to_numeric(df[cols["weight"]], errors="coerce")
        else:
            weight = v.apply(extract_capacity_tonnes)

        def _row_em(i):
            w = weight.iloc[i] if pd.notna(weight.iloc[i]) else None
            return calculate_emissions_kg(v.iloc[i], dist.iloc[i], w)["emissions_kg"]

        emissions = pd.Series([_row_em(i) for i in range(n)])
        total_emissions = round(emissions.sum(), 0)
        max_em = emissions.max()
        esg_scores = (100 - (emissions / max_em) * 100) if max_em > 0 else pd.Series([100] * n)
        esg_score = round(esg_scores.mean(), 1)

    # Delay cost impact
    if cost_available:
        avg_cost = cost.mean()
        delay_cost = round(n_delayed * avg_cost, 0)
        delay_cost_available = True
    elif carbon_available:
        # fallback proxy: delayed shipments cost proxy via carbon cost so the
        # figure is never fabricated from nothing
        delay_cost = round(n_delayed * (total_emissions / n if n else 0) * carbon_price, 0) if total_emissions else None
        delay_cost_available = delay_cost is not None
    else:
        delay_cost = None
        delay_cost_available = False

    return {
        "df": df,
        "n_shipments": n,
        "n_delayed": n_delayed,
        "otd_pct": otd_pct,
        "delay_method": delay_method,
        "delay_tier": delay_tier,
        "tat_hours": tat_hours, "tat_available": tat_available,
        "cost_per_shipment": cost_per_shipment, "total_cost": total_cost, "cost_available": cost_available,
        "util_pct": util_pct, "util_available": util_available,
        "idle_hours": idle_hours, "idle_available": idle_available,
        "throughput": throughput, "throughput_available": throughput_available,
        "total_emissions_kg": total_emissions, "esg_score": esg_score, "carbon_available": carbon_available,
        "delay_cost": delay_cost, "delay_cost_available": delay_cost_available,
        "carbon_price": carbon_price,
    }


# ─────────────────────────────────────────────
# STEP 4 — SIGMA LEVEL (DPMO -> approx sigma, Bothe approximation)
# ─────────────────────────────────────────────
def dpmo_to_sigma(dpmo: float) -> float:
    dpmo = max(min(dpmo, 999999), 1)
    try:
        z = 0.8406 + math.sqrt(max(29.37 - 2.221 * math.log(dpmo), 0))
    except ValueError:
        z = 0.0
    return round(min(z, 6.0), 2)


# ─────────────────────────────────────────────
# STEP 5 — ROOT CAUSE / PARETO ANALYSIS
# ─────────────────────────────────────────────
def root_cause_analysis(df: pd.DataFrame, cols: dict) -> dict:
    delayed = df[df["_is_delayed"]] if "_is_delayed" in df.columns else df.iloc[0:0]
    n_delayed = len(delayed)

    causes = {}
    if n_delayed == 0:
        method = "No delayed shipments detected (or delay signal unavailable)."
        tier = 0

    elif cols["reason"]:
        raw = delayed[cols["reason"]].astype(str).str.lower()
        for cause, kws in DELAY_CAUSE_KEYWORDS.items():
            causes[cause] = int(raw.apply(lambda x: any(k in x for k in kws)).sum())
        uncategorized = n_delayed - sum(causes.values())
        if uncategorized > 0:
            causes["Others"] = uncategorized
        method = f"Tier 1 — classified directly from '{cols['reason']}' column text."
        tier = 1

    elif any(cols[k] for k in ["warehouse", "driver", "weather", "traffic"]):
        # Tier 2: attribute using whichever contextual columns exist, applied
        # only to the actually-delayed subset.
        remaining = delayed.copy()
        if cols["weather"]:
            flag = remaining[cols["weather"]].astype(str).str.lower().str.contains(
                "rain|storm|fog|flood|snow|bad", na=False)
            causes["Weather"] = int(flag.sum())
            remaining = remaining[~flag]
        if cols["traffic"]:
            flag = remaining[cols["traffic"]].astype(str).str.lower().str.contains(
                "high|heavy|jam|severe", na=False)
            causes["Traffic"] = int(flag.sum())
            remaining = remaining[~flag]
        if cols["warehouse"] and cols["idle"]:
            idle_vals = pd.to_numeric(remaining[cols["idle"]], errors="coerce")
            flag = idle_vals > idle_vals.median() if idle_vals.notna().any() else pd.Series(False, index=remaining.index)
            causes["Warehouse Congestion"] = int(flag.sum())
            remaining = remaining[~flag]
        leftover = len(remaining)
        if leftover > 0:
            # split leftover across Route Planning / Vehicle Breakdown / Driver
            # proportionally to the illustrative baseline, since no direct
            # signal distinguishes them
            base = {"Route Planning": 0.5, "Vehicle Breakdown": 0.3, "Driver Issues": 0.2}
            for c, pct in base.items():
                causes[c] = causes.get(c, 0) + round(leftover * pct)
        method = "Tier 2 — attributed using available context columns (weather/traffic/warehouse) plus a proportional split for the remainder."
        tier = 2

    else:
        for cause, pct in FALLBACK_DISTRIBUTION.items():
            causes[cause] = round(n_delayed * pct)
        method = ("Tier 3 — ESTIMATED: dataset has no delay-reason, weather, traffic, or warehouse "
                   "signal, so this uses a labeled illustrative industry-typical split. Not a real finding "
                   "— add a delay-reason column for accurate RCA.")
        tier = 3

    if not causes:
        pareto_df = pd.DataFrame(columns=["Cause", "Count", "Pct", "CumulativePct"])
    else:
        pareto_df = pd.DataFrame(sorted(causes.items(), key=lambda x: -x[1]), columns=["Cause", "Count"])
        total = pareto_df["Count"].sum()
        pareto_df["Pct"] = (pareto_df["Count"] / total * 100).round(1) if total else 0
        pareto_df["CumulativePct"] = pareto_df["Pct"].cumsum().round(1)

    top_cause = pareto_df.iloc[0]["Cause"] if len(pareto_df) else None

    return {
        "pareto_df": pareto_df,
        "method": method,
        "tier": tier,
        "n_delayed": n_delayed,
        "top_cause": top_cause,
    }


def fishbone_categories(pareto_df: pd.DataFrame, kpis: dict = None, rca: dict = None, cols: dict = None) -> dict:
    """Groups Pareto causes into the 6 Ishikawa buckets.

    If kpis/rca/cols are supplied, tries a Groq-assisted categorization first
    (useful because Tier 1 datasets can surface free-text cause labels that
    don't match the fixed keyword taxonomy at all). Falls back to the static
    FISHBONE_MAP for any cause the AI didn't confidently place, or entirely
    if the AI call isn't available.
    """
    buckets = {b: [] for b in FISHBONE_BUCKETS}

    ai_map = {}
    if kpis is not None and rca is not None:
        ai = get_ai_analysis(kpis, rca, cols or {})
        if ai:
            ai_map = ai.get("fishbone", {})

    for _, row in pareto_df.iterrows():
        cause = row["Cause"]
        bucket = ai_map.get(cause) or FISHBONE_MAP.get(cause, "Management")
        buckets[bucket].append(f"{cause} ({row['Pct']}%)")

    for k in buckets:
        if not buckets[k]:
            buckets[k].append("No significant contributing issues identified")
    return buckets


def five_whys(top_cause: str, kpis: dict = None, rca: dict = None, cols: dict = None) -> dict:
    if not top_cause:
        return {"whys": [], "root_cause": "Not enough delay data to run a 5 Whys investigation.", "source": "none"}

    if kpis is not None and rca is not None:
        ai = get_ai_analysis(kpis, rca, cols or {})
        if ai and ai.get("whys") and ai.get("root_cause"):
            whys = ai["whys"]
            # Pad to 5 with the static template's remaining steps if the model
            # returned fewer than 5 (validation only requires >= 3).
            if len(whys) < 5 and top_cause in FIVE_WHYS_TEMPLATES:
                whys = whys + FIVE_WHYS_TEMPLATES[top_cause][len(whys):5]
            return {"whys": whys, "root_cause": ai["root_cause"], "source": "ai"}

    if top_cause not in FIVE_WHYS_TEMPLATES:
        return {"whys": [], "root_cause": "Not enough delay data to run a 5 Whys investigation.", "source": "none"}
    return {
        "whys": FIVE_WHYS_TEMPLATES[top_cause],
        "root_cause": ROOT_CAUSE_STATEMENT.get(top_cause, "Root cause requires further investigation."),
        "source": "static",
    }


# ─────────────────────────────────────────────
# STEP 6 — DMAIC
# ─────────────────────────────────────────────
def build_dmaic(kpis: dict, rca: dict, cols: dict = None) -> list:
    top_cause = rca["top_cause"] or "delay drivers"
    otd = kpis["otd_pct"]

    tat_part = f"TAT {kpis['tat_hours']} hrs, " if kpis["tat_available"] else ""
    esg_part = (
        f"ESG score {kpis['esg_score']}/100"
        if kpis["carbon_available"]
        else "ESG score unavailable"
    )
    measure_result = f"Baseline established: OTD {otd}%, {tat_part}{esg_part}."

    ai = get_ai_analysis(kpis, rca, cols or {}) if rca.get("top_cause") else None
    if ai and ai.get("improve") and ai.get("control"):
        improve_result = ai["improve"]
        control_result = ai["control"]
    else:
        improve_result = RECOMMENDATION_LIBRARY.get(top_cause, {}).get(
            "text", "Define and roll out improvement actions.")
        control_result = "Track OTD, TAT, and delay-cause mix weekly; alert if OTD drops below target."

    return [
        {
            "phase": "Define", "status": "Completed",
            "desc": "Define the business problem from the uploaded dataset.",
            "result": f"On-Time Delivery is {otd}% with {kpis['n_delayed']} delayed shipment(s) out of {kpis['n_shipments']}.",
        },
        {
            "phase": "Measure", "status": "Completed",
            "desc": "Measure current KPI baseline.",
            "result": measure_result,
        },
        {
            "phase": "Analyze", "status": "Completed",
            "desc": "Identify root causes via Pareto, Fishbone, and 5 Whys.",
            "result": f"Leading cause: {top_cause} ({rca['method'].split('—')[0].strip()}).",
        },
        {
            "phase": "Improve", "status": "In Progress",
            "desc": "Implement AI-generated operational improvements.",
            "result": improve_result,
        },
        {
            "phase": "Control", "status": "In Progress",
            "desc": "Monitor and sustain results.",
            "result": control_result,
        },
    ]


# ─────────────────────────────────────────────
# STEP 7 — RECOMMENDATIONS + BUSINESS IMPACT
# ─────────────────────────────────────────────
def build_recommendations(rca: dict, kpis: dict, top_n: int = 4) -> list:
    pareto_df = rca["pareto_df"]
    recs = []
    for _, row in pareto_df.head(top_n).iterrows():
        cause = row["Cause"]
        lib = RECOMMENDATION_LIBRARY.get(cause, RECOMMENDATION_LIBRARY["Others"])
        recs.append({
            "cause": cause,
            "text": lib["text"],
            "impact_pct": round(lib["delay_reduction_pct"] * row["Pct"], 1),  # share of total delay this could remove
        })
    return recs


def business_impact(kpis: dict, recs: list) -> dict:
    total_delay_reduction_pct = round(sum(r["impact_pct"] for r in recs), 1)
    total_delay_reduction_pct = min(total_delay_reduction_pct, 60.0)  # cap to a believable range

    if kpis["delay_cost_available"] and kpis["delay_cost"]:
        savings = round(kpis["delay_cost"] * (total_delay_reduction_pct / 100), 0)
    else:
        savings = None

    otd_improvement = round(total_delay_reduction_pct * 0.4, 1)  # conservative pass-through to OTD

    return {
        "delay_reduction_pct": total_delay_reduction_pct,
        "potential_savings": savings,
        "otd_improvement_pct": otd_improvement,
        "carbon_reduction_pct": round(total_delay_reduction_pct * 0.25, 1) if kpis["carbon_available"] else None,
    }