"""Label replies by hand, on the same rubric the judge uses. Blind: you never see the checks or the judge.

    python label.py            # 40 trials sampled from every results/runs-*.jsonl, resumes where you stopped
    python label.py --n 60

Keys: p = pass, f = fail, s = skip, q = quit. Then an optional one-line note (why), which is your error analysis.
"""

import argparse
import json
import random
from pathlib import Path

from judge import RUBRIC

OUT = Path("results/labels.jsonl")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()

    rows = []
    for f in sorted(Path("results").glob("runs-*.jsonl")):
        if "-demo" not in f.name:
            for i, line in enumerate(f.open()):
                rows.append({**json.loads(line), "key": f"{f.stem.removeprefix('runs-')}/{i}"})
    rows = [r for r in rows if r.get("reply")]
    random.Random(a.seed).shuffle(rows)
    seen_cases, picked = set(), []
    for r in rows:  # first pass: one per case and config, so the sample isn't all happy-path
        key = (r["case_id"], r["prompt"])
        if key not in seen_cases:
            seen_cases.add(key)
            picked.append(r)
    picked += [r for r in rows if r not in picked]
    picked = picked[: a.n]

    done = {json.loads(l)["key"] for l in OUT.open()} if OUT.exists() else set()
    print(RUBRIC.split("PASS only if")[1].split("Write a")[0].strip(), "\n")
    for n, r in enumerate(picked, 1):
        key = f"{r['key']}/{r['case_id']}"
        if key in done:
            continue
        print("=" * 80, f"\n[{n}/{len(picked)}] {key}\n\nCUSTOMER: {r['message']}\n")
        for c in r["calls"]:
            print(f"  → {c['tool']}({json.dumps(c['args'])})\n      {c['result'][:300]}")
        print(f"\nREPLY:\n{r['reply']}\n")
        while (k := input("p / f / s / q > ").strip().lower()) not in ("p", "f", "s", "q"):
            pass
        if k == "q":
            break
        if k == "s":
            continue
        note = input("note (optional) > ").strip()
        with OUT.open("a") as f:
            f.write(json.dumps({"key": key, "label": "pass" if k == "p" else "fail", "note": note,
                                "message": r["message"], "calls": r["calls"], "reply": r["reply"]}) + "\n")
    print(f"\n{sum(1 for _ in OUT.open()) if OUT.exists() else 0} labels in {OUT}")


if __name__ == "__main__":
    main()
