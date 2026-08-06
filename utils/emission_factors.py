"""
Emission factor methodology.

Primary approach: GLEC Framework v3.2 (Smart Freight Centre), aligned with
ISO 14083:2023, well-to-wheel (WTW), AR6 GWP-100 basis.
Formula: emissions (kg CO2e) = cargo weight (tonnes) x distance (km) x factor (kg CO2e/tonne-km)

Data quality tiers (per GLEC's own hierarchy):
  Tier 2 - Published default factor for vehicle class     -> used for HCV / rigid trucks
  Tier 3 - Interpolated/engineering-estimated factor        -> used for LCV / mini / van
  Tier 4 - Fallback distance-only proxy (no weight data)     -> used only if cargo weight is missing

Sources:
- Smart Freight Centre, GLEC Framework v3.2, Table 8: Articulated 34-40t GVW,
  average/mixed load, diesel -> 0.101 kg CO2e/tonne-km (WTW)
- GLEC v3.2-derived rigid truck (7.5-12t) factor -> 0.223 kg CO2e/tonne-km (WTW)
These are the two publicly documented anchor points used here. LCV/mini/van
factors below are NOT independently published GLEC defaults; they are
interpolated estimates (Tier 3) based on the well-established inverse
relationship between vehicle payload capacity and per-tonne-km carbon
intensity (smaller vehicles carry less freight per trip so post per-tonne
emissions rise, even though absolute per-km emissions are lower).
"""

# kg CO2e per tonne-km, WTW basis
TONNE_KM_FACTORS = {
    "HEAVY":  {"factor": 0.101, "tier": 2, "source": "GLEC v3.2 Table 8 (Artic 34-40t, avg/mixed, diesel)"},
    "RIGID":  {"factor": 0.223, "tier": 2, "source": "GLEC v3.2-derived (Rigid 7.5-12t)"},
    "LIGHT":  {"factor": 0.350, "tier": 3, "source": "Interpolated estimate - no published GLEC default for this class"},
    "MINI":   {"factor": 0.450, "tier": 3, "source": "Interpolated estimate - no published GLEC default for this class"},
}

# Fallback ONLY used when cargo weight is unavailable in the dataset
# (kg CO2 per vehicle-km, not tonne-km) - Tier 4, distance-only proxy
DISTANCE_ONLY_FALLBACK = {
    "HEAVY": 0.85,
    "RIGID": 0.45,
    "LIGHT": 0.22,
    "MINI":  0.15,
}


def classify_vehicle(vehicle_name: str) -> str:
    v = str(vehicle_name).upper()
    if any(x in v for x in ["HCV", "AXLE", "TRAILER", "MULTI"]):
        return "HEAVY"
    elif any(x in v for x in ["TRUCK", "LPT"]):
        return "RIGID"
    elif any(x in v for x in ["LCV", "ACE", "PICKUP"]):
        return "LIGHT"
    elif any(x in v for x in ["MINI", "VAN"]):
        return "MINI"
    return "RIGID"  # conservative middle-ground default


def calculate_emissions_kg(vehicle_name: str, distance_km: float, weight_tonnes: float = None) -> dict:
    """
    Returns dict: {emissions_kg, method, tier, factor, source}
    Uses tonne-km method (Tier 2/3) when weight is available,
    falls back to distance-only proxy (Tier 4) when it isn't.
    """
    vclass = classify_vehicle(vehicle_name)

    if weight_tonnes is not None and weight_tonnes > 0:
        f = TONNE_KM_FACTORS[vclass]
        emissions = weight_tonnes * distance_km * f["factor"]
        return {
            "emissions_kg": emissions,
            "method": "tonne-km (GLEC v3.2)",
            "tier": f["tier"],
            "factor": f["factor"],
            "source": f["source"],
        }
    else:
        factor = DISTANCE_ONLY_FALLBACK[vclass]
        emissions = distance_km * factor
        return {
            "emissions_kg": emissions,
            "method": "distance-only proxy (no cargo weight in dataset)",
            "tier": 4,
            "factor": factor,
            "source": "Tier 4 fallback - engineering estimate, cargo weight not available",
        }
import re

def extract_capacity_tonnes(vehicle_type_str: str) -> float:
    """
    Extracts vehicle carrying-capacity in tonnes from a description string
    like '32 FT SINGLE-AXLE 7MT - HCV' or '1 MT TATA ACE (OPEN BODY)'.
    Returns None if no tonnage pattern is found.

    NOTE: this is the vehicle's stated capacity, not the actual cargo
    weight carried on a given trip - used as a Tier 3 proxy when no
    real shipment-level weight data exists.
    """
    if not vehicle_type_str:
        return None
    match = re.search(r'(\d+(?:\.\d+)?)\s*MT\b', str(vehicle_type_str).upper())
    if match:
        return float(match.group(1))
    return None