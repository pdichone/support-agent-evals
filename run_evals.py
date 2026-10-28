"""The eval runner: every case once, graded by code, every failure printed.

    python run_evals.py --demo              # the five questions I tried by hand
    python run_evals.py                     # all 24 cases
    python run_evals.py --show-failures     # ...and print the transcript of every failure
"""

import argparse
import json
from pathlib import Path

import yaml

import agent
from checks import run_checks

CASES = yaml.safe_load(Path("cases.yaml").read_text())


def run_trial(case: dict) -> dict:
    t = agent.run(case["message"], case["as"], case_id=case["id"]).to_dict()
    t["checks"] = run_checks(case, t)
    t["code_pass"] = all(ok for _, ok, _ in t["checks"])
    return t


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true", help="only the five cases I tried by hand")
    p.add_argument("--show-failures", action="store_true")
    a = p.parse_args()

    cases = [c for c in CASES if c.get("demo") or not a.demo]
    trials = [run_trial(c) for c in cases]

    passed = sum(t["code_pass"] for t in trials)
    print(f"\n{passed}/{len(trials)} passed ({passed / len(trials):.0%}) · ${sum(t['cost'] for t in trials):.2f}")

    # every failure: this list is where error analysis starts
    for t in trials:
        failed = [f"{name}: {why}" for name, ok, why in t["checks"] if not ok]
        if failed:
            print(f"✗ {t['case_id']}  " + " | ".join(failed))
            if a.show_failures:
                for c in t["calls"]:
                    print(f"    → {c['tool']}({json.dumps(c['args'])})")
                print("    " + t["reply"].replace("\n", "\n    ") + "\n")


if __name__ == "__main__":
    main()
