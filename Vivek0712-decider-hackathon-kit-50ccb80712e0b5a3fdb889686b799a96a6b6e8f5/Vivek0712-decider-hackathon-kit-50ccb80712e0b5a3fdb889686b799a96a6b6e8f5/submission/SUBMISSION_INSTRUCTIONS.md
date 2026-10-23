# EarthOS — Submission Instructions

Complete these steps before submitting to the hackathon.
Do NOT submit without your confirmation on each step.

---

## Step 1: Configure .env (required before any kit command works)

```powershell
.\kit.cmd setup
```

Choose:
- `DECIDER_MODE=ugmdu` (hosted API, needs key from https://www.awsugmdu.in) OR
- `DECIDER_MODE=local` (requires a running `strands-decider serve` on port 8099)
- `LLM_PROVIDER=bedrock` (required for submission)

Then enter AWS credentials when prompted, or run:
```powershell
.\kit.cmd aws-login
```

---

## Step 2: Run tests

```powershell
.\kit.cmd test
# expected: 46+ passed, 3 known pre-existing failures (ollama/openai optional packages)
```

---

## Step 3: Benchmark the decision

```powershell
.\kit.cmd bench --split tune    # tune questions, then:
.\kit.cmd bench --split test    # report numbers from submission/bench/results.md
```

Add the benchmark numbers to `submission/article/fields.md` and `submission/article/body.md`.

---

## Step 4: Deploy to Amazon Bedrock AgentCore

```powershell
.\kit.cmd deploy
# creates submission/deployment.json
.\kit.cmd invoke "Investigate the heatwave in Rajasthan. Scenario: heatwave_india_2026"
```

---

## Step 5: Record the demo video

```powershell
.\kit.cmd video --target agentcore
# output: submission/video/demo.mp4 (should be under 3 minutes)
```

Upload `demo.mp4` as a **public** video on YouTube or Vimeo. Save the URL.

---

## Step 6: Draft and finalise the article

```powershell
.\kit.cmd article --draft
# then edit submission/article/body.md in your own words
.\kit.cmd article
# repeat until it says "ready"
```

Publish on AWS Builder Center. Save the article URL.

---

## Step 7: Publish the public repository

```powershell
.\kit.cmd gh-login
.\kit.cmd publish <your-github-username/earthos-agent>
# or: .\kit.cmd readme    (updates README with real numbers first)
```

---

## Step 8: Collect the three submission links

Fill `submission/SUBMISSION.md` with:
1. Public repo URL (GitHub)
2. AWS Builder Center article URL
3. Video URL (YouTube or Vimeo, public)

---

## Step 9: Submit

Go to: https://builder.aws.com/build/hackathons/4f50957c-1d08-37ab-b11c-97516b9adeb4
Submit the three links before **23 October 2026, 11:59 PM PT**.

Tags to include: `#strands-decider-2b` and `#tool-selection`
