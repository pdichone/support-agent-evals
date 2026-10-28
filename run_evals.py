"""The eval runner: every case, k trials each, graded by code.

    python run_evals.py --demo                   # the five questions I tried by hand
    python run_evals.py                          # all 24 cases, one trial
    python run_evals.py --show-failures          # ...and print the transcript of every failure
    python run_evals.py --trials 5               # pass@1 and pass^5
"""

import argparse
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from math import comb
from pathlib import Path

import yaml

import agent
from checks import run_checks

CASES = yaml.safe_load(Path("cases.yaml").read_text())


def run_trial(case: dict) -> dict:
    try:
        t = agent.run(case["message"], case["as"], case_id=case["id"]).to_dict()
    except Exception as e:  # a crashed trial is a failed trial
        return {"case_id": case["id"], "tag": case["tag"], "checks": [["crashed", False, repr(e)]],
                "code_pass": False, "cost": 0.0, "calls": [], "reply": ""}
    t["tag"], t["message"] = case["tag"], case["message"]
    t["checks"] = run_checks(case, t)
    t["code_pass"] = all(ok for _, ok, _ in t["checks"])
    return t


def pass_hat_k(c: int, n: int, k: int) -> float:
    """pass^k (tau-bench): the chance that k trials, picked from this case's n, all passed."""
    return comb(c, k) / comb(n, k)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--trials", type=int, default=1)
    p.add_argument("--demo", action="store_true", help="only the five cases I tried by hand")
    p.add_argument("--show-failures", action="store_true")
    a = p.parse_args()

    cases = [c for c in CASES if c.get("demo") or not a.demo]
    jobs = [c for c in cases for _ in range(a.trials)]
    with ThreadPoolExecutor(8) as pool:  # 24 cases × 5 trials is 120 agent runs: run 8 at a time
        trials = list(pool.map(run_trial, jobs))

    # pass@1 and pass^k, per tag and overall
    results = defaultdict(list)  # case_id -> [True, False, ...]
    for t in trials:
        results[t["case_id"]].append(t["code_pass"])
    tags = {c["id"]: c["tag"] for c in cases}
    k = a.trials
    print(f"\n{'tag':<14}{'cases':>6}{'pass@1':>9}{f'pass^{k}':>9}")
    for tag in sorted(set(tags.values())) + ["ALL"]:
        runs = [r for cid, r in results.items() if tag in ("ALL", tags[cid])]
        p1 = sum(sum(r) / len(r) for r in runs) / len(runs)
        pk = sum(pass_hat_k(sum(r), len(r), k) for r in runs) / len(runs)
        print(f"{tag:<14}{len(runs):>6}{p1:>9.0%}{pk:>9.0%}")
    cost = sum(t["cost"] for t in trials)
    print(f"\n${cost:.2f} for {len(trials)} trials")

    # every failure: this list is where error analysis starts
    for t in trials:
        failed = [f"{name}: {why}" for name, ok, why in t["checks"] if not ok]
        if failed:
            print(f"✗ {t['case_id']}  " + " | ".join(failed))
            if a.show_failures:
                for c in t["calls"]:
                    print(f"    → {c['tool']}({json.dumps(c['args'])})")
                print("    " + t["reply"].replace("\n", "\n    ") + "\n")

    config = "v1" + ("-demo" if a.demo else "")
    Path("results").mkdir(exist_ok=True)
    with open(f"results/runs-{config}.jsonl", "w") as f:
        f.writelines(json.dumps(t) + "\n" for t in trials)


if __name__ == "__main__":
    main()
