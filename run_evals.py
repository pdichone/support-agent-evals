"""The smallest eval runner that works: run every case once, grade it in code, print PASS or FAIL."""

from pathlib import Path

import yaml

import agent
from checks import run_checks

CASES = yaml.safe_load(Path("cases.yaml").read_text())

for case in CASES:
    t = agent.run(case["message"], case["as"], case_id=case["id"]).to_dict()
    checks = run_checks(case, t)
    passed = all(ok for _, ok, _ in checks)
    print("PASS" if passed else "FAIL", case["id"], [f"{name}: {why}" for name, ok, why in checks if not ok])
