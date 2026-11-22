"""Replay ordered virtual-resource transactions with an all-or-nothing spend policy."""

TITLE = "Game Economy Ledger"
DESCRIPTION = "Replay game rewards and purchases in order to expose blocked spends and resource shortfalls by phase."
PROMPT = ("Explain where a player cannot afford the next spend. Cite phase, event, resource, opening "
          "balance and shortfall, and keep hypothetical shortfalls distinct from currency actually spent.")


def analyze(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Input must be an object.")
    opening, events = data.get("opening"), data.get("events")
    if (not isinstance(opening, dict) or not opening or not isinstance(events, list)
            or any(not isinstance(k, str) or not k.strip() or type(v) is not int or v < 0
                   for k, v in opening.items())):
        raise ValueError("Provide nonnegative integer opening balances for named resources and an events list.")
    balances = dict(opening)
    ids, phases, rows, blocked = set(), {}, [], 0
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("Every event must be an object.")
        eid, phase, kind = [event.get(k) for k in ("id", "phase", "kind")]
        if any(not isinstance(s, str) or not s.strip() for s in (eid, phase)):
            raise ValueError("Every event needs a nonempty ID and phase.")
        if eid in ids:
            raise ValueError(f"Duplicate event ID: {eid}.")
        ids.add(eid)
        amounts = event.get("amounts")
        if kind not in ("grant", "spend") or not isinstance(amounts, dict) or not amounts:
            raise ValueError(f"{eid}: provide grant or spend with a nonempty amounts object.")
        for resource, quantity in amounts.items():
            if resource not in balances or type(quantity) is not int or quantity <= 0:
                raise ValueError(f"{eid}: use positive integer amounts of declared resources.")
        gaps = {r: max(0, n - balances[r]) if kind == "spend" else 0 for r, n in amounts.items()}
        rejected = any(gaps.values())
        blocked += int(rejected)
        phase_report = phases.setdefault(phase, {"events": 0, "blocked_spends": 0, "shortfalls": {}})
        phase_report["events"] += 1
        phase_report["blocked_spends"] += int(rejected)
        for resource, quantity in amounts.items():
            before = balances[resource]
            delta = 0 if rejected else (quantity if kind == "grant" else -quantity)
            balances[resource] += delta
            if gaps[resource]:
                gaps_by_resource = phase_report["shortfalls"]
                gaps_by_resource[resource] = gaps_by_resource.get(resource, 0) + gaps[resource]
            rows.append({"Phase": phase, "Event": eid, "Action": kind, "Resource": resource,
                         "Opening": before, "Requested": quantity, "Applied change": delta,
                         "Shortfall": gaps[resource], "Closing": balances[resource],
                         "Status": "Blocked" if rejected else "Applied"})
    return {"summary": f"{blocked} of {len(events)} events were blocked spends. "
                       "A blocked spend leaves every balance unchanged.",
            "metrics": {"Events": len(events), "Blocked spends": blocked,
                        "Phases": len(phases), "Resources": len(balances)},
            "rows": rows, "closing_balances": balances, "phases": phases}
