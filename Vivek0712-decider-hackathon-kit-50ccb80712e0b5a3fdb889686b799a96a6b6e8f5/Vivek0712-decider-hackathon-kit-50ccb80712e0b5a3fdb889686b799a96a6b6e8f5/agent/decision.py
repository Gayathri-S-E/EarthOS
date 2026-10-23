"""REUSABLE DECISION PATTERN: environmental investigation routing  (#tool-selection)

What it does
    Given the current state of an environmental investigation (scenario description plus any
    evidence already collected), Strands Decider 2B picks which specialist tool to run next:

    - check_heat_cooling_risk   — temperature, wet-bulb, cooling capacity
    - check_water_reserves      — reservoir levels, daily deficit, Day-Zero countdown
    - check_energy_capacity     — generation gap, grid reserves, blackout risk
    - check_data_quality        — sensor availability and scenario classification

    When the decider is confident (above `threshold`, default 0.6), only that one tool is
    passed to the Strands Agent — reducing token use and wrong-tool calls.  When it is unsure,
    all tools are passed and the LLM chooses, so nothing is ever lost.

    The decision is repeated each step inside the investigation loop in `agent.py`, with the
    growing evidence context appended to the state, until a tool signals `evidence_complete`
    or the step limit is reached.

Typed questions and options
    `tool` (choice): one option per investigation tool, described by that tool's own docstring,
    plus `none`.  Options are assembled from the live `TOOLS` list at import time, so adding a
    new probe requires no model retraining — just a new `@tool` function and a line in TOOLS.

Wiring
    Called from `HackathonAgent.chat()` before each investigation step:

        from agent.decision import make_selector, build_state
        selector = make_selector(decider)
        tools_this_step = selector.tools_for(build_state(message, evidence_so_far))
        # each call appends one record to selector.log

How to reuse it
    Copy this file.  Replace TOOLS with your own `@tool` functions and set `context` to one
    sentence describing your domain.  The log record produced by each `selector.select()` call
    (stage, tool, confidence, probabilities, alternatives, outcome, decider_ms) is included in
    `HackathonAgent.chat()["decisions"]` and rendered live in the demo UI.
"""

from __future__ import annotations

from typing import Any

from decider_kit import Decider
from decider_kit.patterns.tool_selection import ToolSelector, questions_for

from .tools import TOOLS

PATTERN_TAG = "#tool-selection"

# Assembled once at import so the benchmark and tests share exactly these questions.
QUESTIONS = questions_for(TOOLS, context="environmental crisis investigation routing")


def build_state(message: str, evidence: list[dict[str, Any]]) -> str:
    """Compose the state string that Strands Decider 2B reads.

    The state includes the original operator message and a summary of evidence collected so far,
    mirroring the layout used in eval_cases.jsonl so the benchmark measures the same thing.
    """
    lines = [f"Operator request: {message}"]
    if evidence:
        lines.append("\nEvidence collected so far:")
        for i, e in enumerate(evidence, 1):
            inv = e.get("investigation", "unknown")
            sev = e.get("severity", "")
            lines.append(f"  Step {i}: {inv}" + (f" — severity {sev}" if sev else ""))
    else:
        lines.append("\nNo evidence collected yet.")
    return "\n".join(lines)


class EarthOSSelector:
    """ToolSelector wrapper that appends EarthOS-specific fields (alternatives, outcome)
    to each decision log record so the demo UI shows richer information."""

    def __init__(self, decider: Decider, threshold: float = 0.6) -> None:
        self._selector = ToolSelector(
            decider,
            tools=TOOLS,
            threshold=threshold,
            context="environmental crisis investigation routing",
        )
        self.log: list[dict[str, Any]] = []

    def tools_for(self, state: str) -> list[Any]:
        sel = self._selector.select(state)
        raw = self._selector.log[-1].copy()

        # Add alternatives: all tools sorted by probability, highest first
        probs = raw.get("probabilities", {})
        alternatives = sorted(
            [{"tool": t, "probability": round(p, 3)} for t, p in probs.items() if t != sel.tool],
            key=lambda x: x["probability"],
            reverse=True,
        )

        raw["pattern"] = PATTERN_TAG
        raw["alternatives"] = alternatives
        raw["outcome"] = "narrowed" if sel.narrowed else "all_tools_kept"
        self.log.append(raw)

        if not sel.narrowed:
            return list(TOOLS)
        if sel.tool == "none":
            return []
        by_name = {getattr(t, "__name__", str(t)): t for t in TOOLS}
        # ToolSelector uses tool spec name; fall back gracefully
        by_spec = {}
        for t in TOOLS:
            spec = getattr(t, "tool_spec", None)
            if spec:
                by_spec[spec["name"]] = t
        chosen = by_spec.get(sel.tool) or by_name.get(sel.tool)
        return [chosen] if chosen else list(TOOLS)

    @property
    def selector(self) -> ToolSelector:
        return self._selector


def make_selector(decider: Decider | None = None, threshold: float = 0.6) -> EarthOSSelector:
    """Return an EarthOSSelector configured for environmental investigation routing."""
    return EarthOSSelector(decider or Decider(), threshold=threshold)
