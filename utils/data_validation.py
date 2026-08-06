"""
data_validation.py — RouteIQ Aggressive Data Validation Engine
===============================================================

Validates every uploaded dataset against ALL KPI domains consumed by the
four analytics modules:
  1. ESG Analysis            (vehicle, distance, weight, cost, date, status)
  2. Route Optimization      (city_coordinates sheet, transport corridors)
  3. Operational Excellence  (status/delay, TAT timestamps, cost, idle, capacity)
  4. Mobility Assistant      (vehicle_type, daily_distance, fuel fields)

For each domain this engine reports:
  • PRESENT   — column found, data quality good
  • PARTIAL   — column found but >30% null / low cardinality
  • MISSING   — column not found at all
  • ESTIMATED — will fall back to a labeled proxy / illustrative default

The result drives the Upload page's interactive "Column Health Dashboard"
and powers the multi-dataset registry that lets users supplement missing
fields by uploading a second (or third) file.
"""

import math
import re
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
# DOMAIN DEFINITIONS
# Each domain maps a logical field name → list of alias patterns that
# detect_column() uses (substring, case-insensitive).
# "required" = True means the module CANNOT function without this field
# "fallback"  = human-readable description of what RouteIQ does when missing
# ─────────────────────────────────────────────

DOMAIN_SCHEMA = {
    # ── ESG ANALYSIS ─────────────────────────────────────────────────
    "esg": {
        "label": "ESG Analysis",
        "icon": "🌿",
        "fields": {
            "vehicle": {
                "aliases": ["vehicletype", "vehicle_type", "truck", "lorry", "transport", "vehicle"],
                "required": True,
                "dtype": "categorical",
                "fallback": "ESG module cannot compute emissions without a vehicle column.",
            },
            "distance": {
                "aliases": ["distance", "dist_km", "km", "kilometer", "length"],
                "required": True,
                "dtype": "numeric",
                "fallback": "ESG module cannot compute emissions without a distance column.",
            },
            "weight": {
                "aliases": ["weight", "cargo", "load", "tonnage", "payload"],
                "required": False,
                "dtype": "numeric",
                "fallback": "Will extract stated vehicle capacity from name (Tier 3 proxy) or fall back to distance-only emissions factor (Tier 4).",
            },
            "cost": {
                "aliases": ["cost", "price", "freight", "charge", "amount", "rate"],
                "required": False,
                "dtype": "numeric",
                "fallback": "Carbon cost shown; freight cost analysis unavailable.",
            },
            "date": {
                "aliases": ["date", "datetime", "shipment_date", "created", "order_date", "dispatch"],
                "required": False,
                "dtype": "datetime",
                "fallback": "Time-series / trend charts unavailable.",
            },
            "status": {
                "aliases": ["status", "delivery_status", "ontime", "on_time", "delivery"],
                "required": False,
                "dtype": "categorical",
                "fallback": "On-time delivery KPI unavailable (Operational Excellence will estimate via proxy).",
            },
            "route": {
                "aliases": ["route", "lane", "origin", "source", "from"],
                "required": False,
                "dtype": "categorical",
                "fallback": "Route-level ESG breakdown unavailable.",
            },
        },
    },

    # ── OPERATIONAL EXCELLENCE ────────────────────────────────────────
    "opex": {
        "label": "Operational Excellence",
        "icon": "🎯",
        "fields": {
            "vehicle": {
                "aliases": ["vehicletype", "vehicle_type", "truck", "lorry", "transport", "vehicle"],
                "required": True,
                "dtype": "categorical",
                "fallback": "Fleet utilization and sigma-level calculations unavailable.",
            },
            "distance": {
                "aliases": ["distance", "dist_km", "km", "kilometer"],
                "required": True,
                "dtype": "numeric",
                "fallback": "Throughput and route-level KPIs unavailable.",
            },
            "status": {
                "aliases": ["status", "delivery_status", "ontime", "on_time", "delay_status"],
                "required": False,
                "dtype": "categorical",
                "fallback": "OTD computed via Tier 3 cost-per-km proxy — add a status column for accurate OTD.",
            },
            "delay_reason": {
                "aliases": ["reason", "cause", "delay_reason", "root_cause", "exception"],
                "required": False,
                "dtype": "categorical",
                "fallback": "Root cause analysis uses Tier 3 illustrative industry split — add a delay-reason column for real Pareto.",
            },
            "planned_time": {
                "aliases": ["promised", "planned", "expected", "scheduled", "eta", "planned_delivery"],
                "required": False,
                "dtype": "datetime",
                "fallback": "TAT (Turnaround Time) KPI unavailable.",
            },
            "actual_time": {
                "aliases": ["actual", "delivered_time", "arrival", "ata", "actual_delivery"],
                "required": False,
                "dtype": "datetime",
                "fallback": "TAT KPI unavailable.",
            },
            "cost": {
                "aliases": ["cost", "price", "freight", "charge", "amount"],
                "required": False,
                "dtype": "numeric",
                "fallback": "Cost-per-shipment and delay-cost impact unavailable.",
            },
            "weight": {
                "aliases": ["weight", "cargo", "load", "tonnage"],
                "required": False,
                "dtype": "numeric",
                "fallback": "Fleet utilization requires both weight and capacity columns.",
            },
            "capacity": {
                "aliases": ["capacity", "max_load", "payload", "max_weight"],
                "required": False,
                "dtype": "numeric",
                "fallback": "Fleet utilization unavailable without capacity column.",
            },
            "idle_time": {
                "aliases": ["idle", "waiting", "dwell", "idle_hours", "wait_time"],
                "required": False,
                "dtype": "numeric",
                "fallback": "Vehicle idle time KPI unavailable.",
            },
            "date": {
                "aliases": ["date", "datetime", "shipment_date", "created", "order_date"],
                "required": False,
                "dtype": "datetime",
                "fallback": "Warehouse throughput (shipments/day) unavailable.",
            },
        },
    },

    # ── ROUTE OPTIMIZATION ────────────────────────────────────────────
    "route": {
        "label": "Route Optimization",
        "icon": "🌐",
        "fields": {
            "source_city": {
                "aliases": ["source", "origin", "from_city", "from", "origin_city", "departure"],
                "required": False,
                "dtype": "categorical",
                "fallback": "Route Optimization uses its own master dataset (ESG_Logistics_Final_Master_Dataset.xlsx); this field is optional here.",
            },
            "destination_city": {
                "aliases": ["destination", "to_city", "to", "dest", "arrival_city", "delivery_city"],
                "required": False,
                "dtype": "categorical",
                "fallback": "Route Optimization uses its own master dataset; this field is optional here.",
            },
            "distance": {
                "aliases": ["distance", "km", "kilometer", "dist_km"],
                "required": False,
                "dtype": "numeric",
                "fallback": "Live OSRM distances used when coordinates available.",
            },
            "mode": {
                "aliases": ["mode", "transport_mode", "transportmode", "modetype"],
                "required": False,
                "dtype": "categorical",
                "fallback": "Mode auto-selected from multimodal graph.",
            },
        },
    },

    # ── MOBILITY ASSISTANT ────────────────────────────────────────────
    "mobility": {
        "label": "Mobility Assistant",
        "icon": "🚀",
        "fields": {
            "vehicle_type": {
                "aliases": ["vehicletype", "vehicle_type", "vehicle", "transport_type"],
                "required": False,
                "dtype": "categorical",
                "fallback": "Mobility Assistant uses sidebar inputs; dataset is supplemental.",
            },
            "fuel_cost": {
                "aliases": ["fuel", "fuel_cost", "fuel_price", "petrol", "diesel_price"],
                "required": False,
                "dtype": "numeric",
                "fallback": "Fuel cost entered manually via sidebar.",
            },
            "daily_distance": {
                "aliases": ["daily_distance", "daily_km", "commute_km", "daily_dist"],
                "required": False,
                "dtype": "numeric",
                "fallback": "Daily distance entered manually via sidebar.",
            },
        },
    },
}

# ─────────────────────────────────────────────
# LEGACY REQUIRED COLUMN GROUPS (backward compat)
# ─────────────────────────────────────────────
REQUIRED_COLUMN_GROUPS = {
    "vehicle":  DOMAIN_SCHEMA["esg"]["fields"]["vehicle"]["aliases"],
    "distance": DOMAIN_SCHEMA["esg"]["fields"]["distance"]["aliases"],
}

# ─────────────────────────────────────────────
# MULTI-DATASET REGISTRY KEY (stored in session_state)
# ─────────────────────────────────────────────
DATASET_REGISTRY_KEY = "dataset_registry"   # session_state key → list of DatasetEntry dicts


# ─────────────────────────────────────────────
# CORE COLUMN DETECTOR (unchanged public API)
# ─────────────────────────────────────────────
def detect_column(possible_names, columns):
    """
    Case-insensitive substring match. Returns the first matching column
    name from `columns`, or None if nothing matches.
    """
    for name in possible_names:
        for col in columns:
            if name.lower() in str(col).lower():
                return col
    return None


# ─────────────────────────────────────────────
# DTYPE CHECKER
# ─────────────────────────────────────────────
def _infer_field_quality(series: pd.Series, expected_dtype: str) -> dict:
    """
    Returns quality metadata for a single column Series.
    {
      "null_pct":     float,
      "dtype_ok":     bool,
      "cardinality":  int,   # unique value count
      "sample":       list,  # up to 5 sample values
      "quality":      "good" | "partial" | "poor",
    }
    """
    n = len(series)
    null_pct = round(series.isna().sum() / n * 100, 1) if n else 100.0
    cardinality = series.nunique(dropna=True)
    sample = series.dropna().unique()[:5].tolist()

    dtype_ok = True
    if expected_dtype == "numeric":
        numeric = pd.to_numeric(series, errors="coerce")
        dtype_ok = numeric.notna().sum() / max(n, 1) >= 0.7
    elif expected_dtype == "datetime":
        parsed = pd.to_datetime(series, errors="coerce")
        dtype_ok = parsed.notna().sum() / max(n, 1) >= 0.5
    elif expected_dtype == "categorical":
        dtype_ok = cardinality >= 1

    if null_pct > 60 or not dtype_ok:
        quality = "poor"
    elif null_pct > 25:
        quality = "partial"
    else:
        quality = "good"

    return {
        "null_pct": null_pct,
        "dtype_ok": dtype_ok,
        "cardinality": cardinality,
        "sample": [str(s) for s in sample],
        "quality": quality,
    }


# ─────────────────────────────────────────────
# DOMAIN COVERAGE ANALYSIS
# ─────────────────────────────────────────────
def analyse_domain_coverage(df: pd.DataFrame) -> dict:
    """
    For each analytics domain, checks which logical fields are present,
    partial, or missing.

    Returns:
    {
      "esg":      { "score": 0-100, "fields": { field_name: FieldResult } },
      "opex":     { ... },
      "route":    { ... },
      "mobility": { ... },
      "merged_fields": { col_name: [domain_names...] },   # which cols serve multiple domains
    }

    FieldResult = {
      "status":    "present" | "partial" | "missing",
      "col":       str | None,   # matched column name
      "quality":   dict | None,  # _infer_field_quality output (if present)
      "required":  bool,
      "fallback":  str,
      "dtype":     str,
    }
    """
    results = {}
    cols = list(df.columns)

    for domain_key, domain_def in DOMAIN_SCHEMA.items():
        field_results = {}
        score_parts = []

        for field_name, field_def in domain_def["fields"].items():
            matched_col = detect_column(field_def["aliases"], cols)

            if matched_col is None:
                field_results[field_name] = {
                    "status": "missing",
                    "col": None,
                    "quality": None,
                    "required": field_def["required"],
                    "fallback": field_def["fallback"],
                    "dtype": field_def["dtype"],
                }
                score_parts.append(0 if field_def["required"] else 30)
            else:
                quality = _infer_field_quality(df[matched_col], field_def["dtype"])
                if quality["quality"] == "good":
                    status = "present"
                    score_parts.append(100)
                elif quality["quality"] == "partial":
                    status = "partial"
                    score_parts.append(60)
                else:
                    status = "poor"
                    score_parts.append(20)

                field_results[field_name] = {
                    "status": status,
                    "col": matched_col,
                    "quality": quality,
                    "required": field_def["required"],
                    "fallback": field_def["fallback"],
                    "dtype": field_def["dtype"],
                }

        domain_score = round(sum(score_parts) / len(score_parts)) if score_parts else 0
        results[domain_key] = {
            "label": domain_def["label"],
            "icon": domain_def["icon"],
            "score": domain_score,
            "fields": field_results,
        }

    return results


# ─────────────────────────────────────────────
# MISSING FIELD SUPPLEMENT SUGGESTIONS
# ─────────────────────────────────────────────
def get_supplement_suggestions(coverage: dict) -> list:
    """
    Returns a list of supplement suggestions — fields that are missing
    across one or more domains and could be provided via a supplemental
    upload.

    Each suggestion:
    {
      "field":       str,           # logical field name
      "domains":     [str],         # domain labels affected
      "impact":      str,           # what becomes available if fixed
      "aliases":     [str],         # what column names to use in the supplement file
      "required":    bool,
      "dtype":       str,
    }
    """
    # Collect all missing fields across domains, deduped by field name
    missing_map = {}  # field_name → {domains, aliases, required, dtype, impacts}

    for domain_key, domain_result in coverage.items():
        domain_label = DOMAIN_SCHEMA[domain_key]["label"]
        for field_name, field_result in domain_result["fields"].items():
            if field_result["status"] in ("missing", "poor"):
                if field_name not in missing_map:
                    missing_map[field_name] = {
                        "field": field_name,
                        "domains": [],
                        "impacts": [],
                        "aliases": DOMAIN_SCHEMA[domain_key]["fields"][field_name]["aliases"],
                        "required": field_result["required"],
                        "dtype": field_result["dtype"],
                        "fallback": field_result["fallback"],
                    }
                missing_map[field_name]["domains"].append(domain_label)
                missing_map[field_name]["impacts"].append(field_result["fallback"])

    # Sort: required first, then by number of domains affected
    suggestions = sorted(
        missing_map.values(),
        key=lambda x: (-int(x["required"]), -len(x["domains"])),
    )
    return suggestions


# ─────────────────────────────────────────────
# MULTI-DATASET REGISTRY OPERATIONS
# ─────────────────────────────────────────────
def make_dataset_entry(
    df: pd.DataFrame,
    filename: str,
    file_size: int,
    uploaded_at: str,
    label: str = "",
    primary: bool = False,
) -> dict:
    """
    Creates a registry entry dict for a single uploaded dataset.
    """
    coverage = analyse_domain_coverage(df)
    return {
        "df": df,
        "filename": filename,
        "file_size": file_size,
        "uploaded_at": uploaded_at,
        "label": label or filename,
        "primary": primary,
        "coverage": coverage,
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "columns": list(df.columns),
    }


def merge_datasets(registry: list) -> pd.DataFrame:
    """
    Merges all datasets in the registry into a single DataFrame.

    Strategy:
    1. Primary dataset is the base.
    2. Supplemental datasets are concatenated (union of all columns) —
       columns that exist in both are NOT overwritten; supplement columns
       are added as new columns.

    This allows uploading a "weights supplement" CSV that only has
    [shipment_id, weight] and getting those merged into the primary.
    """
    if not registry:
        return pd.DataFrame()

    primary_entries = [e for e in registry if e["primary"]]
    other_entries = [e for e in registry if not e["primary"]]

    if not primary_entries:
        # No explicit primary — use first entry
        base = registry[0]["df"].copy()
        others = [e["df"] for e in registry[1:]]
    else:
        base = primary_entries[0]["df"].copy()
        others = [e["df"] for e in other_entries]

    if not others:
        return base

    # Merge supplemental datasets by concatenating missing columns
    for sup_df in others:
        new_cols = [c for c in sup_df.columns if c not in base.columns]
        if new_cols:
            # Align by index (row order) — simple concat of new columns
            sup_subset = sup_df[new_cols].reset_index(drop=True)
            base_reset = base.reset_index(drop=True)
            # Pad or truncate supplement to match base length
            n = len(base_reset)
            if len(sup_subset) < n:
                pad = pd.DataFrame(index=range(len(sup_subset), n), columns=new_cols)
                sup_subset = pd.concat([sup_subset, pad], ignore_index=True)
            else:
                sup_subset = sup_subset.iloc[:n]
            base = pd.concat([base_reset, sup_subset], axis=1)

    return base.reset_index(drop=True)


def get_merged_df(registry: list) -> pd.DataFrame:
    """Convenience wrapper — returns the merged DataFrame from the registry."""
    return merge_datasets(registry)


# ─────────────────────────────────────────────
# LEGACY validate_dataset (unchanged public API)
# ─────────────────────────────────────────────
def validate_dataset(df: pd.DataFrame) -> dict:
    """
    Backward-compatible validation used by upload.py's file-processor.
    Returns {"errors": [...], "warnings": [...], "info": [...]}

    Now also embeds domain coverage summary in info[] for display.
    """
    report = {"errors": [], "warnings": [], "info": []}

    if df is None or df.empty:
        report["errors"].append("The uploaded file has no rows of data.")
        return report

    if len(df.columns) == 0:
        report["errors"].append("The uploaded file has no columns.")
        return report

    dupes = df.columns[df.columns.duplicated()].tolist()
    if dupes:
        report["errors"].append(
            f"Duplicate column names found: {', '.join(map(str, set(dupes)))}"
        )

    clean_cols = [str(c).strip() for c in df.columns]

    for label, aliases in REQUIRED_COLUMN_GROUPS.items():
        if not detect_column(aliases, clean_cols):
            report["warnings"].append(
                f"Couldn't auto-detect a '{label}' column. "
                f"You'll need to map it manually on the ESG Analysis page."
            )

    empty_rows = df.isna().all(axis=1).sum()
    if empty_rows > 0:
        report["warnings"].append(f"{empty_rows} completely empty row(s) found.")

    empty_cols = df.columns[df.isna().all(axis=0)].tolist()
    if empty_cols:
        report["warnings"].append(
            f"{len(empty_cols)} completely empty column(s): {', '.join(map(str, empty_cols))}"
        )

    dup_rows = df.duplicated().sum()
    if dup_rows > 0:
        report["warnings"].append(f"{dup_rows} duplicate row(s) found.")

    null_pct = (df.isna().sum() / len(df) * 100).round(1)
    high_null_cols = null_pct[(null_pct > 30) & (null_pct < 100)]
    if not high_null_cols.empty:
        cols_str = ", ".join(f"{c} ({p}% missing)" for c, p in high_null_cols.items())
        report["warnings"].append(f"Columns with significant missing data: {cols_str}")

    report["info"].append(f"{len(df):,} rows × {len(df.columns)} columns loaded.")
    return report


# ─────────────────────────────────────────────
# CLEAN DATASET (unchanged public API)
# ─────────────────────────────────────────────
def clean_dataset(
    df: pd.DataFrame,
    drop_empty_rows: bool = True,
    drop_empty_cols: bool = True,
    strip_col_names: bool = True,
) -> pd.DataFrame:
    df = df.copy()
    if strip_col_names:
        df.columns = [str(c).strip() for c in df.columns]
    if drop_empty_rows:
        df = df.dropna(how="all")
    if drop_empty_cols:
        df = df.dropna(how="all", axis=1)
    return df.reset_index(drop=True)