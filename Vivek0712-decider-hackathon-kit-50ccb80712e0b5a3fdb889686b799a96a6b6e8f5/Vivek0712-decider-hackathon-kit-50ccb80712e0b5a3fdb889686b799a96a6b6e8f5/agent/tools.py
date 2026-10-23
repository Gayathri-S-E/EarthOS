"""EarthOS investigation tools — four specialist probes for environmental emergencies.

Each tool investigates one dimension of a planetary crisis.  Data is synthetic and
deterministic so the demo, tests, and benchmark all run offline without any external API.

Tool docstrings are read by the #tool-selection pattern as option descriptions; keep them
concise, factual, and domain-specific.

Three canonical scenarios (used by the demo, eval cases, and tests):
  urban_heatwave        — extreme urban heat event in a major city
  water_shortage        — metropolitan water-supply failure approaching Day Zero
  renewable_energy_gap  — renewable-generation shortfall threatening grid stability
"""

from __future__ import annotations

from strands import tool

# ---------------------------------------------------------------------------
# Synthetic scenario database — deterministic, no external calls needed
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, dict] = {
    # ---- Scenario 1: Urban heatwave ----------------------------------------
    "urban_heatwave": {
        "type": "heatwave",
        "label": "Urban Heatwave",
        "region": "Phoenix Metro Area, Arizona, USA",
        "max_temp_c": 47.8,
        "wet_bulb_temp_c": 33.2,
        "duration_days": 7,
        "heat_index": "extreme",
        "population_at_risk": 1_650_000,
        "vulnerable_population": 210_000,   # elderly, children, outdoor workers
        "cooling_centres_open": 18,
        "cooling_centres_capacity": 9_000,
        "heat_related_er_visits_24h": 412,
        "heat_related_deaths_confirmed": 6,
        "urban_heat_island_delta_c": 4.1,   # city hotter than surroundings
        "power_grid_strain_pct": 94,        # grid at 94 % of peak capacity
    },
    # ---- Scenario 2: Water shortage ----------------------------------------
    "water_shortage": {
        "type": "water_shortage",
        "label": "Metropolitan Water Shortage",
        "region": "Greater Chennai, Tamil Nadu, India",
        "reservoir_level_pct": 14.7,
        "daily_demand_ML": 870,
        "daily_supply_ML": 620,
        "deficit_ML_per_day": 250,
        "groundwater_depth_m": 58.3,
        "months_to_day_zero": 1.9,
        "water_quality_ok": True,
        "tanker_trucks_deployed": 340,
        "districts_on_rationing": 8,
        "total_districts": 15,
        "estimated_affected_population": 3_800_000,
    },
    # ---- Scenario 3: Renewable-energy gap ----------------------------------
    "renewable_energy_gap": {
        "type": "energy_shortfall",
        "label": "Renewable Energy Shortfall",
        "region": "UK National Grid",
        "grid_demand_GW": 52.4,
        "renewable_output_GW": 21.7,
        "gas_peaker_output_GW": 18.3,
        "nuclear_output_GW": 5.8,
        "total_supply_GW": 45.8,
        "supply_deficit_GW": 6.6,
        "gas_storage_pct": 27.0,
        "rolling_blackout_risk": "high",
        "solar_irradiance_pct_normal": 38,
        "wind_capacity_factor_pct": 19,
        "interconnector_import_available_GW": 2.1,
        "demand_response_available_GW": 1.8,
    },
}

# ---------------------------------------------------------------------------
# Investigation tools
# ---------------------------------------------------------------------------


@tool
def check_heat_cooling_risk(scenario_id: str) -> dict:
    """Assess heat stress and cooling capacity: returns wet-bulb temperature, vulnerable population, ER visit rate, and cooling-centre headroom."""
    data = SCENARIOS.get(scenario_id)
    if not data:
        return {"error": f"unknown scenario '{scenario_id}'. Known: {list(SCENARIOS)}"}
    if data["type"] != "heatwave":
        return {
            "error": f"scenario '{scenario_id}' is type '{data['type']}'; use the right tool",
            "hint": "try check_water_reserves or check_energy_capacity",
        }
    capacity_gap = data["cooling_centres_capacity"] - data["vulnerable_population"]
    er_rate_per_100k = round(data["heat_related_er_visits_24h"] / data["population_at_risk"] * 100_000, 1)
    return {
        "scenario_id": scenario_id,
        "investigation": "heat_cooling_risk",
        "region": data["region"],
        "max_temp_c": data["max_temp_c"],
        "wet_bulb_temp_c": data["wet_bulb_temp_c"],
        "duration_days": data["duration_days"],
        "heat_index": data["heat_index"],
        "population_at_risk": data["population_at_risk"],
        "vulnerable_population": data["vulnerable_population"],
        "cooling_centre_capacity": data["cooling_centres_capacity"],
        "cooling_centre_deficit": max(0, -capacity_gap),
        "er_visits_24h": data["heat_related_er_visits_24h"],
        "er_rate_per_100k": er_rate_per_100k,
        "confirmed_deaths": data["heat_related_deaths_confirmed"],
        "urban_heat_island_delta_c": data["urban_heat_island_delta_c"],
        "power_grid_strain_pct": data["power_grid_strain_pct"],
        "severity": "critical" if data["wet_bulb_temp_c"] > 32 else "high",
        "evidence_complete": True,
    }


@tool
def check_water_reserves(scenario_id: str) -> dict:
    """Assess water-supply status: returns reservoir level, daily deficit, groundwater depth, days to Day Zero, and rationing coverage."""
    data = SCENARIOS.get(scenario_id)
    if not data:
        return {"error": f"unknown scenario '{scenario_id}'. Known: {list(SCENARIOS)}"}
    if data["type"] != "water_shortage":
        return {
            "error": f"scenario '{scenario_id}' is type '{data['type']}'; use the right tool",
            "hint": "try check_heat_cooling_risk or check_energy_capacity",
        }
    days_to_zero = round(data["months_to_day_zero"] * 30.4)
    rationing_coverage_pct = round(data["districts_on_rationing"] / data["total_districts"] * 100)
    return {
        "scenario_id": scenario_id,
        "investigation": "water_reserves",
        "region": data["region"],
        "reservoir_level_pct": data["reservoir_level_pct"],
        "daily_demand_ML": data["daily_demand_ML"],
        "daily_supply_ML": data["daily_supply_ML"],
        "deficit_ML_per_day": data["deficit_ML_per_day"],
        "groundwater_depth_m": data["groundwater_depth_m"],
        "days_to_day_zero": days_to_zero,
        "months_to_day_zero": data["months_to_day_zero"],
        "water_quality_ok": data["water_quality_ok"],
        "tanker_trucks_deployed": data["tanker_trucks_deployed"],
        "rationing_coverage_pct": rationing_coverage_pct,
        "affected_population": data["estimated_affected_population"],
        "severity": "critical" if data["reservoir_level_pct"] < 15 else "high",
        "evidence_complete": True,
    }


@tool
def check_energy_capacity(scenario_id: str) -> dict:
    """Assess grid supply-demand balance: returns generation gap, storage levels, blackout risk, and available demand-response headroom."""
    data = SCENARIOS.get(scenario_id)
    if not data:
        return {"error": f"unknown scenario '{scenario_id}'. Known: {list(SCENARIOS)}"}
    if data["type"] != "energy_shortfall":
        return {
            "error": f"scenario '{scenario_id}' is type '{data['type']}'; use the right tool",
            "hint": "try check_heat_cooling_risk or check_water_reserves",
        }
    gap = round(data["supply_deficit_GW"], 2)
    flex_available = round(data["interconnector_import_available_GW"] + data["demand_response_available_GW"], 2)
    unmet_after_flex = round(max(0.0, gap - flex_available), 2)
    return {
        "scenario_id": scenario_id,
        "investigation": "energy_capacity",
        "region": data["region"],
        "grid_demand_GW": data["grid_demand_GW"],
        "total_supply_GW": data["total_supply_GW"],
        "supply_deficit_GW": gap,
        "renewable_output_GW": data["renewable_output_GW"],
        "gas_storage_pct": data["gas_storage_pct"],
        "rolling_blackout_risk": data["rolling_blackout_risk"],
        "solar_irradiance_pct_normal": data["solar_irradiance_pct_normal"],
        "wind_capacity_factor_pct": data["wind_capacity_factor_pct"],
        "flex_resources_available_GW": flex_available,
        "unmet_after_flexibility_GW": unmet_after_flex,
        "severity": "critical" if unmet_after_flex > 0 else "high",
        "evidence_complete": True,
    }


@tool
def check_data_quality(scenario_id: str) -> dict:
    """Check data availability and sensor quality for an unknown or ambiguous emergency scenario; returns what is known and what data is missing."""
    known = scenario_id in SCENARIOS
    data = SCENARIOS.get(scenario_id, {})
    return {
        "scenario_id": scenario_id,
        "investigation": "data_quality",
        "found_in_database": known,
        "scenario_type": data.get("type", "unknown"),
        "scenario_label": data.get("label", "unclassified"),
        "available_scenario_ids": list(SCENARIOS),
        "missing_sensor_types": (
            [] if known else
            ["temperature_sensors", "water_level_gauges", "grid_telemetry", "population_registry"]
        ),
        "data_completeness_pct": 100 if known else 0,
        "recommended_next_step": (
            f"Run the appropriate specialist tool for type '{data['type']}'" if known
            else "Dispatch field assessment team; request baseline sensor readings"
        ),
        "evidence_complete": known,   # complete only when we know the scenario type
    }


# Ordered list used by TOOLS and the #tool-selection pattern
TOOLS = [
    check_heat_cooling_risk,
    check_water_reserves,
    check_energy_capacity,
    check_data_quality,
]
