#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "scripts" / "extension_smoke.py").read_text(encoding="utf-8")
policy_source = (ROOT / "scripts" / "gift_skip_policy.py").read_text(encoding="utf-8")
combined_source = source + "\n" + policy_source

required = [
    'game_page.bring_to_front()',
    "type: 'GET_LOG'",
    'worker-memory',
    'storage-fallback',
    'log_source',
    '"--disable-background-timer-throttling"',
    '"--disable-renderer-backgrounding"',
    '"--disable-backgrounding-occluded-windows"',
    'game_visibility_before_run',
    'wall_seconds_elapsed',
    '--executable-path',
    'game_over_events',
    'snake collided / game over',
    'simulated game time did not reach the requested duration',
    'non_gift_pickups',
    'count_confirmed_turns(log_text)',
    'gift_expirations',
    'assess_expired_gift_skips(',
    'accepted_safe_gift_skips',
    'gift_skip_diagnostics',
    'MAX_ACCEPTED_NO_SAFE_ROUTE_SKIPS',
    'gift(s) expired without matching no-safe-route evidence',
    'exceed the allowance',
    'gift spawn/pickup/expiry accounting mismatch',
    'state.get("score") != len(gifts) * 500',
]
missing = [item for item in required if item not in combined_source]
assert not missing, f"Missing foreground-throttling safeguards: {missing}"
assert source.index("game_page.bring_to_front()") < source.index("game_page.wait_for_timeout(args.seconds * 1000)")
assert '"runner_version": "0.1.10"' in source, "Runner version is not 0.1.10"
print("PASS: runner foreground timing and objective gift-skip gate checks are present")
