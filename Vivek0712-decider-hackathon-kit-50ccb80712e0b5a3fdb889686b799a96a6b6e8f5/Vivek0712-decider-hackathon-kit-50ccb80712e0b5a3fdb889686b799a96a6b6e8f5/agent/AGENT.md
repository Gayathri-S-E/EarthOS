# Use case

- **Pitch:** EarthOS — The Decision Brain for a Living Planet. An AI agent that investigates
  environmental emergencies step by step, using Strands Decider 2B to route each investigation
  and Amazon Bedrock to synthesise the evidence into a prioritised action brief.
- **Who it is for:** emergency-response coordinators, sustainability teams, and city planners who
  need fast, evidence-backed action briefs when an urban heatwave, water shortage, or
  renewable-energy gap is reported.
- **Features:**
  - accepts a plain-language scenario description and a scenario ID from the operator;
  - iterative investigation loop: Strands Decider 2B picks the next probe at each step given
    current evidence, runs the tool, and repeats until evidence is complete or the step limit
    is reached;
  - four specialist probes: heat/cooling risk, water reserves, energy capacity, data quality;
  - three built-in scenarios (synthetic, deterministic): urban heatwave (Phoenix), water
    shortage (Chennai), renewable-energy gap (UK National Grid);
  - Amazon Bedrock (Strands Agent) synthesises the gathered evidence into a three-section
    action brief — Severity, Recommended Actions, At Risk;
  - live decision panel shows per-tool probabilities, confidence, alternatives, and outcome.
- **The decision handed to Strands Decider 2B:** at each investigation step, given the current
  scenario description and evidence collected so far, which specialist tool should run next?
  (`#tool-selection`)
- **Why a decision model:** tool routing on language is a single forward pass — fast, cheap,
  and it returns calibrated confidence so the loop knows when to use all tools instead of one.
  The Bedrock LLM is reserved for the one task it does best: synthesising evidence into prose.
- **Amazon Bedrock:** the final action-brief synthesis (Amazon Nova Pro by default, via a
  Strands Agent with no tools — synthesis only).
