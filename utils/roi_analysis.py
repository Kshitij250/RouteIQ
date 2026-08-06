"""
Optimization potential analysis.

Two modes, both "within-fleet benchmarking" (compare each shipment
against the best vehicle class already present in this fleet's data):

1. Tonne-km mode (preferred): used when cargo weight is available.
   Uses GLEC v3.2 tonne-km factors (Tier 2/3).
2. Distance-only mode (fallback): used when no weight column exists.
   Uses the Tier 4 per-km proxy factors instead. Less precise (ignores
   load), but still a real, traceable within-fleet comparison - NOT
   an external or invented benchmark.

Explicitly NOT claimed: mode-shift savings (e.g. road->rail), since that
requires route/lane feasibility data this dataset doesn't carry.
"""

import pandas as pd
from utils.emission_factors import TONNE_KM_FACTORS, DISTANCE_ONLY_FALLBACK, classify_vehicle


def calculate_optimization_potential(df: pd.DataFrame, vehicle_col: str,
                                      distance_col: str, weight_col: str = None,
                                      carbon_price: float = 80) -> dict:
    df = df.copy()
    df["_vclass"] = df[vehicle_col].apply(classify_vehicle)
    classes_in_use = df["_vclass"].unique().tolist()

    has_weight = weight_col and weight_col in df.columns and df[weight_col].notna().any()

    if has_weight:
        weight = pd.to_numeric(df[weight_col], errors="coerce").fillna(0)
        best_class = min(classes_in_use, key=lambda c: TONNE_KM_FACTORS[c]["factor"])
        best_factor = TONNE_KM_FACTORS[best_class]["factor"]
        df["_best_case_kg"] = weight * df[distance_col] * best_factor
        method = "tonne-km (GLEC v3.2)"
    else:
        best_class = min(classes_in_use, key=lambda c: DISTANCE_ONLY_FALLBACK[c])
        best_factor = DISTANCE_ONLY_FALLBACK[best_class]
        df["_best_case_kg"] = df[distance_col] * best_factor
        method = "distance-only proxy (no cargo weight in dataset - Tier 4)"

    df["_actual_kg"] = df["emission_kgCO2"]
    df["_potential_savings_kg"] = (df["_actual_kg"] - df["_best_case_kg"]).clip(lower=0)

    total_potential_kg = df["_potential_savings_kg"].sum()
    total_potential_cost = total_potential_kg * carbon_price

    by_class = (
        df[df["_vclass"] != best_class]
        .groupby("_vclass")["_potential_savings_kg"]
        .sum()
        .sort_values(ascending=False)
    )

    return {
        "available": True,
        "method": method,
        "best_class": best_class,
        "best_factor": best_factor,
        "total_potential_kg": total_potential_kg,
        "total_potential_cost": total_potential_cost,
        "pct_of_total_emissions": (total_potential_kg / df["_actual_kg"].sum() * 100)
                                    if df["_actual_kg"].sum() > 0 else 0,
        "by_class": by_class,
    }