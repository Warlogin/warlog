"""Classify expired gifts using target-specific no-safe-route evidence from the extension log."""
from datetime import datetime
import re

MAX_ACCEPTED_NO_SAFE_ROUTE_SKIPS = 2
GRID_ORIGIN_X = 234
GRID_ORIGIN_Y = 144
GRID_STEP = 40

NO_SAFE_ROUTE_RE = re.compile(
    r"ЦЕЛИ:\s*gift@(?P<x>-?\d+),(?P<y>-?\d+)\s*\+500;.*?причина=no-safe-route"
)
LOG_TIME_RE = re.compile(r"^(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})\b")


def _elapsed_ms(line, started_at):
    match = LOG_TIME_RE.match(line)
    if not match or not started_at:
        return None
    try:
        started = datetime.fromisoformat(started_at)
    except (TypeError, ValueError):
        return None
    start_seconds = started.hour * 3600 + started.minute * 60 + started.second
    line_seconds = (
        int(match.group("hour")) * 3600
        + int(match.group("minute")) * 60
        + int(match.group("second"))
    )
    delta = (line_seconds - start_seconds) % 86400
    if delta > 43200:
        delta -= 86400
    return delta * 1000


def assess_expired_gift_skips(expirations, spawn_events, log_text, started_at):
    """Classify skips; only exact-cell, in-lifetime no-safe-route evidence counts."""
    evidence_by_target = {}
    for line in (log_text or "").splitlines():
        match = NO_SAFE_ROUTE_RE.search(line)
        if not match:
            continue
        elapsed = _elapsed_ms(line, started_at)
        if elapsed is None:
            continue
        target = (int(match.group("x")), int(match.group("y")))
        evidence_by_target.setdefault(target, []).append(
            {"elapsed_ms": elapsed, "time": line[:8]}
        )

    spawn_times_by_cell = {}
    for event in spawn_events or []:
        cell = event.get("cell") or {}
        try:
            key = (int(cell["x"]), int(cell["y"]))
            spawn_time = float(event["time"])
        except (KeyError, TypeError, ValueError):
            continue
        spawn_times_by_cell.setdefault(key, []).append(spawn_time)

    diagnostics = []
    for expiration in expirations or []:
        cell = expiration.get("cell") or {}
        try:
            key = (int(cell["x"]), int(cell["y"]))
            expiry_ms = float(expiration["time"])
        except (KeyError, TypeError, ValueError):
            diagnostics.append({
                "cell": cell,
                "classification": "unjustified_expiry",
                "reason": "missing-expiry-cell-or-time",
                "evidence_count": 0,
                "evidence_times": [],
            })
            continue

        target_pixel = {
            "x": GRID_ORIGIN_X + GRID_STEP * key[0],
            "y": GRID_ORIGIN_Y + GRID_STEP * key[1],
        }
        prior_spawns = [
            value for value in spawn_times_by_cell.get(key, [])
            if value <= expiry_ms
        ]
        spawn_ms = max(prior_spawns) if prior_spawns else None
        matching_evidence = []
        if spawn_ms is not None:
            for item in evidence_by_target.get(
                (target_pixel["x"], target_pixel["y"]), []
            ):
                # Log timestamps have one-second precision.
                if spawn_ms - 1000 <= item["elapsed_ms"] <= expiry_ms + 1000:
                    matching_evidence.append(item)

        evidence_times = sorted({item["time"] for item in matching_evidence})
        justified = bool(matching_evidence)
        diagnostics.append({
            "cell": {"x": key[0], "y": key[1]},
            "target_pixel": target_pixel,
            "spawn_time_ms": spawn_ms,
            "expiry_time_ms": expiry_ms,
            "classification": "accepted_no_safe_route" if justified else "unjustified_expiry",
            "reason": "no-safe-route" if justified else "missing-matching-no-safe-route-evidence",
            "evidence_count": len(matching_evidence),
            "evidence_times": evidence_times,
        })

    accepted = sum(item["classification"] == "accepted_no_safe_route" for item in diagnostics)
    unjustified = sum(item["classification"] == "unjustified_expiry" for item in diagnostics)
    failures = []
    if unjustified:
        failures.append(
            f"{unjustified} gift(s) expired without matching no-safe-route evidence"
        )
    if accepted > MAX_ACCEPTED_NO_SAFE_ROUTE_SKIPS:
        failures.append(
            f"{accepted} objectively blocked gift skip(s) exceed the allowance "
            f"of {MAX_ACCEPTED_NO_SAFE_ROUTE_SKIPS}"
        )
    return diagnostics, accepted, failures
