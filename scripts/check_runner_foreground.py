#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "scripts" / "extension_smoke.py").read_text(encoding="utf-8")

required = [
    'game_page.bring_to_front()',
    '"--disable-background-timer-throttling"',
    '"--disable-renderer-backgrounding"',
    '"--disable-backgrounding-occluded-windows"',
    'game_visibility_before_run',
    'wall_seconds_elapsed',
]
missing = [item for item in required if item not in source]
assert not missing, f"Missing foreground-throttling safeguards: {missing}"
assert source.index("game_page.bring_to_front()") < source.index("game_page.wait_for_timeout(args.seconds * 1000)")
print("PASS: runner keeps the game tab foreground and records wall-clock timing")
