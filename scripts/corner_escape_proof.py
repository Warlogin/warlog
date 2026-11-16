"""Independent diagnostics for objectively unavoidable corner gift skips.

This checks simulator event history, NOT the autopilot's own verdict. It
classifies skips as independently proven or unproven. Under the current release
rule, proof is diagnostic only: up to ten total expired gifts are allowed.
"""

COLS = 18
ROWS = 10


def _cell(event):
    cell = event.get("cell") or {}
    try:
        return (int(cell["x"]), int(cell["y"]))
    except (KeyError, TypeError, ValueError):
        return None


def _time(event):
    try:
        return float(event["time"])
    except (KeyError, TypeError, ValueError):
        return None


def _girl_present_throughout(neighbor, start_ms, end_ms, events):
    spawns = [
        _time(e) for e in events
        if e.get("kind") == "spawn" and e.get("type") == "girl"
        and _cell(e) == neighbor and _time(e) is not None
        and _time(e) <= start_ms
    ]
    if not spawns:
        return False
    latest_spawn = max(spawns)
    for event in events:
        t = _time(event)
        if t is None or t <= latest_spawn or t > end_ms:
            continue
        if event.get("kind") == "reset":
            return False
        if event.get("kind") in ("pickup", "expire") and event.get("type") == "girl":
            return False
    return True


def prove_corner_trap(cell, start_ms, end_ms, events):
    """Return an objective geometric proof, or None when not independently proved."""
    if cell is None or start_ms is None or end_ms is None or start_ms > end_ms:
        return None
    x, y = cell
    if x not in (0, COLS - 1) or y not in (0, ROWS - 1):
        return None
    neighbors = [
        (nx, ny) for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
        if 0 <= nx < COLS and 0 <= ny < ROWS
    ]
    if len(neighbors) != 2:
        return None
    blocked = [pt for pt in neighbors if _girl_present_throughout(pt, start_ms, end_ms, events)]
    if not blocked:
        return None
    return {
        "reason": "corner_has_no_nonreversing_exit_without_girl_pickup",
        "blocked_neighbors": [{"x": bx, "y": by} for bx, by in blocked],
        "free_neighbor_count": len(neighbors) - len(blocked),
        "assumptions": [
            "no_180_degree_reversal",
            "no_wall_wrap",
            "girl_pickup_forbidden",
            "girl_present_for_entire_gift_lifetime",
        ],
    }


def audit_objective_gift_skips(expirations, gift_spawns, events):
    """Audit expired gifts independently of planner no-safe-route messages."""
    audits, failures = [], []
    for expiry in expirations:
        cell = _cell(expiry)
        ended = _time(expiry)
        prior = [
            _time(e) for e in gift_spawns
            if e.get("kind") == "spawn" and e.get("type") == "gift"
            and _cell(e) == cell and _time(e) is not None and ended is not None
            and _time(e) <= ended
        ]
        started = max(prior) if prior else None
        proof = prove_corner_trap(cell, started, ended, events)
        label = {"x": cell[0], "y": cell[1]} if cell else expiry.get("cell")
        audits.append({
            "cell": label,
            "classification": "independently_proven" if proof else "not_independently_proven",
            "proof": proof,
        })
        # Unproven skips remain visible in the report but count only toward the total skip budget.
    return audits, failures
