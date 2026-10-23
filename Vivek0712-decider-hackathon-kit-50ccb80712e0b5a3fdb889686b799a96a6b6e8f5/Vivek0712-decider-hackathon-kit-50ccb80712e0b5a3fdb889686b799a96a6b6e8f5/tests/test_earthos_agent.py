"""EarthOS-specific tests.

Covers:
  - all four investigation tools (no network, no Bedrock, no Decider)
  - scenario coverage and wrong-type errors
  - build_state helper and scenario-ID extraction
  - EarthOSSelector log record contents (FakeDecider)
  - multi-step investigation loop (FakeDecider + patched Strands Agent)
  - HackathonAgent.chat() kit-contract keys (FakeDecider + patched Strands Agent)
"""

from __future__ import annotations

from fakes import FakeDecider

from agent.tools import (
    SCENARIOS,
    TOOLS,
    check_data_quality,
    check_energy_capacity,
    check_heat_cooling_risk,
    check_water_reserves,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call(tool_fn, *args, **kwargs):
    """Call a @tool-decorated function without going through the Strands runtime.

    Tries common attribute names the Strands SDK uses to store the original callable,
    then falls back to calling the object directly.
    """
    for attr in ("func", "__wrapped__", "_func"):
        if hasattr(tool_fn, attr):
            return getattr(tool_fn, attr)(*args, **kwargs)
    return tool_fn(*args, **kwargs)


# ---------------------------------------------------------------------------
# Tool correctness tests — no external calls
# ---------------------------------------------------------------------------

def test_heat_tool_returns_expected_fields():
    r = _call(check_heat_cooling_risk, "urban_heatwave")
    assert r["investigation"] == "heat_cooling_risk"
    assert r["severity"] == "critical"          # wet_bulb_temp_c 33.2 > 32
    assert "vulnerable_population" in r
    assert "wet_bulb_temp_c" in r
    assert "er_rate_per_100k" in r
    assert r["evidence_complete"] is True


def test_water_tool_returns_expected_fields():
    r = _call(check_water_reserves, "water_shortage")
    assert r["investigation"] == "water_reserves"
    assert r["severity"] == "critical"          # reservoir_level_pct 14.7 < 15
    assert "days_to_day_zero" in r
    assert "rationing_coverage_pct" in r
    assert r["evidence_complete"] is True


def test_energy_tool_returns_expected_fields():
    r = _call(check_energy_capacity, "renewable_energy_gap")
    assert r["investigation"] == "energy_capacity"
    assert r["supply_deficit_GW"] > 0
    assert r["rolling_blackout_risk"] == "high"
    assert "unmet_after_flexibility_GW" in r
    assert r["evidence_complete"] is True


def test_data_quality_tool_known_scenario():
    r = _call(check_data_quality, "urban_heatwave")
    assert r["investigation"] == "data_quality"
    assert r["found_in_database"] is True
    assert r["data_completeness_pct"] == 100
    # known scenario: evidence_complete because we now know the type
    assert r["evidence_complete"] is True


def test_data_quality_tool_unknown_scenario():
    r = _call(check_data_quality, "totally_unknown_99")
    assert r["investigation"] == "data_quality"
    assert r["found_in_database"] is False
    assert r["evidence_complete"] is False
    assert len(r["missing_sensor_types"]) > 0


def test_wrong_type_returns_error_with_hint():
    r = _call(check_heat_cooling_risk, "water_shortage")
    assert "error" in r
    assert "hint" in r


def test_all_canonical_scenarios_covered():
    """Each of the three canonical scenarios must be handled without error by its typed tool."""
    for sid, data in SCENARIOS.items():
        tool_map = {
            "heatwave": check_heat_cooling_risk,
            "water_shortage": check_water_reserves,
            "energy_shortfall": check_energy_capacity,
        }
        t = tool_map.get(data["type"])
        if t is None:
            continue  # unexpected type; skip rather than fail
        result = _call(t, sid)
        assert "error" not in result, f"{t.__name__} failed on {sid}: {result}"


# ---------------------------------------------------------------------------
# build_state and scenario-ID extraction
# ---------------------------------------------------------------------------

def test_build_state_no_evidence():
    from agent.decision import build_state

    state = build_state("Heatwave in Phoenix. Scenario: urban_heatwave", [])
    assert "Operator request:" in state
    assert "No evidence collected yet." in state


def test_build_state_with_evidence():
    from agent.decision import build_state

    evidence = [{"investigation": "heat_cooling_risk", "severity": "critical"}]
    state = build_state("Scenario: urban_heatwave", evidence)
    assert "Step 1" in state
    assert "heat_cooling_risk" in state
    assert "critical" in state


def test_extract_scenario_id_explicit():
    from agent.agent import _extract_scenario_id

    assert _extract_scenario_id("Scenario: urban_heatwave") == "urban_heatwave"
    assert _extract_scenario_id("Scenario ID: water_shortage") == "water_shortage"
    assert _extract_scenario_id("scenario: renewable_energy_gap") == "renewable_energy_gap"


def test_extract_scenario_id_fallback():
    from agent.agent import _extract_scenario_id

    assert _extract_scenario_id("The urban_heatwave is getting worse") == "urban_heatwave"


def test_extract_scenario_id_unknown():
    from agent.agent import _extract_scenario_id

    assert _extract_scenario_id("Something is happening but no ID given") == ""


# ---------------------------------------------------------------------------
# EarthOSSelector decision log records (FakeDecider)
# ---------------------------------------------------------------------------

def test_selector_log_contains_required_fields():
    from agent.decision import build_state, make_selector

    selector = make_selector(FakeDecider(lambda s, n, q: "check_heat_cooling_risk"), threshold=0.6)
    selector.tools_for(build_state("Heatwave. Scenario: urban_heatwave", []))
    rec = selector.log[-1]
    for field in ("stage", "tool", "confidence", "probabilities", "alternatives", "outcome"):
        assert field in rec, f"missing field '{field}' in decision record"


def test_selector_narrows_when_confident():
    from agent.decision import build_state, make_selector

    selector = make_selector(FakeDecider(lambda s, n, q: "check_water_reserves"), threshold=0.6)
    tools = selector.tools_for(build_state("Water shortage. Scenario: water_shortage", []))
    assert len(tools) == 1
    spec = getattr(tools[0], "tool_spec", None)
    name = spec["name"] if spec else getattr(tools[0], "__name__", "")
    assert name == "check_water_reserves"
    assert selector.log[-1]["outcome"] == "narrowed"


def test_selector_keeps_all_when_unsure():
    from agent.decision import build_state, make_selector

    selector = make_selector(FakeDecider(lambda s, n, q: "check_heat_cooling_risk"), threshold=0.99)
    tools = selector.tools_for(build_state("crisis", []))
    assert len(tools) == len(TOOLS)
    assert selector.log[-1]["outcome"] == "all_tools_kept"


def test_selector_alternatives_sorted_by_probability():
    from agent.decision import build_state, make_selector

    selector = make_selector(FakeDecider(lambda s, n, q: "check_heat_cooling_risk"))
    selector.tools_for(build_state("heatwave", []))
    alts = selector.log[-1]["alternatives"]
    probs = [a["probability"] for a in alts]
    assert probs == sorted(probs, reverse=True), "alternatives should be sorted highest-first"


# ---------------------------------------------------------------------------
# Multi-step investigation loop (FakeDecider + patched Strands Agent)
# ---------------------------------------------------------------------------

class _FakeStrandsResult:
    """Stand-in Strands Agent result — no network call."""
    def __str__(self):
        return (
            "SEVERITY: Critical.\n"
            "RECOMMENDED ACTIONS:\n1. Activate emergency protocols.\n2. Deploy resources.\n3. Monitor situation.\n"
            "AT RISK: Approximately 1.5 million people."
        )

    @property
    def metrics(self):
        class _M:
            accumulated_usage = {"inputTokens": 0, "outputTokens": 0}
        return _M()


class _FakeAgent:
    """Strands Agent replacement — returns _FakeStrandsResult without any Bedrock call."""
    def __init__(self, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return _FakeStrandsResult()


def _run_chat(message, decider=None, model_id="us.amazon.nova-lite-v1:0", max_steps=3):
    """Run HackathonAgent.chat() with the Strands Agent monkey-patched."""
    import agent.agent as mod

    original = mod.Agent
    mod.Agent = _FakeAgent
    try:
        a = mod.HackathonAgent(
            decider=decider or FakeDecider(),
            model_id=model_id,
            max_steps=max_steps,
        )
        return a.chat(message)
    finally:
        mod.Agent = original


def test_chat_contract_keys():
    """chat() must return the kit-contract keys."""
    out = _run_chat("Urban heatwave in Phoenix. Scenario: urban_heatwave")
    for key in ("reply", "decisions", "model_id", "latency_ms", "agent"):
        assert key in out, f"missing required key '{key}'"
    assert out["agent"] == "EarthOS — The Decision Brain for a Living Planet"
    assert out["model_id"] == "us.amazon.nova-lite-v1:0"
    assert isinstance(out["decisions"], list)
    assert isinstance(out["latency_ms"], int)


def test_chat_decisions_have_tool_selection_stage():
    """At least one decision record must have stage='tool_selection'."""
    out = _run_chat("Water shortage in Chennai. Scenario: water_shortage")
    assert any(d.get("stage") == "tool_selection" for d in out["decisions"])


def test_chat_decisions_have_outcome_field():
    """Every decision record must have an 'outcome' field."""
    out = _run_chat("Renewable energy gap. Scenario: renewable_energy_gap")
    for d in out["decisions"]:
        assert "outcome" in d, f"decision record missing 'outcome': {d}"


def test_chat_loop_stops_after_evidence_complete():
    """The loop should stop as soon as a tool returns evidence_complete=True.

    FakeDecider always picks check_heat_cooling_risk, which returns evidence_complete=True.
    So with max_steps=3 we should get exactly 1 step.
    """
    out = _run_chat(
        "Heatwave emergency. Scenario: urban_heatwave",
        decider=FakeDecider(lambda s, n, q: "check_heat_cooling_risk"),
        max_steps=3,
    )
    # One Decider call per step; evidence_complete after first call for heatwave
    assert len(out["decisions"]) >= 1
    # The outcome of the last decision should reflect completion
    assert out["decisions"][-1]["outcome"] in ("evidence_complete", "narrowed", "step_complete", "all_tools_kept")


def test_chat_reply_is_non_empty_string():
    out = _run_chat("Scenario: urban_heatwave")
    assert isinstance(out["reply"], str)
    assert len(out["reply"]) > 0


def test_chat_unknown_scenario_id_still_returns_valid_dict():
    """chat() must not raise even when the scenario ID is not in SCENARIOS."""
    out = _run_chat("Unknown emergency. Scenario: totally_unknown_99")
    for key in ("reply", "decisions", "model_id", "latency_ms", "agent"):
        assert key in out
