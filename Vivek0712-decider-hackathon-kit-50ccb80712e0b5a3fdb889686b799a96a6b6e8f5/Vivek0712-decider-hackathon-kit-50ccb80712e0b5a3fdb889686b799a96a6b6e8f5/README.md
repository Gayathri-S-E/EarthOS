# EarthOS — The Decision Brain for a Living Planet

An AI environmental-emergency analyst.  **Strands Decider 2B** routes each investigation step;
**Amazon Bedrock** (Amazon Nova Pro, via the Strands Agents SDK) writes the action brief.

---

## How it works

```
operator message
      │
      ▼  (repeated up to MAX_STEPS times)
Strands Decider 2B ──► which tool next? ──► run tool ──► add evidence
      │                                               │
      │                evidence_complete = True ◄─────┘
      ▼
Strands Agent (Amazon Bedrock, no tools) ──► Action Brief
```

1. The operator describes an environmental crisis and supplies a scenario ID.
2. Strands Decider 2B reads the state (message + evidence so far) and picks the next investigation tool in **one forward pass** — no LLM call needed.
3. The selected tool gathers evidence from the scenario database.  When `evidence_complete: True` is returned, the loop stops.
4. A single Strands Agent call on Amazon Bedrock synthesises the evidence into a **three-section action brief**: Severity · Recommended Actions · At Risk.

The Decider and Bedrock are kept entirely separate: Decider 2B handles routing; Bedrock handles language.

---

## Three scenarios

| Scenario ID | Type | Location |
|---|---|---|
| `urban_heatwave` | Urban heatwave | Phoenix Metro Area, Arizona, USA |
| `water_shortage` | Metropolitan water shortage | Greater Chennai, Tamil Nadu, India |
| `renewable_energy_gap` | Renewable-energy shortfall | UK National Grid |

All data is synthetic and deterministic — the demo, tests, and benchmark work offline.

---

## Four investigation tools

| Tool | What it probes |
|---|---|
| `check_heat_cooling_risk` | Wet-bulb temperature, vulnerable population, cooling-centre headroom, ER visit rate |
| `check_water_reserves` | Reservoir level, daily deficit, Day-Zero countdown, rationing coverage |
| `check_energy_capacity` | Generation gap, gas storage, blackout risk, demand-response headroom |
| `check_data_quality` | Sensor availability and scenario classification for unknown emergencies |

---

## Decision pattern: `#tool-selection`

`agent/decision.py` contains the labelled **REUSABLE DECISION PATTERN**.  Copy it, replace
`TOOLS` with your own `@tool` functions, and set `context` to your domain:

```python
from agent.decision import make_selector, build_state
selector = make_selector(decider)                        # EarthOSSelector wrapping ToolSelector
tools = selector.tools_for(build_state(message, evidence))
# selector.log[-1] has: stage, tool, confidence, probabilities, alternatives, outcome, decider_ms
```

---

## Quick start

```powershell
# 1. Configure environment (API keys, Bedrock model, Decider endpoint)
.\kit.cmd setup

# 2. Run tests (no cloud needed)
.\kit.cmd test

# 3. Local demo UI  (requires .env with DECIDER_MODE and LLM_PROVIDER)
.\kit.cmd demo
# open http://localhost:8501 — try: "Urban heatwave in Phoenix. Scenario: urban_heatwave"

# 4. Benchmark Decider 2B vs Bedrock LLM
.\kit.cmd bench --split tune
.\kit.cmd bench --split test
```

---

## Environment (`.env`)

```
DECIDER_MODE=ugmdu              # ugmdu | local
DECIDER_URL=https://da25tnxy06gjk.cloudfront.net
DECIDER_API_KEY=<your-key>      # from https://www.awsugmdu.in — never commit
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=us.amazon.nova-pro-v1:0
AWS_REGION=us-east-1
```

---

## Licence

Apache-2.0

Built with the **AWS User Group Madurai** Strands Decider hackathon kit.
[Agent Experience Hackathon: Strands Decider](https://builder.aws.com/build/hackathons/4f50957c-1d08-37ab-b11c-97516b9adeb4)
