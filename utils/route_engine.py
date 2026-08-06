"""
route_engine.py — Dynamic multimodal route engine for RouteIQ
==============================================================

What changed from the static version
--------------------------------------
1. Road distances are now fetched from OSRM automatically (always-on).
   The Excel corridor distance is used only when OSRM fails.

2. Road costs are adjusted by a live diesel-price multiplier so the ₹/km
   figure moves with fuel prices rather than staying fixed forever.

3. Road and Sea ETAs are multiplied by a weather-risk factor fetched from
   Open-Meteo (free, no API key). Bad weather → longer ETA.

4. Sea segment distances use an approximate sailing-lane distance
   (great-circle × lane-deviation factor) instead of the Excel flat value.
   Sea ETAs include port waiting time and slow-steaming optimization.

5. Ocean weather for Sea segments uses Stormglass if an API key is present,
   falls back to Open-Meteo otherwise.

6. discover_route() accepts an optional disrupted_edges list so the UI can
   simulate corridor closures (port shutdown, road blockage, flood).

7. A new dynamic_road_graph_extension() function builds road edges for city
   pairs in the coordinate sheet that are NOT in road_corridors Excel — so
   any two cities with known coordinates become routable by road.

All changes are backward-compatible: the function signatures accepted by
2_Route_Optimization.py are unchanged.
"""

import math
import logging
import pandas as pd
import networkx as nx

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Import dynamic API helpers
# ─────────────────────────────────────────────────────────
try:
    from utils.routing_api import (
        get_road_route,
        get_route_weather_risk,
        get_diesel_cost_multiplier,
        get_sea_route_distance,
        get_ocean_weather_risk,
        get_port_waiting_hours,
        slow_steam_metrics,
        build_dynamic_road_graph_edges,
        INDIAN_PORT_COORDS,
    )
    _ROUTING_API_AVAILABLE = True
except ImportError:
    logger.warning("routing_api not found — dynamic features disabled, using static values only.")
    _ROUTING_API_AVAILABLE = False

    # Stub fallbacks so the rest of the engine never crashes
    def get_road_route(*a, **kw):               return None
    def get_route_weather_risk(*a, **kw):       return {"mult": 1.0, "description": "N/A", "road_mult": 1.0, "sea_mult": 1.0}
    def get_diesel_cost_multiplier(*a, **kw):   return 1.0
    def get_sea_route_distance(*a, **kw):       return None
    def get_ocean_weather_risk(*a, **kw):       return {"sea_mult": 1.0, "description": "N/A"}
    def get_port_waiting_hours(*a, **kw):       return {"waiting_hours": 0, "congestion_level": "Unknown"}
    def slow_steam_metrics(*a, **kw):           return None
    def build_dynamic_road_graph_edges(*a, **kw): return {}
    INDIAN_PORT_COORDS = {}


# =====================================================
# TRANSPORT ASSETS
# =====================================================

TRANSPORT_ASSETS = {
    # ROAD
    "Tata Ace": {
        "mode": "Road", "capacity": 1, "speed": 45,
        "kmpl": 18, "fuel_type": "Diesel", "co2_per_litre": 2.68, "cost_per_km": 12,
    },
    "Pickup Truck": {
        "mode": "Road", "capacity": 3, "speed": 50,
        "kmpl": 12, "fuel_type": "Diesel", "co2_per_litre": 2.68, "cost_per_km": 18,
    },
    "Medium Truck": {
        "mode": "Road", "capacity": 10, "speed": 55,
        "kmpl": 6,  "fuel_type": "Diesel", "co2_per_litre": 2.68, "cost_per_km": 35,
    },
    "Heavy Truck": {
        "mode": "Road", "capacity": 20, "speed": 60,
        "kmpl": 4,  "fuel_type": "Diesel", "co2_per_litre": 2.68, "cost_per_km": 55,
    },
    # RAIL
    "Freight Rail": {
        "mode": "Rail", "capacity": 3000, "speed": 65,
        "fuel_type": "Diesel", "fuel_litre_per_ton_km": 0.004,
        "co2_per_litre": 2.68, "cost_per_ton_km": 0.9,
    },
    "Electric Freight Rail": {
        "mode": "Rail", "capacity": 3000, "speed": 75,
        "fuel_type": "Electric", "co2_per_kwh": 0.7, "cost_per_ton_km": 0.8,
    },
    # SEA
    "Container Ship": {
        "mode": "Sea", "capacity": 50000, "speed": 37,   # km/h (≈20 knots)
        "fuel_type": "Marine Fuel", "fuel_litre_per_ton_km": 0.002,
        "co2_per_litre": 3.11, "cost_per_ton_km": 0.4,
    },
    "Bulk Carrier": {
        "mode": "Sea", "capacity": 120000, "speed": 28,  # km/h (≈15 knots)
        "fuel_type": "Marine Fuel", "fuel_litre_per_ton_km": 0.0015,
        "co2_per_litre": 3.11, "cost_per_ton_km": 0.3,
    },
    # AIR
    "Cargo Aircraft": {
        "mode": "Air", "capacity": 100, "speed": 750,
        "fuel_type": "Jet Fuel", "fuel_litre_per_ton_km": 0.8,
        "co2_per_litre": 2.54, "cost_per_ton_km": 12,
    },
    "Express Air Freight": {
        "mode": "Air", "capacity": 40, "speed": 850,
        "fuel_type": "Jet Fuel", "fuel_litre_per_ton_km": 1.0,
        "co2_per_litre": 2.54, "cost_per_ton_km": 15,
    },
}

BEST_ASSET_FOR = {
    "cheapest": {"Road": "Heavy Truck",           "Rail": "Electric Freight Rail", "Sea": "Bulk Carrier",     "Air": "Cargo Aircraft"},
    "fastest":  {"Road": "Heavy Truck",           "Rail": "Electric Freight Rail", "Sea": "Container Ship",   "Air": "Express Air Freight"},
    "greenest": {"Road": "Heavy Truck",           "Rail": "Electric Freight Rail", "Sea": "Bulk Carrier",     "Air": "Cargo Aircraft"},
}

MODE_TRANSFER_COST = 5000   # ₹ penalty per mode switch
MODE_TRANSFER_TIME = 4      # hrs penalty per mode switch


def get_assets_by_mode(mode: str) -> list:
    return [a for a, info in TRANSPORT_ASSETS.items() if info["mode"] == mode]


# =====================================================
# LOAD DATA
# =====================================================

def load_data(file_path: str) -> dict:
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
# =====================================================

def build_multimodal_graph(data: dict) -> nx.MultiGraph:
    """
    Builds a NetworkX MultiGraph from the Excel corridor sheets.
    Additionally extends road edges using OSRM for any city pair that has
    coordinates but is NOT already in road_corridors — making the road
    graph dynamically connected rather than limited to Excel-defined lanes.
    """
    G = nx.MultiGraph()

    corridor_sheets = {
        "Road": data["road_corridors"],
        "Rail": data["rail_corridors"],
        "Sea":  data["sea_corridors"],
        "Air":  data["air_corridors"],
    }
    transport_modes = data["transport_modes"]

    # ── Add static Excel corridors ────────────────────────
    for mode, table in corridor_sheets.items():
        mode_info = transport_modes[transport_modes["mode"] == mode]
        if mode_info.empty:
            continue
        mode_info   = mode_info.iloc[0]
        source_col  = table.columns[0]
        dest_col    = table.columns[1]

        for _, row in table.iterrows():
            G.add_edge(
                row[source_col],
                row[dest_col],
                distance=row["distance_km"],
                mode=mode,
                cost_factor=mode_info["cost_per_ton_km"],
                speed=mode_info["speed_kmph"],
                co2_factor=mode_info["co2_kg_per_ton_km"],
                handling_cost=mode_info["handling_cost_inr"],
            )

    # ── Extend road graph with OSRM-derived edges ─────────
    # Any two cities that have coordinates but no Excel road corridor
    # between them get a real OSRM-derived road edge added.
    # This means routing is not constrained to pre-defined Excel lanes.
    if _ROUTING_API_AVAILABLE:
        city_coords = get_city_coordinates(data)
        existing_road_pairs = set()
        for u, v, ed in G.edges(data=True):
            if ed.get("mode") == "Road":
                existing_road_pairs.add((min(u, v), max(u, v)))

        road_mode_info = transport_modes[transport_modes["mode"] == "Road"]
        if not road_mode_info.empty:
            rmi = road_mode_info.iloc[0]
            new_edges = build_dynamic_road_graph_edges(city_coords)
            added = 0
            for (city_a, city_b), (dist_km, dur_hr) in new_edges.items():
                pair = (min(city_a, city_b), max(city_a, city_b))
                if pair not in existing_road_pairs:
                    G.add_edge(
                        city_a, city_b,
                        distance=dist_km,
                        mode="Road",
                        cost_factor=rmi["cost_per_ton_km"],
                        speed=dist_km / dur_hr if dur_hr > 0 else 60,
                        co2_factor=rmi["co2_kg_per_ton_km"],
                        handling_cost=rmi["handling_cost_inr"],
                        source="osrm",
                    )
                    added += 1
            if added:
                logger.info("Dynamic road graph: added %d OSRM-derived edges.", added)

    return G


# =====================================================
# SEGMENT METRICS — static base calculation
# =====================================================

def _segment_metrics_base(distance: float, mode: str, asset_name: str, cargo_weight: float) -> tuple:
    """
    Pure static segment calculation (no API calls).
    Returns (cost, eta_hrs, co2_kg, fuel_litres, fuel_type).
    Used internally; dynamic wrappers apply live adjustments on top.
    """
    a         = TRANSPORT_ASSETS[asset_name]
    speed     = a["speed"]
    fuel_type = a["fuel_type"]
    eta       = distance / speed

    if mode == "Road":
        capacity     = a["capacity"]
        num_vehicles = max(1, math.ceil(cargo_weight / capacity))
        utilization  = min(cargo_weight / (num_vehicles * capacity), 1.0)
        eff_kmpl     = a["kmpl"] * (1 - 0.3 * utilization)
        fuel         = (distance / eff_kmpl) * num_vehicles
        co2          = fuel * a["co2_per_litre"]
        cost         = distance * a["cost_per_km"] * num_vehicles

    elif mode == "Rail":
        if fuel_type == "Electric":
            fuel = distance * cargo_weight * 0.002
            co2  = fuel * a.get("co2_per_kwh", 0.7)
            cost = distance * cargo_weight * a["cost_per_ton_km"]
        else:
            capacity    = a["capacity"]
            num_units   = max(1, math.ceil(cargo_weight / capacity))
            utilization = min(cargo_weight / (num_units * capacity), 1.0)
            fuel        = distance * cargo_weight * a["fuel_litre_per_ton_km"] * (1 + 0.15 * utilization)
            co2         = fuel * a["co2_per_litre"]
            cost        = distance * cargo_weight * a["cost_per_ton_km"]

    elif mode == "Sea":
        capacity    = a["capacity"]
        num_units   = max(1, math.ceil(cargo_weight / capacity))
        utilization = min(cargo_weight / (num_units * capacity), 1.0)
        fuel        = distance * cargo_weight * a["fuel_litre_per_ton_km"] * (1 + 0.10 * utilization)
        co2         = fuel * a["co2_per_litre"]
        cost        = distance * cargo_weight * a["cost_per_ton_km"]

    else:  # Air
        capacity    = a["capacity"]
        num_units   = max(1, math.ceil(cargo_weight / capacity))
        utilization = min(cargo_weight / (num_units * capacity), 1.0)
        fuel        = distance * cargo_weight * a["fuel_litre_per_ton_km"] * (1 + 0.40 * utilization)
        co2         = fuel * a["co2_per_litre"]
        cost        = distance * cargo_weight * a["cost_per_ton_km"]

    return cost, eta, co2, fuel, fuel_type


# =====================================================
# SEGMENT METRICS — dynamic (with live adjustments)
# =====================================================

def _segment_metrics(
    distance:         float,
    mode:             str,
    asset_name:       str,
    cargo_weight:     float,
    origin_coords:    tuple = None,   # (lat, lon) of segment start
    dest_coords:      tuple = None,   # (lat, lon) of segment end
    optimize_for:     str   = "balanced",
    origin_unlocode:  str   = "",
    dest_unlocode:    str   = "",
) -> tuple:
    """
    Returns (cost, eta_hrs, co2_kg, fuel_litres, fuel_type) with dynamic
    adjustments applied where coordinates and API responses are available.

    Road: OSRM distance + weather ETA multiplier + diesel price cost multiplier.
    Sea:  Sailing-lane distance + slow steaming + ocean weather + port waiting.
    Rail/Air: static base (no live adjustments — fixed corridors/schedules).
    """
    a         = TRANSPORT_ASSETS[asset_name]
    fuel_type = a["fuel_type"]

    # ── ROAD — live distance + weather + fuel price ──────
    if mode == "Road":
        live_distance = distance
        live_eta      = None

        if _ROUTING_API_AVAILABLE and origin_coords and dest_coords:
            result = get_road_route(
                origin_coords[0], origin_coords[1],
                dest_coords[0],   dest_coords[1],
            )
            if result:
                live_distance, live_eta = result
                logger.debug("OSRM road: %s km in %.2f hr", live_distance, live_eta)

        cost, eta, co2, fuel, _ = _segment_metrics_base(
            live_distance, mode, asset_name, cargo_weight
        )

        # Replace ETA with OSRM duration if available (more accurate)
        if live_eta is not None:
            eta = live_eta

        # Apply diesel price multiplier to cost
        if _ROUTING_API_AVAILABLE:
            diesel_mult = get_diesel_cost_multiplier()
            cost = cost * diesel_mult

        # Apply weather risk to ETA
        if _ROUTING_API_AVAILABLE and origin_coords and dest_coords:
            weather = get_route_weather_risk(
                origin_coords[0], origin_coords[1],
                dest_coords[0],   dest_coords[1],
                mode="Road",
            )
            eta  = eta  * weather["road_mult"]
            # Weather also increases fuel (engine works harder in rain/fog)
            fuel = fuel * (1 + (weather["road_mult"] - 1) * 0.4)
            co2  = fuel * a["co2_per_litre"]

        return cost, eta, co2, fuel, fuel_type

    # ── SEA — sailing distance + slow steam + weather + port ──
    elif mode == "Sea":
        # Get sailing-lane-adjusted distance
        sea_dist = distance   # fallback to static Excel value
        if _ROUTING_API_AVAILABLE and origin_coords and dest_coords:
            sea_data = get_sea_route_distance(
                origin_coords[0], origin_coords[1],
                dest_coords[0],   dest_coords[1],
                origin_unlocode=origin_unlocode,
                dest_unlocode=dest_unlocode,
            )
            if sea_data:
                sea_dist = sea_data["distance_km"]

        # Base metrics at full speed
        cost_base, _eta_base, co2_base, fuel_base, _ = _segment_metrics_base(
            sea_dist, mode, asset_name, cargo_weight
        )

        # Apply slow steaming optimization
        if _ROUTING_API_AVAILABLE:
            ss = slow_steam_metrics(
                distance_km    = sea_dist,
                base_speed_kmh = a["speed"],
                base_fuel_ltrs = fuel_base,
                base_co2_kg    = co2_base,
                base_cost      = cost_base,
                optimize_for   = optimize_for,
            )
            if ss:
                fuel = ss["fuel"]
                co2  = ss["co2"]
                eta  = ss["eta_hr"]
                cost = ss["cost"]
            else:
                fuel, co2, eta, cost = fuel_base, co2_base, _eta_base, cost_base
        else:
            fuel, co2, eta, cost = fuel_base, co2_base, _eta_base, cost_base

        # Apply ocean weather multiplier (midpoint of route)
        if _ROUTING_API_AVAILABLE and origin_coords and dest_coords:
            mid_lat = (origin_coords[0] + dest_coords[0]) / 2
            mid_lon = (origin_coords[1] + dest_coords[1]) / 2
            ocean_wx = get_ocean_weather_risk(mid_lat, mid_lon)
            sea_mult = ocean_wx["sea_mult"]
            eta  = eta  * sea_mult
            fuel = fuel * (1 + (sea_mult - 1) * 0.6)
            co2  = fuel * a["co2_per_litre"]

        # Add destination port waiting time
        if _ROUTING_API_AVAILABLE and dest_unlocode:
            port_info = get_port_waiting_hours(dest_unlocode)
            eta += port_info["waiting_hours"]

        return cost, eta, co2, fuel, fuel_type

    # ── RAIL / AIR — static base only (fixed scheduled corridors) ──
    else:
        return _segment_metrics_base(distance, mode, asset_name, cargo_weight)


# =====================================================
# ASSET SELECTION
# =====================================================

def select_best_asset_for_weight(mode: str, cargo_weight: float, objective: str) -> str:
    """Selects the best asset for a given mode, weight, and objective."""
    candidates = get_assets_by_mode(mode)
    if not candidates:
        return None

    best_asset = None
    best_score = float("inf")

    for asset_name in candidates:
        try:
            cost, eta, co2, fuel, _ = _segment_metrics_base(1.0, mode, asset_name, cargo_weight)
        except Exception as e:
            logger.warning("Asset eval failed for %s/%s: %s", asset_name, mode, e)
            continue

        if objective == "cheapest":
            score = cost
        elif objective == "fastest":
            score = 1.0 / TRANSPORT_ASSETS[asset_name]["speed"]
        else:  # greenest
            score = co2

        if score < best_score:
            best_score = score
            best_asset = asset_name

    return best_asset or BEST_ASSET_FOR.get(objective, {}).get(mode)


def get_default_asset(mode: str) -> str:
    defaults = {
        "Road": "Medium Truck",
        "Rail": "Freight Rail",
        "Sea":  "Container Ship",
        "Air":  "Cargo Aircraft",
    }
    return defaults.get(mode, "Medium Truck")


# =====================================================
# CORRIDOR AVAILABILITY
# =====================================================

def _build_corridor_availability(data: dict) -> dict:
    """Returns {(min_city, max_city): set_of_modes} from Excel sheets."""
    availability = {}
    sheets = {
        "Road": data["road_corridors"],
        "Rail": data["rail_corridors"],
        "Sea":  data["sea_corridors"],
        "Air":  data["air_corridors"],
    }
    for mode, table in sheets.items():
        src_col = table.columns[0]
        dst_col = table.columns[1]
        for _, row in table.iterrows():
            pair = (min(row[src_col], row[dst_col]), max(row[src_col], row[dst_col]))
            availability.setdefault(pair, set()).add(mode)
    return availability


# =====================================================
# GRAPH BUILDERS FOR PATH-FINDING
# =====================================================

def _build_optimized_graph(
    data: dict,
    G_multi: nx.MultiGraph,
    objective: str,
    cargo_weight: float,
    city_coords: dict = None,
    use_live_routing: bool = False,
) -> nx.Graph:
    """
    Collapses MultiGraph to simple Graph with best weight per edge for
    the given objective.

    By default uses static base metrics only (fast, no API calls) since
    this is called during path-finding which may evaluate many edges.

    If use_live_routing=True and city_coords is provided, edge metrics are
    computed via _segment_metrics() instead — i.e. Road edges use live OSRM
    distance/ETA + diesel price + weather, and Sea edges use sailing-lane
    distance + slow steaming + ocean weather + port waiting. This means the
    CHEAPEST/FASTEST/GREENEST path itself (not just its reported numbers)
    can shift based on live conditions. Rail/Air are unaffected either way
    (fixed scheduled corridors).
    """
    G_opt               = nx.Graph()
    corridor_availability = _build_corridor_availability(data)
    processed           = set()

    for u, v, edge_data in G_multi.edges(data=True):
        pair = (min(u, v), max(u, v))
        if pair in processed:
            continue
        processed.add(pair)

        distance        = edge_data["distance"]
        available_modes = corridor_availability.get(pair, set())
        if not available_modes:
            # Include the mode from the edge even if not in Excel corridors (e.g. OSRM-derived)
            available_modes = {edge_data.get("mode", "Road")}

        origin_coords = city_coords.get(u) if (use_live_routing and city_coords) else None
        dest_coords   = city_coords.get(v) if (use_live_routing and city_coords) else None
        live_ok       = use_live_routing and origin_coords and dest_coords

        best_weight = float("inf")
        best_mode   = None
        best_asset  = None

        for mode in available_modes:
            asset = select_best_asset_for_weight(mode, cargo_weight, objective)
            if asset is None:
                continue
            try:
                if live_ok:
                    cost, eta, co2, fuel, _ = _segment_metrics(
                        distance, mode, asset, cargo_weight,
                        origin_coords=origin_coords, dest_coords=dest_coords,
                        optimize_for=objective,
                    )
                else:
                    cost, eta, co2, fuel, _ = _segment_metrics_base(distance, mode, asset, cargo_weight)
            except Exception as e:
                logger.warning("Metrics failed for %s->%s via %s/%s: %s", u, v, mode, asset, e)
                continue

            w = cost if objective == "cheapest" else (eta if objective == "fastest" else co2)

            if w < best_weight:
                best_weight = w
                best_mode   = mode
                best_asset  = asset

        if best_mode is not None:
            G_opt.add_edge(u, v, weight=best_weight, distance=distance, mode=best_mode, asset=best_asset)

    return G_opt


def _build_balanced_graph(data: dict, G_multi: nx.MultiGraph, cargo_weight: float, weights: dict = None) -> nx.Graph:
    """
    Balanced multi-objective graph: each edge weight is a normalized
    combination of cost + ETA + CO2 so discover_route() optimizes the
    city sequence jointly with mode/asset selection.
    """
    weights               = weights or {"cost": 0.34, "eta": 0.33, "co2": 0.33}
    corridor_availability = _build_corridor_availability(data)
    G_bal                 = nx.Graph()
    processed             = set()

    for u, v, edge_data in G_multi.edges(data=True):
        pair = (min(u, v), max(u, v))
        if pair in processed:
            continue
        processed.add(pair)

        distance        = edge_data["distance"]
        available_modes = corridor_availability.get(pair, set()) or {edge_data.get("mode", "Road")}

        options = []
        for mode in available_modes:
            seen_assets = set()
            for target in ("cheapest", "fastest", "greenest"):
                asset = select_best_asset_for_weight(mode, cargo_weight, target)
                if not asset or asset in seen_assets:
                    continue
                seen_assets.add(asset)
                try:
                    cost, eta, co2, fuel, _ = _segment_metrics_base(distance, mode, asset, cargo_weight)
                    options.append((mode, asset, cost, eta, co2))
                except Exception as e:
                    logger.warning("Balanced graph metrics failed for %s->%s via %s/%s: %s", u, v, mode, asset, e)

        if not options:
            continue

        costs = [o[2] for o in options]
        etas  = [o[3] for o in options]
        co2s  = [o[4] for o in options]

        def _norm(val, lst):
            lo, hi = min(lst), max(lst)
            return 0.0 if hi == lo else (val - lo) / (hi - lo)

        best_score = float("inf")
        best       = None
        for mode, asset, cost, eta, co2 in options:
            score = (
                weights["cost"] * _norm(cost, costs)
                + weights["eta"] * _norm(eta, etas)
                + weights["co2"] * _norm(co2, co2s)
            )
            if score < best_score:
                best_score = score
                best       = (mode, asset, cost, eta, co2)

        mode, asset, cost, eta, co2 = best
        G_bal.add_edge(u, v, weight=best_score, distance=distance, mode=mode, asset=asset)

    return G_bal


# =====================================================
# ROUTE FINDERS
# =====================================================

def discover_route(
    G:               nx.MultiGraph,
    source:          str,
    destination:     str,
    data:            dict = None,
    cargo_weight:    float = 1,
    weights:         dict  = None,
    disrupted_edges: list  = None,
) -> list:
    """
    Finds the best city sequence from source to destination.

    disrupted_edges: list of (city_a, city_b) tuples to exclude from
    routing — simulates corridor closures, port shutdowns, or road blocks.
    Example: [("Mumbai", "Pune"), ("Chennai", "Vizag")]
    """
    G_work = G.copy()

    # Remove disrupted edges before path-finding
    if disrupted_edges:
        for city_a, city_b in disrupted_edges:
            # Remove all edges between the pair (all modes)
            while G_work.has_edge(city_a, city_b):
                keys = list(G_work[city_a][city_b].keys())
                if keys:
                    G_work.remove_edge(city_a, city_b, key=keys[0])
                else:
                    break
        logger.info("Disruption: removed %d corridor(s) from graph.", len(disrupted_edges))

    if data is not None:
        try:
            G_bal = _build_balanced_graph(data, G_work, cargo_weight, weights)
            if G_bal.has_node(source) and G_bal.has_node(destination):
                return nx.shortest_path(G_bal, source, destination, weight="weight")
        except Exception as e:
            logger.warning(
                "Balanced route discovery failed for %s -> %s (%s); falling back to distance-only.",
                source, destination, e,
            )

    # Distance-only fallback
    try:
        if isinstance(G_work, nx.MultiGraph):
            G_simple = nx.Graph()
            for u, v, ed in G_work.edges(data=True):
                dist = ed["distance"]
                if G_simple.has_edge(u, v):
                    if G_simple[u][v]["distance"] > dist:
                        G_simple[u][v]["distance"] = dist
                else:
                    G_simple.add_edge(u, v, distance=dist)
            return nx.shortest_path(G_simple, source, destination, weight="distance")
        return nx.shortest_path(G_work, source, destination, weight="distance")
    except Exception as e:
        logger.warning("Distance-only fallback failed for %s -> %s: %s", source, destination, e)
        return []


def find_cheapest_route(G, source, destination, data=None, cargo_weight=1,
                         city_coords=None, use_live_routing=False):
    if data is not None:
        G_opt = _build_optimized_graph(data, G, "cheapest", cargo_weight,
                                        city_coords=city_coords, use_live_routing=use_live_routing)
        try:
            return nx.shortest_path(G_opt, source, destination, weight="weight")
        except Exception as e:
            logger.warning("Optimized cheapest route failed (%s -> %s): %s", source, destination, e)
    try:
        return nx.shortest_path(G, source, destination, weight="cost_factor")
    except Exception as e:
        logger.warning("Fallback cheapest route failed (%s -> %s): %s", source, destination, e)
        return []


def find_fastest_route(G, source, destination, data=None, cargo_weight=1,
                        city_coords=None, use_live_routing=False):
    if data is not None:
        G_opt = _build_optimized_graph(data, G, "fastest", cargo_weight,
                                        city_coords=city_coords, use_live_routing=use_live_routing)
        try:
            return nx.shortest_path(G_opt, source, destination, weight="weight")
        except Exception as e:
            logger.warning("Optimized fastest route failed (%s -> %s): %s", source, destination, e)
    try:
        return nx.shortest_path(
            G, source, destination,
            weight=lambda u, v, d: d["distance"] / d["speed"],
        )
    except Exception as e:
        logger.warning("Fallback fastest route failed (%s -> %s): %s", source, destination, e)
        return []


def find_greenest_route(G, source, destination, data=None, cargo_weight=1,
                         city_coords=None, use_live_routing=False):
    if data is not None:
        G_opt = _build_optimized_graph(data, G, "greenest", cargo_weight,
                                        city_coords=city_coords, use_live_routing=use_live_routing)
        try:
            return nx.shortest_path(G_opt, source, destination, weight="weight")
        except Exception as e:
            logger.warning("Optimized greenest route failed (%s -> %s): %s", source, destination, e)
    try:
        return nx.shortest_path(G, source, destination, weight="co2_factor")
    except Exception as e:
        logger.warning("Fallback greenest route failed (%s -> %s): %s", source, destination, e)
        return []


# =====================================================
# AUTO SELECTION (mode + asset per segment)
# =====================================================

def build_auto_selection(G, route, objective="cheapest", data=None, cargo_weight=1,
                          city_coords=None, use_live_routing=False):
    """For each segment in route, pick the best mode+asset for the given objective.

    If use_live_routing=True and city_coords is provided, Road/Sea segments are
    scored using live-adjusted metrics (_segment_metrics) instead of static
    base metrics, so the mode/asset choice reflects current conditions.
    """
    selections            = {}
    corridor_availability = _build_corridor_availability(data) if data else {}

    for i in range(len(route) - 1):
        u, v = route[i], route[i + 1]

        try:
            if isinstance(G, nx.MultiGraph):
                edge_data = list(G[u][v].values())[0]
            else:
                edge_data = G[u][v]
            distance = edge_data["distance"]
        except Exception:
            distance = 500  # fallback

        pair            = (min(u, v), max(u, v))
        available_modes = corridor_availability.get(pair, set())
        if not available_modes:
            try:
                fallback_mode = list(G[u][v].values())[0]["mode"] if isinstance(G, nx.MultiGraph) else G[u][v]["mode"]
            except Exception:
                fallback_mode = "Road"
            available_modes = {fallback_mode}

        origin_coords = city_coords.get(u) if (use_live_routing and city_coords) else None
        dest_coords   = city_coords.get(v) if (use_live_routing and city_coords) else None
        live_ok       = use_live_routing and origin_coords and dest_coords

        best_weight = float("inf")
        best_mode   = None
        best_asset  = None

        for mode in available_modes:
            asset = select_best_asset_for_weight(mode, cargo_weight, objective)
            if asset is None:
                continue
            try:
                if live_ok:
                    cost, eta, co2, fuel, _ = _segment_metrics(
                        distance, mode, asset, cargo_weight,
                        origin_coords=origin_coords, dest_coords=dest_coords,
                        optimize_for=objective,
                    )
                else:
                    cost, eta, co2, fuel, _ = _segment_metrics_base(distance, mode, asset, cargo_weight)
            except Exception:
                continue
            w = cost if objective == "cheapest" else (eta if objective == "fastest" else co2)
            if w < best_weight:
                best_weight = w
                best_mode   = mode
                best_asset  = asset

        if best_mode is None:
            best_mode  = list(available_modes)[0]
            best_asset = select_best_asset_for_weight(best_mode, cargo_weight, objective) or get_default_asset(best_mode)

        selections[(u, v)] = {"mode": best_mode, "asset": best_asset}

    return selections


# =====================================================
# CALCULATE CUSTOM ROUTE — dynamic version
# =====================================================

def calculate_custom_route(
    G,
    route,
    selected_modes,
    cargo_weight,
    city_coords=None,
    use_live_routing=True,       # now defaults to True (always-on)
    optimize_for="balanced",
):
    """
    Computes full route metrics with dynamic adjustments:
    - Road: OSRM distance/ETA + weather multiplier + diesel cost multiplier
    - Sea: sailing-lane distance + slow steaming + ocean weather + port waiting
    - Rail/Air: static base metrics (fixed schedules)

    use_live_routing is kept as a parameter for backward compatibility but
    now defaults to True. Set False only to force static-only mode (testing).
    """
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
    live_segments  = 0

    # Segment-level detail for transparency (shown in UI)
    segment_details = []

    if city_coords is None and _ROUTING_API_AVAILABLE:
        # Caller didn't pass coords — we can't do live lookups this run
        use_live_routing = False

    for i in range(len(route) - 1):
        u, v = route[i], route[i + 1]

        # ── Get static distance from graph ────────────────
        try:
            if isinstance(G, nx.MultiGraph):
                seg_info    = selected_modes.get((u, v), {})
                chosen_mode = seg_info.get("mode", "Road")
                edge_data   = None
                for k, ed in G[u][v].items():
                    if ed["mode"] == chosen_mode:
                        edge_data = ed
                        break
                if edge_data is None:
                    edge_data = list(G[u][v].values())[0]
            else:
                edge_data = G[u][v]
            static_distance = edge_data["distance"]
        except Exception:
            static_distance = 500

        seg_info   = selected_modes.get((u, v), {})
        mode       = seg_info.get("mode", "Road")
        asset_name = seg_info.get("asset", get_default_asset(mode))

        # ── Resolve coordinates for this segment ──────────
        origin_coords = city_coords.get(u) if city_coords else None
        dest_coords   = city_coords.get(v) if city_coords else None

        # ── Resolve port UNLOCODEs if sea segment ─────────
        # Map city name → UNLOCODE using known Indian port list
        origin_unlocode = ""
        dest_unlocode   = ""
        if mode == "Sea" and _ROUTING_API_AVAILABLE:
            city_to_unlocode = {v: k for k, v in {
                "Mumbai":       "INNSA",
                "Nhava Sheva":  "INNSA",
                "Mundra":       "INMUN",
                "Chennai":      "INMAA",
                "Kolkata":      "INCCU",
                "Haldia":       "INCCU",
                "Visakhapatnam":"INVTZ",
                "Vizag":        "INVTZ",
                "Cochin":       "INCOK",
                "Kochi":        "INCOK",
                "Kandla":       "INKLA",
                "Pipavav":      "INPAV",
            }.items()}
            origin_unlocode = city_to_unlocode.get(u, "")
            dest_unlocode   = city_to_unlocode.get(v, "")

        # ── Calculate segment metrics (dynamic) ───────────
        if use_live_routing and _ROUTING_API_AVAILABLE:
            cost, eta, co2, fuel, fuel_type = _segment_metrics(
                static_distance,
                mode,
                asset_name,
                cargo_weight,
                origin_coords   = origin_coords,
                dest_coords     = dest_coords,
                optimize_for    = optimize_for,
                origin_unlocode = origin_unlocode,
                dest_unlocode   = dest_unlocode,
            )
            if mode == "Road" and origin_coords and dest_coords:
                osrm_result = get_road_route(
                    origin_coords[0], origin_coords[1],
                    dest_coords[0],   dest_coords[1],
                )
                if osrm_result:
                    live_segments += 1
        else:
            cost, eta, co2, fuel, fuel_type = _segment_metrics_base(
                static_distance, mode, asset_name, cargo_weight
            )

        # ── Mode transfer penalty ─────────────────────────
        if prev_mode and prev_mode != mode:
            total_cost += MODE_TRANSFER_COST
            total_eta  += MODE_TRANSFER_TIME

        total_distance += static_distance
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

        segment_details.append({
            "from":       u,
            "to":         v,
            "mode":       mode,
            "asset":      asset_name,
            "distance":   round(static_distance, 1),
            "cost":       round(cost, 0),
            "eta_hr":     round(eta, 2),
            "co2_kg":     round(co2, 1),
            "fuel_ltrs":  round(fuel, 1),
        })

    carbon_tax = total_co2 * 5

    return {
        "distance":       round(total_distance, 2),
        "cost":           round(total_cost, 2),
        "eta":            round(total_eta, 2),
        "co2":            round(total_co2, 2),
        "carbon_tax":     round(carbon_tax, 2),
        "diesel":         round(diesel, 2),
        "marine":         round(marine, 2),
        "jet":            round(jet, 2),
        "fuel":           round(total_fuel, 2),
        "modes":          route_modes,
        "live_segments":  live_segments,
        "segment_details": segment_details,
    }


# =====================================================
# HELPER FUNCTIONS (unchanged public API)
# =====================================================

def build_route_segments(route: list) -> list:
    return [{"from": route[i], "to": route[i + 1]} for i in range(len(route) - 1)]


def get_segment_modes(data: dict, source: str, destination: str) -> list:
    modes       = []
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
            if (row[src_col] == source and row[dst_col] == destination) or \
               (row[src_col] == destination and row[dst_col] == source):
                modes.append(mode)
                break
    # Always offer all 4 modes; metrics are calculated from TRANSPORT_ASSETS
    for m in ["Road", "Rail", "Sea", "Air"]:
        if m not in modes:
            modes.append(m)
    return modes


def get_city_coordinates(data: dict) -> dict:
    coords = {}
    for _, row in data["city_coordinates"].iterrows():
        coords[row["city"]] = (row["latitude"], row["longitude"])
    return coords


def get_available_modes() -> list:
    return ["Road", "Rail", "Sea", "Air"]


def calculate_esg_score(co2: float) -> int:
    if co2 <= 500:   return 95
    if co2 <= 1000:  return 85
    if co2 <= 2000:  return 75
    if co2 <= 4000:  return 65
    return 50


def build_strategy_plan(route: list, selections: dict) -> list:
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
# LEGACY HELPERS (kept for backward compatibility)
# =====================================================

def calculate_route_metrics(G, route, cargo_weight):
    """Uses graph edge data directly. Kept for other pages."""
    total_distance = 0
    total_cost     = 0
    total_eta      = 0
    total_co2      = 0
    route_modes    = []
    prev_mode      = None

    for i in range(len(route) - 1):
        try:
            edge = list(G[route[i]][route[i+1]].values())[0] if isinstance(G, nx.MultiGraph) else G[route[i]][route[i+1]]
        except Exception as e:
            logger.warning("No edge for %s -> %s (%s); skipping.", route[i], route[i+1], e)
            continue

        distance      = edge["distance"]
        speed         = edge["speed"]
        mode          = edge["mode"]
        cost_factor   = edge["cost_factor"]
        co2_factor    = edge["co2_factor"]
        handling_cost = edge["handling_cost"]

        if prev_mode and prev_mode != mode:
            total_cost += MODE_TRANSFER_COST
            total_eta  += MODE_TRANSFER_TIME

        total_distance += distance
        total_cost     += distance * cargo_weight * cost_factor + handling_cost
        total_eta      += distance / speed
        total_co2      += distance * cargo_weight * co2_factor
        route_modes.append(mode)
        prev_mode = mode

    DIESEL_CO2 = 2.68
    total_fuel = total_co2 / DIESEL_CO2
    carbon_tax = total_co2 * 5

    return {
        "distance":           round(total_distance, 2),
        "cost":               round(total_cost, 2),
        "eta":                round(total_eta, 2),
        "co2":                round(total_co2, 2),
        "fuel":               round(total_fuel, 2),
        "carbon_tax":         round(carbon_tax, 2),
        "sustainability_cost": round(total_cost + carbon_tax, 2),
        "esg_score":          calculate_esg_score(total_co2),
        "modes":              list(set(route_modes)),
    }


def generate_recommendation(current_metrics, optimized_metrics):
    cost_saved = current_metrics["cost"]       - optimized_metrics["cost"]
    co2_saved  = current_metrics["co2"]        - optimized_metrics["co2"]
    tax_saved  = current_metrics["carbon_tax"] - optimized_metrics["carbon_tax"]
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


def find_route(G, source, destination):
    return find_balanced_route(G, source, destination)


def find_balanced_route(G, source, destination):
    try:
        if isinstance(G, nx.MultiGraph):
            G_simple = nx.Graph()
            for u, v, ed in G.edges(data=True):
                score = 0.4 * ed["distance"] * ed["cost_factor"] \
                      + 0.3 * ed["distance"] / ed["speed"] \
                      + 0.3 * ed["distance"] * ed["co2_factor"]
                if not G_simple.has_edge(u, v) or G_simple[u][v]["weight"] > score:
                    G_simple.add_edge(u, v, weight=score)
            return nx.shortest_path(G_simple, source, destination, weight="weight")
        return nx.shortest_path(G, source, destination, weight="cost_factor")
    except Exception as e:
        logger.warning("Balanced route failed (%s -> %s): %s", source, destination, e)
        return []


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