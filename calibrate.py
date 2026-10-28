"""Grade the grader: run each judge on the replies I labeled by hand, and count where it agrees with me.

    python calibrate.py                              # Haiku 5.5 and Opus 5.5
    python calibrate.py --judges claude-sonnet-5-5   # any other judge
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from judge import judge

SIGNED_IN = {c["id"]: c["as"] for c in yaml.safe_load(Path("cases.yaml").read_text())}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--judges", nargs="*", default=["claude-haiku-5-5", "claude-opus-5-5"])
    a = p.parse_args()

    labels = [json.loads(line) for line in open("results/labels.jsonl")]
    for l in labels:  # who was signed in comes from the case
        l["as"] = SIGNED_IN[l["key"].rsplit("/", 1)[1]]
    human_fails = sum(l["label"] == "fail" for l in labels)
    print(f"{len(labels)} labels by hand: {len(labels) - human_fails} pass, {human_fails} fail\n")
    print(f"{'judge':<20}{'agreement':>11}{'catches failures':>18}{'passes good ones':>18}{'$':>8}")

    for model in a.judges:
        with ThreadPoolExecutor(8) as pool:
            verdicts = list(pool.map(lambda l: judge(l["as"], l["message"], l["calls"], l["reply"], model), labels))
        pairs = [(l["label"], v["verdict"]) for l, v in zip(labels, verdicts)]

        agreement = sum(h == j for h, j in pairs) / len(pairs)
        # agreement alone hides a judge that passes everything, so split it:
        catches = sum(h == j == "fail" for h, j in pairs) / max(human_fails, 1)            # of my fails, judge failed
        passes = sum(h == j == "pass" for h, j in pairs) / max(len(pairs) - human_fails, 1)  # of my passes, judge passed
        cost = sum(v["cost"] for v in verdicts)
        print(f"{model:<20}{agreement:>11.0%}{catches:>18.0%}{passes:>18.0%}{cost:>8.3f}")

        for l, v in zip(labels, verdicts):
            if l["label"] != v["verdict"]:
                print(f"    {l['key']}: me {l['label']}, judge {v['verdict']}: {v['critique'][:160]}")


if __name__ == "__main__":
    main()
