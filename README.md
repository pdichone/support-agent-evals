# My AI agent looked perfect. Then I ran evals on it.

A customer support agent for a made-up kitchenware shop (Kettleworks), and the eval suite that found what the demo couldn't. Claude Opus 5.5 with four tools, 24 cases written from the shop's policy, code checks that grade what actually happened in the store, every case run k times (pass^k), an LLM judge for what code can't check, and a calibration script that grades the judge against my own labels.

Video: [link]

## Run it

```bash
git clone https://github.com/pdichone/support-agent-evals && cd support-agent-evals
uv venv && source .venv/bin/activate && uv pip install -r pyproject.toml
cp .env.example .env    # ANTHROPIC_API_KEY

python run_evals.py --demo --trials 1        # the five questions I tried by hand
python run_evals.py --prompt v1 --trials 5   # all 24 cases, 5 trials each: pass@1 and pass^5
python label.py                              # label 40 replies by hand, blind
python calibrate.py                          # grade two judges against your labels
python run_evals.py --prompt v2 --guard --trials 5 --judge claude-haiku-5-5
python agent.py "I was charged twice for K-1005" --as sam@example.com   # one conversation
```

A 5-trial pass over all 24 cases is 120 agent runs, about $3 on Opus 5.5. `calibrate.py` with two judges on 40 labels is well under $1.

## Files

| File | What |
|---|---|
| `store.py` | the fake shop: customers, orders, the policy, four tools, and the ledger of what really happened. Today is frozen at 2026-10-28 |
| `agent.py` | the agent: `@beta_tool` tools bound to a fresh store per trial, the SDK's `tool_runner`, the meter |
| `prompts/v1.md`, `v2.md` | the first prompt and the one written from error analysis |
| `cases.yaml` | 24 cases, each with what must be true at the end (refund, escalation, what the reply must or must never say) |
| `checks.py` | code graders: the ledger, the tickets, "said = did", leaks |
| `judge.py` | the LLM judge: binary, critique first, structured output |
| `run_evals.py` | runs cases × trials in parallel, grades them, writes `results/<config>.json` with pass@1, pass^k and every failure |
| `label.py` | blind human labeling on the judge's rubric → `results/labels.jsonl` |
| `calibrate.py` | each judge vs your labels: agreement, catches failures, passes good ones, Cohen's kappa, $ |

## What the checks grade

The outcome, not the path (Anthropic's advice in "Demystifying evals for AI agents"): whether money moved and how much, whether a human got a ticket and which team, whether the reply says it did something the ledger says it didn't, and whether it leaked another customer's details. Nothing checks which tools were called in which order.

## Notes

- `--guard` turns on the refund rules inside `issue_refund` itself (≤ $150, delivered, ≤ 30 days). The prompt makes a bad refund unlikely; the guard makes it impossible.
- No sampling parameters: API version `2026-10-21` rejects `temperature`. Variation between trials is the point, and pass^k measures it.
- 24 cases × 5 trials finds big problems, not small differences between prompts. See Evan Miller, "Adding Error Bars to Evals".
- My numbers: `results/`. They'll drift with the model; that's why the suite ships, not a screenshot.

MIT licensed.
