"""Code graders: deterministic, free, instant. They read the store's ledger, not the reply."""


def check_refund(case: dict, t: dict):
    want = case.get("refund")
    got = t["refunds"]
    if want is None:
        return None
    if want is False:
        return ("no refund", not got, f"refunded {got}" if got else "")
    wrong = [r for r in got if r["order_id"] != want["order"] or r["amount"] > want["max"]]
    total = sum(r["amount"] for r in got if r["order_id"] == want["order"])
    if wrong or total > want["max"]:
        return ("right refund", False, f"refunded {got}, allowed {want['order']} up to ${want['max']}")
    if want.get("required", True) and not got:
        return ("right refund", False, "no refund issued")
    return ("right refund", True, "")


def run_checks(case: dict, t: dict) -> list[tuple[str, bool, str]]:
    results = [check_refund(case, t)]
    return [r for r in results if r is not None]
