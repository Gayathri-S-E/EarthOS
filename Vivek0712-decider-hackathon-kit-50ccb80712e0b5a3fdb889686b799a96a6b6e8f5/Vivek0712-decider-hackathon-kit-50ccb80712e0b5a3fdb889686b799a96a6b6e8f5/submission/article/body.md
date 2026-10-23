# EarthOS — The Decision Brain for a Living Planet

## The problem

Emergency coordinators face three distinct crisis types — urban heatwaves, water shortages, and
renewable-energy gaps — with no time to route incoming reports to the wrong specialist. A
wrong-tool call wastes a full Bedrock LLM round-trip.  An LLM making the routing decision on
every step adds cost and latency that accumulates across a multi-step investigation.

## The decision

At each investigation step, **Strands Decider 2B** reads:

```
Operator request: <plain-language description>

Evidence collected so far:
  Step 1: water_reserves — severity critical
  ...
```

and answers one question:

> *Which investigation tool should handle this request?*

Options: `check_heat_cooling_risk`, `check_water_reserves`, `check_energy_capacity`,
`check_data_quality`, or `none`.  Each option's description is the tool's own docstring — no
retraining needed when a new probe is added.

One forward pass returns a calibrated probability per tool.  When the winner clears the
confidence threshold (0.6), only that tool is dispatched.  When it doesn't, all tools are
passed to the Strands Agent's LLM so nothing is ever lost.

## Architecture

```
operator message
     │
     ▼  ─────────── loop (max 3 steps) ───────────
Strands Decider 2B → tool selection → run tool → evidence
     │                                         │
     │         evidence_complete = True ◄──────┘
     ▼
Strands Agent (Amazon Bedrock, no tools) → Action Brief
```

The **REUSABLE DECISION PATTERN** in `agent/decision.py` (tagged `#tool-selection`) can be
copied for any multi-tool agent: replace `TOOLS`, set `context`, and the log records
(`stage`, `tool`, `confidence`, `probabilities`, `alternatives`, `outcome`, `decider_ms`)
flow automatically into the demo UI and the benchmark.

## Three scenarios, four tools

| Scenario | Region | Crisis |
|---|---|---|
| `urban_heatwave` | Phoenix Metro, Arizona | Wet-bulb temp 33 °C, 6 confirmed deaths |
| `water_shortage` | Greater Chennai, India | 14.7 % reservoir, 1.9 months to Day Zero |
| `renewable_energy_gap` | UK National Grid | 6.6 GW deficit, high blackout risk |

The fourth tool, `check_data_quality`, handles unknown or ambiguous scenarios and signals that
more sensor data is needed before a specialist tool can be dispatched.

## Benchmark

<!-- FIGURE: bench-accuracy.png -->
<!-- FIGURE: bench-latency.png -->

*Replace with the output of `submission/bench/results.md` after running
`.\kit.cmd bench --split test`.*

## Lessons

- **Tool docstrings are the option descriptions.** Keep them concise and domain-specific.
- **Confidence matters.** A 0.6 threshold gives good narrowing with a safe fallback.
- **Separate routing from synthesis.** Decider 2B handles `which tool`; Bedrock handles `what to say`.
- **The loop pattern is reusable.** `build_state(message, evidence)` is the only glue needed.

---

Built with the **AWS User Group Madurai** Strands Decider hackathon kit.
