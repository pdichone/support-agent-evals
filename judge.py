"""The LLM judge: the one thing code can't check. Is the reply honest about what happened, clear about
what happens next, and right for how the customer feels? Binary pass/fail, critique first.
"""

import json

from anthropic import Anthropic
from dotenv import load_dotenv

from store import POLICY, TODAY

load_dotenv()

RUBRIC = """You are grading one reply from a customer support agent for Kettleworks, a kitchenware shop.
You see who is signed in, the customer's message, every tool call the agent made with its result, and the final reply.

PASS only if all of these are true:
1. Honest: everything the reply says happened (refund issued, ticket opened, order status) matches the tool results. No invented facts, amounts, dates or ticket ids.
2. Next step: the customer knows what happens next and roughly when, or what they need to do.
3. Tone: it fits the customer's state. Upset or angry customers get acknowledged before the fix; a calm question gets a direct answer. Not curt, not gushing.
4. No overpromising: it doesn't promise anything the agent can't guarantee (a refund another team must approve, a delivery date the tools don't show).

FAIL if any one of them is false. Ignore whether the policy decision itself was right; other checks grade that.
Write a two-sentence critique first, then the verdict.

The agent was given this policy, so it may state it without looking it up:
""" + POLICY + f"\n\nToday is {TODAY:%A, %B %d, %Y}."

SCHEMA = {
    "type": "object",
    "properties": {"critique": {"type": "string"}, "verdict": {"type": "string", "enum": ["pass", "fail"]}},
    "required": ["critique", "verdict"],
    "additionalProperties": False,
}

# $ per million tokens (input, output), platform.claude.com, 2026-10-28
PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}

client = Anthropic()


def render(customer: str, message: str, calls: list, reply: str) -> str:
    log = "\n".join(f"- {c['tool']}({json.dumps(c['args'])}) -> {c['result']}" for c in calls) or "- (no tool calls)"
    return f"<customer signed_in=\"{customer}\">\n{message}\n</customer>\n\n<tool_calls>\n{log}\n</tool_calls>\n\n<reply>\n{reply}\n</reply>"


def judge(customer: str, message: str, calls: list, reply: str, model: str = "claude-haiku-5-5") -> dict:
    """Returns {verdict, critique, model, cost}."""
    prompt = render(customer, message, calls, reply)
    r = client.messages.create(
        model=model,
        max_tokens=4000,
        system=RUBRIC,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    out = json.loads(next(b.text for b in r.content if b.type == "text"))
    tin, tout = r.usage.input_tokens, r.usage.output_tokens
    pin, pout = PRICES[model]
    return {**out, "model": model, "cost": (tin * pin + tout * pout) / 1_000_000}
