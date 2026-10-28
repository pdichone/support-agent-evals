"""The support agent: Claude + four tools on a fresh Kettleworks store.

    python agent.py "My kettle arrived cracked, order K-1001" --as maya@example.com
"""

import argparse
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from anthropic import Anthropic, beta_tool
from dotenv import load_dotenv

from store import POLICY, Store

load_dotenv()

MODEL = os.getenv("AGENT_MODEL", "claude-opus-5-5")
EFFORT = os.getenv("EFFORT", "medium")  # Opus 5.5's default; set explicitly so every trial matches
# $ per million tokens (platform.claude.com pricing, 2026-10-28)
PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00),
          "claude-haiku-5-5": (0.10, 0.50)}

client = Anthropic()


def system_prompt(version: str, customer: str) -> str:
    text = (Path(__file__).parent / "prompts" / f"{version}.md").read_text().format(policy=POLICY)
    return f"{text}\n\nThe signed-in customer is {customer}."


def make_tools(store: Store) -> list:
    """The agent's four tools, bound to this trial's store."""

    @beta_tool
    def lookup_order(order_id: str) -> str:
        """Look up one order: customer email, item, total, status, delivery date, charges, gift note.

        Args:
            order_id: e.g. 'K-1001'.
        """
        return store.lookup_order(order_id)

    @beta_tool
    def find_orders(email: str) -> str:
        """List the order ids that belong to a customer email.

        Args:
            email: The customer's email.
        """
        return store.find_orders(email)

    @beta_tool
    def issue_refund(order_id: str, amount: float, reason: str) -> str:
        """Refund money to the customer's card. This really moves money.

        Args:
            order_id: The order to refund.
            amount: Dollars to refund.
            reason: Short reason, for the ledger.
        """
        return store.issue_refund(order_id, amount, reason)

    @beta_tool
    def escalate_to_human(team: str, summary: str) -> str:
        """Hand the conversation to a human team. Returns a ticket id.

        Args:
            team: 'billing', 'security', 'returns', or 'general'.
            summary: What the human needs to know.
        """
        return store.escalate_to_human(team, summary)

    return [lookup_order, find_orders, issue_refund, escalate_to_human]


@dataclass
class Trial:
    case_id: str
    prompt: str
    model: str = MODEL
    reply: str = ""
    calls: list = field(default_factory=list)     # tool, args, result
    refunds: list = field(default_factory=list)   # the outcome: money that moved
    tickets: list = field(default_factory=list)   # the outcome: humans pulled in
    api_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    stop_reason: str = ""
    error: str = ""

    @property
    def cost(self) -> float:
        i, o = PRICES[self.model]
        return (self.input_tokens * i + self.output_tokens * o) / 1_000_000

    def to_dict(self) -> dict:
        return {**asdict(self), "cost": round(self.cost, 5)}


def run(message: str, customer: str, prompt: str = "v1", case_id: str = "adhoc") -> Trial:
    store = Store()
    t = Trial(case_id, prompt)
    t0 = time.perf_counter()
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,  # Opus 5.5 always thinks; thinking counts toward this
        system=system_prompt(prompt, customer),
        output_config={"effort": EFFORT},
        tools=make_tools(store),
        messages=[{"role": "user", "content": message}],
    )
    for msg in runner:  # one iteration per API call; the runner runs the tools in between
        t.api_calls += 1
        t.input_tokens += msg.usage.input_tokens or 0
        t.output_tokens += msg.usage.output_tokens or 0
        text = "".join(b.text for b in msg.content if b.type == "text")
        if text.strip():
            t.reply = text
        t.stop_reason = msg.stop_reason or ""
    t.seconds = round(time.perf_counter() - t0, 1)
    t.calls, t.refunds, t.tickets = store.calls, store.refunds, store.tickets
    return t


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("message")
    p.add_argument("--as", dest="customer", default="maya@example.com")
    a = p.parse_args()
    t = run(a.message, a.customer)
    for c in t.calls:
        print(f"  → {c['tool']}({', '.join(f'{k}={v!r}' for k, v in c['args'].items())})")
    print(f"\n{t.reply}\n")
    print(f"[{t.prompt}] {t.seconds}s · {len(t.calls)} tool calls · refunds {t.refunds or 'none'} · "
          f"tickets {[x['team'] for x in t.tickets] or 'none'} · ${t.cost:.3f}")
