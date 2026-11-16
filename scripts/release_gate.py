"""Strict, explicit release gate for full MV3 extension smoke runs.

Offline unit tests and simulator browser-smoke are not a substitute for an
extension ZIP running inside Chromium. This gate only evaluates E2E evidence.
"""

CORNER_CELLS = {(0, 0), (17, 0), (17, 9), (0, 9)}
EDGE_SIDES = {"left", "right", "top", "bottom"}


def evaluate_release(result, gift_skip_failures=(), objective_skip_failures=()):
    failures = []
    state = result.get("state") or {}
    spawns = result.get("gift_spawns", 0)
    gifts = result.get("gift_pickups", 0)
    expirations = result.get("gift_expirations") or []
    active = result.get("active_gifts", 0)
    non_gifts = result.get("non_gift_pickups") or []
    confirmed_turns = result.get("confirmed_turns", 0)
    actual_turns = result.get("actual_turns", 0)
    duration = result.get("seconds_requested", 60)
    events = result.get("simulator_events") or []

    if result.get("start", {}).get("ok") is not True:
        failures.append("game start was not positively acknowledged")
    if result.get("page_errors"):
        failures.append("browser JavaScript errors")
    if result.get("cdp_commands", 0) < 1:
        failures.append("no confirmed CDP keyboard commands")
    if confirmed_turns < 1 or actual_turns < 1:
        failures.append("no confirmed direction change")
    if confirmed_turns != actual_turns:
        failures.append("confirmed turns differ from observed trajectory turns")
    if result.get("log_source") != "worker-memory":
        failures.append("live worker log unavailable; turn audit incomplete")
    # A planner may internally propose an opposite key while a target is
    # directly behind the head. The extension's reverse guard blocks it before
    # CDP, so this diagnostic alone is not a game reversal. Fail only when the
    # simulator actually receives and rejects an opposite-direction key.
    reverse_events = [
        event for event in events if event.get("kind") == "reverse-rejected"
    ]
    if reverse_events:
        failures.append("a reverse-direction key reached the game")
    if result.get("autopilot_abort"):
        failures.append("autopilot protective stop")
    if result.get("game_over_events") or state.get("mode") == "over":
        failures.append("snake collided / game over")
    if state.get("mode") != "playing":
        failures.append(f"unexpected final game mode: {state.get('mode')}")
    if state.get("time", 0) < duration * 1000 * 0.99:
        failures.append("simulated game time did not reach 99% of requested duration")
    if result.get("wall_seconds_elapsed", 0) < duration * 0.99:
        failures.append("wall-clock test duration was shorter than requested")
    if not gifts:
        failures.append("no gift was collected during the test")
    if non_gifts:
        failures.append(f"non-gift pickup detected: {non_gifts}")
    failures.extend(gift_skip_failures)
    failures.extend(objective_skip_failures)
    if spawns != gifts + len(expirations) + active:
        failures.append("gift spawn/pickup/expiry accounting mismatch")
    if state.get("score") != gifts * 500:
        failures.append("score does not match gift-only pickups")
    if duration >= 720 and state.get("score", 0) <= 70000:
        failures.append("12-minute run did not exceed 70000 points")
    if len(expirations) > 10:
        failures.append("more than ten expired gifts in the release test")

    if events:
        event_spawns = [
            e for e in events
            if e.get("kind") == "spawn" and e.get("type") == "gift"
        ]
        event_pickups = [
            e for e in events
            if e.get("kind") == "pickup" and e.get("type") == "gift"
        ]
        event_expirations = [
            e for e in events
            if e.get("kind") == "expire" and e.get("type") == "gift"
        ]
        if len(event_spawns) != spawns:
            failures.append("gift spawn count differs from simulator event history")
        if len(event_pickups) != gifts:
            failures.append("gift pickup count differs from simulator event history")
        if len(event_expirations) != len(expirations):
            failures.append("gift expiry count differs from simulator event history")

        spawned_cells = {
            ((e.get("cell") or {}).get("x", -1), (e.get("cell") or {}).get("y", -1))
            for e in event_spawns
        }
        scenario = result.get("scenario")
        if scenario == "corners":
            missing = CORNER_CELLS - spawned_cells
            if missing:
                failures.append(
                    "corner scenario did not exercise all four corners: "
                    + ", ".join(f"({x},{y})" for x, y in sorted(missing))
                )
        if scenario == "edge-gifts" and duration >= 180:
            sides = set()
            for x, y in spawned_cells:
                if x == 0:
                    sides.add("left")
                if x == 17:
                    sides.add("right")
                if y == 0:
                    sides.add("top")
                if y == 9:
                    sides.add("bottom")
            missing_sides = EDGE_SIDES - sides
            if missing_sides:
                failures.append(
                    "long edge scenario did not exercise all four edges: "
                    + ", ".join(sorted(missing_sides))
                )
    return failures
