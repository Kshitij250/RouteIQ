import pandas as pd
import networkx as nx
import itertools

# =====================================================
# TRANSPORT ASSETS
# =====================================================

TRANSPORT_ASSETS = {
    # ROAD
    "Tata Ace": {
        "mode": "Road", "capacity": 1, "speed": 45,
        "kmpl": 18, "fuel_type": "Diesel", "co2_per_litre": 2.68, "cost_per_km": 12
    },
    "Pickup Truck": {
        "mode": "Road", "capacity": 3, "speed": 50,
        "kmpl": 12, "fuel_type": "Diesel", "co2_per_litre": 2.68, "cost_per_km": 18
    },
    "Medium Truck": {
        "mode": "Road", "capacity": 10, "speed": 55,
        "kmpl": 6, "fuel_type": "Diesel", "co2_per_litre": 2.68, "cost_per_km": 35
    },
    "Heavy Truck": {
        "mode": "Road", "capacity": 20, "speed": 60,
        "kmpl": 4, "fuel_type": "Diesel", "co2_per_litre": 2.68, "cost_per_km": 55
    },
    # RAIL
    "Freight Rail": {
        "mode": "Rail", "capacity": 3000, "speed": 65,
        "fuel_type": "Diesel", "fuel_litre_per_ton_km": 0.004,
        "co2_per_litre": 2.68, "cost_per_ton_km": 0.9
    },
    "Electric Freight Rail": {
        "mode": "Rail", "capacity": 3000, "speed": 75,
        "fuel_type": "Electric", "co2_per_kwh": 0.7, "cost_per_ton_km": 0.8
    },
    # SEA
    "Container Ship": {
        "mode": "Sea", "capacity": 50000, "speed": 32,
        "fuel_type": "Marine Fuel", "fuel_litre_per_ton_km": 0.002,
        "co2_per_litre": 3.11, "cost_per_ton_km": 0.4
    },
    "Bulk Carrier": {
        "mode": "Sea", "capacity": 120000, "speed": 28,
        "fuel_type": "Marine Fuel", "fuel_litre_per_ton_km": 0.0015,
        "co2_per_litre": 3.11, "cost_per_ton_km": 0.3
    },
    # AIR
    "Cargo Aircraft": {
        "mode": "Air", "capacity": 100, "speed": 750,
        "fuel_type": "Jet Fuel", "fuel_litre_per_ton_km": 0.8,
        "co2_per_litre": 2.54, "cost_per_ton_km": 12
    },
    "Express Air Freight": {
        "mode": "Air", "capacity": 40, "speed": 850,
        "fuel_type": "Jet Fuel", "fuel_litre_per_ton_km": 1.0,
        "co2_per_litre": 2.54, "cost_per_ton_km": 15
    },
}

# Best asset per mode for each optimization target
BEST_ASSET_FOR = {
    "cheapest": {
        "Road": "Heavy Truck",          # highest capacity → lowest cost/km effective
        "Rail": "Electric Freight Rail", # lowest cost_per_ton_km
        "Sea":  "Bulk Carrier",          # lowest cost_per_ton_km
        "Air":  "Cargo Aircraft",        # lower cost_per_ton_km
    },
    "fastest": {
        "Road": "Heavy Truck",           # highest speed road
        "Rail": "Electric Freight Rail", # highest speed rail
        "Sea":  "Container Ship",        # highest speed sea
        "Air":  "Express Air Freight",   # highest speed air
    },
    "greenest": {
        "Road": "Heavy Truck",           # highest capacity → best utilization per ton
        "Rail": "Electric Freight Rail", # electric → lowest co2
        "Sea":  "Bulk Carrier",          # lowest fuel_litre_per_ton_km
        "Air":  "Cargo Aircraft",        # lower co2 multiplier
    },
}

MODE_TRANSFER_COST = 5000   # ₹ penalty per mode switch
MODE_TRANSFER_TIME = 4      # hrs penalty per mode switch


def get_assets_by_mode(mode):
    return [a for a, info in TRANSPORT_ASSETS.items() if info["mode"] == mode]


# =====================================================
# LOAD DATA
# =====================================================

def load_data(file_path):
    return {
        "transport_modes":  pd.read_excel(file_path, sheet_name="transport_modes"),
        "road_corridors":   pd.read_excel(file_path, sheet_name="road_corridors"),
        "rail_corridors":   pd.read_excel(file_path, sheet_name="rail_corridors"),
        "sea_corridors":    pd.read_excel(file_path, sheet_name="sea_corridors"),
        "air_corridors":    pd.read_excel(file_path, sheet_name="air_corridors"),
        "eta_factors":      pd.read_excel(file_path, sheet_name="eta_factors"),
        "carbon_pricing":   pd.read_excel(file_path, sheet_name="carbon_pricing"),
        "city_coordinates": pd.read_excel(file_path, sheet_name="city_coordinates"),
    }


# =====================================================
# BUILD MULTIMODAL GRAPH
# (MultiGraph: multiple edges per node pair, one per mode)
# =====================================================

def build_multimodal_graph(data):
    """
    Returns a networkx MultiGraph where each (u,v) pair can have
    multiple edges — one per available transport mode.
    Each edge carries: distance, mode, cost_factor, speed,
    co2_factor, handling_cost.
    """
    G = nx.MultiGraph()

    corridor_sheets = {
        "Road": data["road_corridors"],
        "Rail": data["rail_corridors"],
        "Sea":  data["sea_corridors"],
        "Air":  data["air_corridors"],
    }

    transport_modes = data["transport_modes"]

    for mode, table in corridor_sheets.items():
        mode_info = transport_modes[transport_modes["mode"] == mode]
        if mode_info.empty:
            continue
        mode_info = mode_info.iloc[0]

        source_col      = table.columns[0]
        destination_col = table.columns[1]

        for _, row in table.iterrows():
            G.add_edge(
                row[source_col],
                row[destination_col],
                distance=row["distance_km"],
                mode=mode,
                cost_factor=mode_info["cost_per_ton_km"],
                speed=mode_info["speed_kmph"],
                co2_factor=mode_info["co2_kg_per_ton_km"],
                handling_cost=mode_info["handling_cost_inr"],
            )

    return G


# =====================================================
# SEGMENT METRICS (for a single segment + asset)
# =====================================================

def _segment_metrics(distance, mode, asset_name, cargo_weight):
    """
    Returns (cost, eta_hrs, co2_kg, fuel_litres, fuel_type) for one segment.
    """
    a = TRANSPORT_ASSETS[asset_name]
    speed = a["speed"]
    fuel_type = a["fuel_type"]
    eta = distance / speed

    if mode == "Road":
        kmpl        = a["kmpl"]
        capacity    = a["capacity"]
        utilization = min(cargo_weight / capacity, 1.0)
        eff_kmpl    = kmpl * (1 - 0.3 * utilization)
        fuel        = distance / eff_kmpl
        co2         = fuel * a["co2_per_litre"]
        cost        = distance * a["cost_per_km"]

    elif mode == "Rail":
        if fuel_type == "Electric":
            # Electric rail: use co2_per_kwh proxy, very low emissions
            fuel = distance * cargo_weight * 0.002   # kWh proxy stored as "fuel"
            co2  = fuel * a.get("co2_per_kwh", 0.7)
            cost = distance * cargo_weight * a["cost_per_ton_km"]
        else:
            utilization = min(cargo_weight / a["capacity"], 1.0)
            fuel        = distance * a["fuel_litre_per_ton_km"] * (1 + 0.15 * utilization)
            co2         = fuel * a["co2_per_litre"]
            cost        = distance * cargo_weight * a["cost_per_ton_km"]

    elif mode == "Sea":
        utilization = min(cargo_weight / a["capacity"], 1.0)
        fuel        = distance * a["fuel_litre_per_ton_km"] * (1 + 0.10 * utilization)
        co2         = fuel * a["co2_per_litre"]
        cost        = distance * cargo_weight * a["cost_per_ton_km"]

    else:  # Air
        utilization = min(cargo_weight / a["capacity"], 1.0)
        fuel        = distance * a["fuel_litre_per_ton_km"] * (1 + 0.40 * utilization)
        co2         = fuel * a["co2_per_litre"]
        cost        = distance * cargo_weight * a["cost_per_ton_km"]

    return cost, eta, co2, fuel, fuel_type


# =====================================================
# BUILD OPTIMIZED WEIGHTED GRAPH (simple Graph for path-finding)
# =====================================================

def _build_optimized_graph(data, G_multi, objective, cargo_weight):
    """
    Collapses the MultiGraph into a simple Graph where each edge
    carries the BEST weight for the given objective, along with
    the winning mode and asset.

    objective: "cheapest" | "fastest" | "greenest"
    """
    G_opt = nx.Graph()

    # Collect all unique node pairs that have at least one edge
    seen_pairs = set()
    for u, v, edge_data in G_multi.edges(data=True):
        pair = (min(u, v), max(u, v))
        seen_pairs.add((pair, edge_data["distance"], u, v))

    # For every (u,v) pair, find which mode+asset is best
    corridor_availability = _build_corridor_availability(data)

    processed = set()
    for u, v, edge_data in G_multi.edges(data=True):
        pair = (min(u, v), max(u, v))
        if pair in processed:
            continue
        processed.add(pair)

        distance = edge_data["distance"]
        available_modes = corridor_availability.get(pair, set())

        best_weight = float("inf")
        best_mode   = None
        best_asset  = None

        for mode in available_modes:
            asset = BEST_ASSET_FOR[objective].get(mode)
            if asset is None:
                continue
            try:
                cost, eta, co2, fuel, _ = _segment_metrics(distance, mode, asset, cargo_weight)
            except Exception:
                continue

            if objective == "cheapest":
                w = cost
            elif objective == "fastest":
                w = eta
            else:  # greenest
                w = co2

            if w < best_weight:
                best_weight = w
                best_mode   = mode
                best_asset  = asset

        if best_mode is not None:
            G_opt.add_edge(
                u, v,
                weight=best_weight,
                distance=distance,
                mode=best_mode,
                asset=best_asset,
            )

    return G_opt


def _build_corridor_availability(data):
    """
    Returns dict: {(min_city, max_city): set_of_modes}
    """
    availability = {}
    corridor_sheets = {
        "Road": data["road_corridors"],
        "Rail": data["rail_corridors"],
        "Sea":  data["sea_corridors"],
        "Air":  data["air_corridors"],
    }
    for mode, table in corridor_sheets.items():
        src_col = table.columns[0]
        dst_col = table.columns[1]
        for _, row in table.iterrows():
            pair = (min(row[src_col], row[dst_col]), max(row[src_col], row[dst_col]))
            availability.setdefault(pair, set()).add(mode)
    return availability


# =====================================================
# OPTIMIZED ROUTE FINDERS
# =====================================================

def find_cheapest_route(G_multi, source, destination, data=None, cargo_weight=1):
    if data is not None:
        G_opt = _build_optimized_graph(data, G_multi, "cheapest", cargo_weight)
        try:
            return nx.shortest_path(G_opt, source, destination, weight="weight")
        except Exception:
            pass
    # Fallback
    try:
        return nx.shortest_path(G_multi, source, destination, weight="cost_factor")
    except Exception:
        return []


def find_fastest_route(G_multi, source, destination, data=None, cargo_weight=1):
    if data is not None:
        G_opt = _build_optimized_graph(data, G_multi, "fastest", cargo_weight)
        try:
            return nx.shortest_path(G_opt, source, destination, weight="weight")
        except Exception:
            pass
    try:
        return nx.shortest_path(
            G_multi, source, destination,
            weight=lambda u, v, d: d["distance"] / d["speed"]
        )
    except Exception:
        return []


def find_greenest_route(G_multi, source, destination, data=None, cargo_weight=1):
    if data is not None:
        G_opt = _build_optimized_graph(data, G_multi, "greenest", cargo_weight)
        try:
            return nx.shortest_path(G_opt, source, destination, weight="weight")
        except Exception:
            pass
    try:
        return nx.shortest_path(G_multi, source, destination, weight="co2_factor")
    except Exception:
        return []


# =====================================================
# BUILD AUTO SELECTION (optimized per strategy)
# =====================================================

def build_auto_selection(G_multi, route, objective="cheapest", data=None, cargo_weight=1):
    """
    For each segment in route, pick the best mode+asset for the given objective.
    If data is provided, checks actual corridor availability.
    Falls back to graph edge mode if nothing else available.
    """
    selections = {}
    corridor_availability = _build_corridor_availability(data) if data else {}

    for i in range(len(route) - 1):
        u, v = route[i], route[i + 1]

        # Distance from graph (first available edge)
        try:
            if isinstance(G_multi, nx.MultiGraph):
                edge_data = list(G_multi[u][v].values())[0]
            else:
                edge_data = G_multi[u][v]
            distance = edge_data["distance"]
        except Exception:
            distance = 500  # fallback

        pair = (min(u, v), max(u, v))
        available_modes = corridor_availability.get(pair, set())

        if not available_modes:
            # Fallback: use whatever mode the graph has
            try:
                if isinstance(G_multi, nx.MultiGraph):
                    fallback_mode = list(G_multi[u][v].values())[0]["mode"]
                else:
                    fallback_mode = G_multi[u][v]["mode"]
            except Exception:
                fallback_mode = "Road"
            available_modes = {fallback_mode}

        best_weight = float("inf")
        best_mode   = None
        best_asset  = None

        for mode in available_modes:
            asset = BEST_ASSET_FOR[objective].get(mode)
            if asset is None:
                continue
            try:
                cost, eta, co2, fuel, _ = _segment_metrics(distance, mode, asset, cargo_weight)
            except Exception:
                continue

            w = cost if objective == "cheapest" else (eta if objective == "fastest" else co2)

            if w < best_weight:
                best_weight = w
                best_mode   = mode
                best_asset  = asset

        if best_mode is None:
            best_mode  = list(available_modes)[0]
            best_asset = BEST_ASSET_FOR[objective].get(best_mode, get_default_asset(best_mode))

        selections[(u, v)] = {"mode": best_mode, "asset": best_asset}

    return selections


def get_default_asset(mode):
    defaults = {
        "Road": "Medium Truck",
        "Rail": "Freight Rail",
        "Sea":  "Container Ship",
        "Air":  "Cargo Aircraft",
    }
    return defaults.get(mode, "Medium Truck")


# =====================================================
# CALCULATE CUSTOM ROUTE (user-selected or auto)
# =====================================================

def calculate_custom_route(G, route, selected_modes, cargo_weight):
    total_distance = 0
    total_cost     = 0
    total_eta      = 0
    total_co2      = 0
    total_fuel     = 0
    diesel         = 0
    marine         = 0
    jet            = 0
    route_modes    = []
    prev_mode      = None

    for i in range(len(route) - 1):
        u, v = route[i], route[i + 1]

        # Get distance from graph
        try:
            if isinstance(G, nx.MultiGraph):
                # Find edge matching the selected mode if possible
                seg_info    = selected_modes[(u, v)]
                chosen_mode = seg_info["mode"]
                edge_data   = None
                for k, ed in G[u][v].items():
                    if ed["mode"] == chosen_mode:
                        edge_data = ed
                        break
                if edge_data is None:
                    edge_data = list(G[u][v].values())[0]
            else:
                edge_data = G[u][v]
            distance = edge_data["distance"]
        except Exception:
            distance = 500

        seg_info   = selected_modes.get((u, v), {})
        mode       = seg_info.get("mode", "Road")
        asset_name = seg_info.get("asset", get_default_asset(mode))

        cost, eta, co2, fuel, fuel_type = _segment_metrics(
            distance, mode, asset_name, cargo_weight
        )

        # Mode transfer penalty
        if prev_mode and prev_mode != mode:
            total_cost += MODE_TRANSFER_COST
            total_eta  += MODE_TRANSFER_TIME

        total_distance += distance
        total_cost     += cost
        total_eta      += eta
        total_co2      += co2
        total_fuel     += fuel
        route_modes.append(mode)
        prev_mode = mode

        if fuel_type in ("Diesel", "Electric"):
            diesel += fuel
        elif fuel_type == "Marine Fuel":
            marine += fuel
        elif fuel_type == "Jet Fuel":
            jet += fuel

    carbon_tax = total_co2 * 5

    return {
        "distance":    round(total_distance, 2),
        "cost":        round(total_cost, 2),
        "eta":         round(total_eta, 2),
        "co2":         round(total_co2, 2),
        "carbon_tax":  round(carbon_tax, 2),
        "diesel":      round(diesel, 2),
        "marine":      round(marine, 2),
        "jet":         round(jet, 2),
        "fuel":        round(total_fuel, 2),
        "modes":       route_modes,
    }


# =====================================================
# GET SEGMENT MODES (from corridor data)
# =====================================================

def get_segment_modes(data, source, destination):
    modes = []
    corridor_map = {
        "Road": data["road_corridors"],
        "Rail": data["rail_corridors"],
        "Sea":  data["sea_corridors"],
        "Air":  data["air_corridors"],
    }
    for mode, df in corridor_map.items():
        src_col = df.columns[0]
        dst_col = df.columns[1]
        for _, row in df.iterrows():
            if (
                (row[src_col] == source and row[dst_col] == destination) or
                (row[src_col] == destination and row[dst_col] == source)
            ):
                modes.append(mode)
                break
    # Always return all 4 modes — user can pick any; metrics are computed from TRANSPORT_ASSETS
    all_modes = ["Road", "Rail", "Sea", "Air"]
    for m in all_modes:
        if m not in modes:
            modes.append(m)
    return modes


# =====================================================
# DISCOVER ROUTE (balanced shortest path)
# =====================================================

def discover_route(G, source, destination):
    try:
        if isinstance(G, nx.MultiGraph):
            # Build a simple graph using minimum weight per edge pair
            G_simple = nx.Graph()
            for u, v, ed in G.edges(data=True):
                dist = ed["distance"]
                if G_simple.has_edge(u, v):
                    if G_simple[u][v]["distance"] > dist:
                        G_simple[u][v]["distance"] = dist
                else:
                    G_simple.add_edge(u, v, distance=dist)
            return nx.shortest_path(G_simple, source, destination, weight="distance")
        return nx.shortest_path(G, source, destination, weight="distance")
    except Exception:
        return []


def build_route_segments(route):
    return [{"from": route[i], "to": route[i + 1]} for i in range(len(route) - 1)]


def get_available_modes():
    return ["Road", "Rail", "Sea", "Air"]


# =====================================================
# GET CITY COORDINATES
# =====================================================

def get_city_coordinates(data):
    coords = {}
    for _, row in data["city_coordinates"].iterrows():
        coords[row["city"]] = (row["latitude"], row["longitude"])
    return coords


# =====================================================
# ESG SCORE
# =====================================================

def calculate_esg_score(co2):
    if co2 <= 500:   return 95
    if co2 <= 1000:  return 85
    if co2 <= 2000:  return 75
    if co2 <= 4000:  return 65
    return 50


# =====================================================
# STRATEGY PLAN — returns route + per-segment details
# =====================================================

def build_strategy_plan(route, selections):
    """
    Returns a list of dicts with per-segment breakdown for display.
    selections: {(u,v): {"mode": ..., "asset": ...}}
    """
    plan = []
    for i in range(len(route) - 1):
        u, v = route[i], route[i + 1]
        seg  = selections.get((u, v), {})
        plan.append({
            "Source":      u,
            "Destination": v,
            "Mode":        seg.get("mode", "—"),
            "Vehicle":     seg.get("asset", "—"),
        })
    return plan


# =====================================================
# CALCULATE ROUTE METRICS (legacy helper for other pages)
# =====================================================

def calculate_route_metrics(G, route, cargo_weight):
    """
    Uses the graph's edge data directly (no asset selection).
    Kept for backwards compatibility with other pages.
    """
    total_distance = 0
    total_cost     = 0
    total_eta      = 0
    total_co2      = 0
    route_modes    = []
    prev_mode      = None

    for i in range(len(route) - 1):
        try:
            if isinstance(G, nx.MultiGraph):
                edge = list(G[route[i]][route[i+1]].values())[0]
            else:
                edge = G[route[i]][route[i+1]]
        except Exception:
            continue

        distance     = edge["distance"]
        speed        = edge["speed"]
        mode         = edge["mode"]
        cost_factor  = edge["cost_factor"]
        co2_factor   = edge["co2_factor"]
        handling_cost= edge["handling_cost"]

        if prev_mode and prev_mode != mode:
            total_cost += MODE_TRANSFER_COST
            total_eta  += MODE_TRANSFER_TIME

        total_distance += distance
        total_cost     += distance * cargo_weight * cost_factor + handling_cost
        total_eta      += distance / speed
        segment_co2     = distance * cargo_weight * co2_factor
        total_co2      += segment_co2
        route_modes.append(mode)
        prev_mode = mode

    DIESEL_CO2 = 2.68
    total_fuel = total_co2 / DIESEL_CO2
    carbon_tax = total_co2 * 5

    return {
        "distance":          round(total_distance, 2),
        "cost":              round(total_cost, 2),
        "eta":               round(total_eta, 2),
        "co2":               round(total_co2, 2),
        "fuel":              round(total_fuel, 2),
        "carbon_tax":        round(carbon_tax, 2),
        "sustainability_cost": round(total_cost + carbon_tax, 2),
        "esg_score":         calculate_esg_score(total_co2),
        "modes":             list(set(route_modes)),
    }


# =====================================================
# RECOMMENDATION (legacy helper)
# =====================================================

def generate_recommendation(current_metrics, optimized_metrics):
    cost_saved = current_metrics["cost"]        - optimized_metrics["cost"]
    co2_saved  = current_metrics["co2"]         - optimized_metrics["co2"]
    tax_saved  = current_metrics["carbon_tax"]  - optimized_metrics["carbon_tax"]
    return {
        "cost_saved":       round(cost_saved, 2),
        "co2_saved":        round(co2_saved, 2),
        "carbon_tax_saved": round(tax_saved, 2),
        "message": (
            f"Cost Saved: ₹{cost_saved:,.0f}\n"
            f"CO₂ Reduced: {co2_saved:,.0f} kg\n"
            f"Carbon Tax Saved: ₹{tax_saved:,.0f}"
        ),
    }


# =====================================================
# FIND ROUTE (alias for balanced — legacy)
# =====================================================

def find_route(G, source, destination):
    return find_balanced_route(G, source, destination)


# =====================================================
# BALANCED ROUTE
# =====================================================

def find_balanced_route(G, source, destination):
    try:
        if isinstance(G, nx.MultiGraph):
            G_simple = nx.Graph()
            for u, v, ed in G.edges(data=True):
                cost_s = ed["distance"] * ed["cost_factor"]
                time_s = ed["distance"] / ed["speed"]
                co2_s  = ed["distance"] * ed["co2_factor"]
                score  = 0.4 * cost_s + 0.3 * time_s + 0.3 * co2_s
                if not G_simple.has_edge(u, v) or G_simple[u][v]["weight"] > score:
                    G_simple.add_edge(u, v, weight=score)
            return nx.shortest_path(G_simple, source, destination, weight="weight")
        return nx.shortest_path(G, source, destination, weight="cost_factor")
    except Exception:
        return []


# =====================================================
# CALCULATE FUEL BREAKDOWN (legacy helper)
# =====================================================

def calculate_fuel_breakdown(route_modes, total_fuel):
    diesel = marine = jet = 0
    for mode in route_modes:
        if mode in ("Road", "Rail"):
            diesel += total_fuel * (0.6 if mode == "Road" else 0.4)
        elif mode == "Sea":
            marine += total_fuel
        elif mode == "Air":
            jet += total_fuel
    return {
        "diesel": round(diesel, 2),
        "marine": round(marine, 2),
        "jet":    round(jet, 2),
    }