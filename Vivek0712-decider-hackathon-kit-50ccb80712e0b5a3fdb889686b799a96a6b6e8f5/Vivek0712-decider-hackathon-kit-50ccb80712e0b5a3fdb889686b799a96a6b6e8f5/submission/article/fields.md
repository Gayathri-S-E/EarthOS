# Builder Center article fields

## Title
EarthOS — The Decision Brain for a Living Planet

## Tags
#strands-decider-2b #tool-selection

## Subtitle / summary (one line)
An AI emergency-response agent that uses Strands Decider 2B to triage planetary crises and Amazon Bedrock to draft action briefs.

## Pattern tag
#tool-selection

## Agent name
EarthOS

## One-line pitch
EarthOS routes each environmental emergency to the right investigation tool in a single Strands Decider 2B forward pass, then synthesises the evidence into a prioritised action brief with Amazon Bedrock.

## Problem
Emergency coordinators face three types of planetary crises — heatwaves, water shortages, and energy shortfalls — with little time to route incoming reports to the right specialist tool. A wrong routing wastes seconds that matter; an LLM routing call adds cost and latency on every dispatch.

## Solution
Strands Decider 2B reads the operator's scenario description and returns calibrated probabilities over four investigation tools in one forward pass (~0.1–2 s, near-zero cost). The correct tool is invoked, evidence is collected, and Amazon Bedrock (Amazon Nova Pro via a Strands Agent) drafts the action brief. Below the confidence threshold all tools are kept and the LLM decides — nothing is lost.

## Benchmark numbers
<!-- FILL IN after running: .\kit.cmd bench --split test -->
Replace this section with the output of submission/bench/results.md after running the benchmark.

## Repo URL
<!-- FILL IN after running: .\kit.cmd publish -->

## Video URL
<!-- FILL IN after uploading demo.mp4 to YouTube/Vimeo -->

## Credit line (required — do not remove)
Built with the AWS User Group Madurai Strands Decider hackathon kit.
