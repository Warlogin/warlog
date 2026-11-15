"""Strict, explicit release gate for full MV3 extension smoke runs.

Offline unit tests and simulator browser-smoke are not a substitute for an
extension ZIP running inside Chromium. This gate only evaluates E2E evidence.
"""


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
    if result.get("reverse_guard", 0):
        failures.append("reverse guard rejected a queued direction")
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
    if len(expirations) > 2:
        failures.append("more than two expired gifts in a 60-second release test")
    return failures
