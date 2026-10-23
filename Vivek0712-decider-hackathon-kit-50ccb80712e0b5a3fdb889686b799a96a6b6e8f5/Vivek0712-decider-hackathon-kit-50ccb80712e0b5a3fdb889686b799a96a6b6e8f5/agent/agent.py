"""EarthOS — The Decision Brain for a Living Planet.

Investigation loop
    Each chat turn runs up to MAX_STEPS investigation steps.  At every step:
      1. Strands Decider 2B reads the current state (operator message + evidence so far)
         and selects the next investigation tool.
      2. The selected tool is called directly (not via the Bedrock LLM) to gather evidence.
      3. If the tool signals `evidence_complete: True`, the loop stops early.
    After the loop, a single Strands Agent call on Amazon Bedrock synthesises the evidence
    into a prioritised action brief.

    Decider and Bedrock are kept entirely separate:
      - Decider 2B → routing only (which tool, when to stop)
      - Bedrock (Strands Agent) → natural-language synthesis only

Kit contract (must not change)
    HackathonAgent.chat(message, session_id="default") -> dict with keys:
      reply       str          action brief from Bedrock
      decisions   list[dict]   one record per Decider call (stage, tool, confidence,
                               probabilities, alternatives, outcome, decider_ms)
      model_id    str
      latency_ms  int
      agent       str

Usage
    from agent.agent import HackathonAgent
    out = HackathonAgent().chat("Urban heatwave in Phoenix. Scenario: urban_heatwave")
    print(out["reply"])
    for d in out["decisions"]:
        print(d["tool"], d["confidence"], d["outcome"])
"""

from __future__ import annotations

import time
from typing import Any

from strands import Agent

from decider_kit import Decider
from decider_kit.llm import agent_model, default_model_id, strip_thinking

from .decision import build_state, make_selector
from .tools import TOOLS, check_data_quality, check_energy_capacity, check_heat_cooling_risk, check_water_reserves

NAME = "EarthOS — The Decision Brain for a Living Planet"

MAX_STEPS = 3   # stop after this many Decider+tool rounds even without evidence_complete

SYSTEM_PROMPT = """You are EarthOS, an AI planetary-emergency analyst.
You will be given an operator request and a set of sensor evidence gathered by investigation tools.
Write a concise Action Brief with exactly these three sections:
  SEVERITY: one sentence (critical / high / moderate).
  RECOMMENDED ACTIONS: numbered list of the top three immediate actions.
  AT RISK: estimated population or infrastructure affected.
Be factual and specific. Use only the evidence provided. Never invent data or scenarios."""

# Map from tool spec-name to the direct Python callable for the investigation loop.
# The Strands @tool decorator stores the original function; the Bedrock Agent is given the
# decorated tool objects so the LLM can describe them.  The loop calls the raw functions
# directly so no Bedrock call is needed per investigation step.
_TOOL_FUNC: dict[str, Any] = {}
for _t in TOOLS:
    _spec = getattr(_t, "tool_spec", None)
    _name = _spec["name"] if _spec else getattr(_t, "__name__", str(_t))
    # Unwrap the Strands @tool wrapper to get the original Python function
    _fn = getattr(_t, "func", None) or getattr(_t, "__wrapped__", None) or _t
    _TOOL_FUNC[_name] = _fn


def _run_tool(tool_name: str, scenario_id: str) -> dict[str, Any]:
    """Call an investigation tool by spec-name, returning its result dict."""
    fn = _TOOL_FUNC.get(tool_name)
    if fn is None:
        return {"error": f"no tool named '{tool_name}'", "evidence_complete": False}
    try:
        result = fn(scenario_id)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "evidence_complete": False}
    if not isinstance(result, dict):
        return {"error": f"tool returned {type(result).__name__}", "evidence_complete": False}
    return result


def _extract_scenario_id(message: str) -> str:
    """Best-effort extraction of a scenario ID from the operator message.

    Looks for 'scenario: <id>' or 'scenario id: <id>' (case-insensitive).
    Falls back to checking if any known scenario ID appears as a word in the message.
    """
    from .tools import SCENARIOS

    lower = message.lower()
    for prefix in ("scenario id:", "scenario:"):
        if prefix in lower:
            after = lower.split(prefix, 1)[1].strip()
            # take the first word-like token
            token = after.split()[0].rstrip(".,;") if after.split() else ""
            if token in SCENARIOS:
                return token
    # fallback: scan for known IDs anywhere in the message
    for sid in SCENARIOS:
        if sid.lower() in lower:
            return sid
    return ""


class HackathonAgent:
    """Multi-step environmental investigation agent.

    Strands Decider 2B chooses the next probe at each step; Amazon Bedrock synthesises
    the final action brief.  Both are stateless per chat turn — no session memory.
    """

    def __init__(
        self,
        decider: Decider | None = None,
        model_id: str | None = None,
        selector_threshold: float = 0.6,
        max_steps: int = MAX_STEPS,
    ) -> None:
        self.decider = decider or Decider()
        self.model_id = model_id or default_model_id()
        self.selector_threshold = selector_threshold
        self.max_steps = max_steps

    def chat(
        self,
        message: str,
        session_id: str = "default",  # noqa: ARG002  kept for kit contract
        images: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Run the investigation loop, then generate the action brief with Bedrock.

        Returns the kit-contract dict: reply, decisions, model_id, latency_ms, agent.
        """
        t0 = time.perf_counter()

        scenario_id = _extract_scenario_id(message)
        selector = make_selector(self.decider, threshold=self.selector_threshold)
        evidence: list[dict[str, Any]] = []
        all_decisions: list[dict[str, Any]] = []

        # ------------------------------------------------------------------
        # Investigation loop — Decider picks next tool, tool gathers evidence
        # ------------------------------------------------------------------
        for _step in range(self.max_steps):
            state = build_state(message, evidence)
            selected_tools = selector.tools_for(state)

            # Record the decision (selector.log grows by one entry per call)
            if selector.log:
                all_decisions.append(selector.log[-1])

            # Determine which tool to run: use the Decider's choice when it narrowed,
            # otherwise fall back to the first tool that hasn't been run yet.
            if selected_tools and len(selected_tools) < len(TOOLS):
                tool_to_run = selected_tools[0]
            else:
                # Decider was unsure — pick the first tool not yet used
                used = {e.get("investigation") for e in evidence}
                tool_spec_to_inv = {
                    "check_heat_cooling_risk": "heat_cooling_risk",
                    "check_water_reserves": "water_reserves",
                    "check_energy_capacity": "energy_capacity",
                    "check_data_quality": "data_quality",
                }
                tool_to_run = None
                for t in TOOLS:
                    spec = getattr(t, "tool_spec", None)
                    tname = spec["name"] if spec else getattr(t, "__name__", "")
                    if tool_spec_to_inv.get(tname) not in used:
                        tool_to_run = t
                        break

            if tool_to_run is None:
                break  # all tools already used

            spec = getattr(tool_to_run, "tool_spec", None)
            tool_name = spec["name"] if spec else getattr(tool_to_run, "__name__", "")

            result = _run_tool(tool_name, scenario_id) if scenario_id else {
                "error": "no scenario_id found in message",
                "evidence_complete": False,
            }

            # Tag the result with the tool name for logging
            result["_tool"] = tool_name
            evidence.append(result)

            # Update the outcome field on the corresponding decision record
            if all_decisions:
                all_decisions[-1]["outcome"] = (
                    "evidence_complete" if result.get("evidence_complete") else "step_complete"
                )

            if result.get("evidence_complete"):
                break

        # ------------------------------------------------------------------
        # Bedrock synthesis — one LLM call to write the action brief
        # ------------------------------------------------------------------
        evidence_text = "\n\n".join(
            f"[{e.get('_tool', 'tool')}]\n" + "\n".join(f"  {k}: {v}" for k, v in e.items() if not k.startswith("_"))
            for e in evidence
        )
        synthesis_prompt = (
            f"Operator request: {message}\n\n"
            f"Scenario: {scenario_id or '(not identified)'}\n\n"
            f"Investigation evidence:\n{evidence_text or '(no evidence collected)'}"
        )

        agent = Agent(
            model=agent_model(self.model_id),
            system_prompt=SYSTEM_PROMPT,
            tools=[],            # synthesis only — no tools needed
            callback_handler=None,
        )

        if images:
            from decider_kit.llm import image_blocks
            result_obj = agent([*image_blocks(images), {"text": synthesis_prompt}])
        else:
            result_obj = agent(synthesis_prompt)

        reply = strip_thinking(str(result_obj))
        latency_ms = round((time.perf_counter() - t0) * 1000)

        return {
            "reply": reply,
            "decisions": all_decisions,
            "model_id": self.model_id,
            "latency_ms": latency_ms,
            "agent": NAME,
        }


if __name__ == "__main__":
    import json
    import sys

    a = HackathonAgent()
    messages = sys.argv[1:] or [
        "Investigate the urban heatwave. Scenario: urban_heatwave",
        "Metropolitan water supply is failing. Scenario: water_shortage",
        "Renewable energy gap on the national grid. Scenario: renewable_energy_gap",
    ]
    for msg in messages:
        print(json.dumps(a.chat(msg), indent=2, default=str))
        print()
