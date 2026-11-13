#!/usr/bin/env python3
"""Run a real MV3 extension against the Ice Snake Lab in Chromium.

The user's extension ZIP stays local. Only URL permissions/routing are patched in
a temporary extraction; planner, timing, and movement code are not changed.
A temporary extension-origin probe page sends START and reads chrome.storage.local,
so the runner never depends on a potentially terminated Playwright Worker handle.
A JSON report is written on success AND on every handled failure.
"""
import argparse
import json
import os
import re
import sys
import tempfile
import threading
import time
import traceback
import zipfile
from pathlib import Path, PurePosixPath
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
GAME_URL_MARKER = "https://dobrycola-promo.ru/games/snake/"

# Count only observed trajectory changes, not the earlier CDP/browser acknowledgement.
# Keep the legacy generic message for older extension builds.
CONFIRMED_TURN_RE = re.compile(
    r"ПОВОРОТ ПОДТВЕРЖДЁН(?: ПО ТРАЕКТОРИИ)?:\\s*"
    r"(?:ArrowUp|ArrowDown|ArrowLeft|ArrowRight)\\b"
)


def count_confirmed_turns(log_text: str) -> int:
    return len(CONFIRMED_TURN_RE.findall(log_text))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


PROBE_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Ice Snake Lab extension bridge</title></head>
<body><pre id="result">bridge-ready</pre><script src="ice-snake-lab-probe.js"></script></body></html>
"""

PROBE_JS = r"""
(() => {
  const result = document.getElementById('result');
  const send = (message) => new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, response => {
      const err = chrome.runtime.lastError;
      if (err) reject(new Error(err.message));
      else resolve(response);
    });
  });
  window.ICE_SNAKE_LAB_PROBE = {
    extensionId: chrome.runtime.id,
    async start() {
      const tabs = await chrome.tabs.query({});
      const tab = tabs.find(t => t.url && t.url.includes('/games/snake/'));
      if (!tab) throw new Error('Game tab not found in chrome.tabs.query');
      const response = await send({type: 'START', tabId: tab.id});
      result.textContent = JSON.stringify({stage: 'start-response', response});
      return response;
    },
    async readLog() {
      const data = await chrome.storage.local.get(null);
      const entries = Object.entries(data);
      const textEntries = entries.filter(([, value]) => typeof value === 'string');
      const preferredLog = data.lastSnakeLog || data.snakeLog || data.log || '';
      const fallbackLog = textEntries
        .filter(([key, value]) => /log|journal|diagnostic/i.test(key) || /АВТОПИЛОТ|CDP|ПОДТВЕРЖДЁН|ЗАЩИТА/.test(value))
        .map(([key, value]) => '[' + key + ']\\n' + value).join('\\n');
      return {
        log: preferredLog || fallbackLog,
        status: data.lastSnakeStatus || data.snakeStatus || data.status || '',
        storage_keys: Object.keys(data)
      };
    }
  };
  result.textContent = 'bridge-ready:' + chrome.runtime.id;
})();
"""


def atomic_report(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def safe_extract(zip_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            member = PurePosixPath(name)
            if member.is_absolute() or ".." in member.parts or (member.parts and ":" in member.parts[0]):
                raise ValueError(f"Unsafe path in extension ZIP: {name}")
        archive.extractall(destination)
    manifests = list(destination.rglob("manifest.json"))
    if len(manifests) != 1:
        raise RuntimeError(f"Expected exactly one manifest.json, found {len(manifests)}")
    return manifests[0].parent


def patch_extension(extension: Path, base_url: str, origin: str) -> dict:
    manifest_path = extension / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    local_pattern = f"{origin}/games/snake/*"
    manifest["host_permissions"] = [local_pattern]
    for entry in manifest.get("content_scripts", []):
        entry["matches"] = [local_pattern]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    replaced_files = []
    for path in extension.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".js", ".html", ".json"}:
            if path.name == "manifest.json":
                continue
            try:
                original = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            updated = original.replace(GAME_URL_MARKER, base_url)
            if updated != original:
                path.write_text(updated, encoding="utf-8")
                replaced_files.append(str(path.relative_to(extension)))

    # A temporary extension-origin bridge page invokes the same START message
    # as the popup. It does not alter worker.js, planner code, or key timings.
    (extension / "ice-snake-lab-probe.html").write_text(PROBE_HTML, encoding="utf-8")
    (extension / "ice-snake-lab-probe.js").write_text(PROBE_JS, encoding="utf-8")

    popup = (
        manifest.get("action", {}).get("default_popup")
        or manifest.get("browser_action", {}).get("default_popup")
    )
    return {
        "manifest_version": manifest.get("manifest_version"),
        "service_worker": manifest.get("background", {}).get("service_worker"),
        "default_popup": popup,
        "url_replacements": replaced_files,
        "local_match": local_pattern,
    }


def extension_id_from_workers(context, timeout_seconds=12):
    deadline = time.monotonic() + timeout_seconds
    seen_urls = []
    while time.monotonic() < deadline:
        try:
            workers = list(context.service_workers)
        except Exception:
            workers = []
        for worker in workers:
            url = getattr(worker, "url", "")
            if url:
                seen_urls.append(url)
                match = re.match(r"chrome-extension://([a-p]{32})/", url)
                if match:
                    return match.group(1), seen_urls
        time.sleep(0.2)
    raise RuntimeError(
        "Could not discover the extension ID from its MV3 service worker. "
        f"Observed worker URLs: {seen_urls}"
    )


def start_http_server():
    server = QuietThreadingHTTPServer(("127.0.0.1", 0), Handler)
    stop_requested = threading.Event()
    server_errors = []

    def serve():
        try:
            server.serve_forever(poll_interval=0.1)
        except OSError as exc:
            if not stop_requested.is_set():
                server_errors.append(repr(exc))

    thread = threading.Thread(target=serve, name="ice-snake-lab-http", daemon=True)
    thread.start()
    return server, thread, stop_requested, server_errors


def stop_http_server(server, thread, stop_requested, server_errors):
    if server is None:
        return
    stop_requested.set()
    try:
        # shutdown() must be called from a thread other than serve_forever().
        server.shutdown()
    except OSError as exc:
        server_errors.append(f"shutdown: {exc!r}")
    finally:
        thread.join(timeout=5)
        try:
            server.server_close()
        except OSError as exc:
            server_errors.append(f"server_close: {exc!r}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--extension-zip", required=True, type=Path,
        help="Local extension archive; it is never uploaded by this script"
    )
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument(
        "--scenario", choices=["mixed", "edge-gifts", "corners"], default="edge-gifts"
    )
    parser.add_argument("--report", type=Path, default=Path("extension-smoke-report.json"))
    parser.add_argument("--headed", action="store_true", help="Show Chromium while testing")
    parser.add_argument("--executable-path", type=Path, help="Optional installed Chromium/Chrome binary")
    args = parser.parse_args()

    report_path = args.report.expanduser().resolve()
    result = {
        "runner_version": "0.1.6",
        "overall": "running",
        "stage": "initializing",
        "extension": args.extension_zip.name,
        "extension_zip": str(args.extension_zip.expanduser().resolve()),
        "seconds_requested": args.seconds,
        "seed": args.seed,
        "scenario": args.scenario,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "start": None,
        "cdp_commands": 0,
        "confirmed_turns": 0,
        "reverse_guard": 0,
        "gift_pickups": 0,
        "non_gift_pickups": [],
        "autopilot_abort": False,
        "extension_log_tail": "",
        "simulator_events": [],
        "page_errors": [],
        "console_errors": [],
        "server_errors": [],
    }
    atomic_report(report_path, result)

    server = thread = stop_requested = None
    server_errors = []
    context = game_page = probe_page = None

    try:
        if not args.extension_zip.expanduser().is_file():
            raise FileNotFoundError(f"Extension ZIP not found: {args.extension_zip}")
        if args.seconds < 1:
            raise ValueError("--seconds must be >= 1")

        with tempfile.TemporaryDirectory(prefix="ice-snake-lab-") as folder:
            temp_root = Path(folder)
            result["stage"] = "extract-extension"
            extension = safe_extract(args.extension_zip.expanduser().resolve(), temp_root / "extension")
            server, thread, stop_requested, server_errors = start_http_server()
            origin = f"http://127.0.0.1:{server.server_port}"
            base_url = f"{origin}/games/snake/"
            result["game_url"] = f"{base_url}?seed={args.seed}&scenario={args.scenario}"
            result["extension_folder"] = str(extension)
            result["patch"] = patch_extension(extension, base_url, origin)
            atomic_report(report_path, result)

            result["stage"] = "launch-chromium"
            with sync_playwright() as playwright:
                launch_args = [
                    f"--disable-extensions-except={extension}",
                    f"--load-extension={extension}",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows",
                ]
                if os.name != "nt":
                    launch_args.extend(["--no-sandbox", "--disable-dev-shm-usage"])
                launch_options = {
                    "user_data_dir": str(temp_root / "chromium-profile"),
                    "headless": not args.headed,
                    "args": launch_args,
                    "viewport": {"width": 1360, "height": 960},
                }
                if args.executable_path:
                    launch_options["executable_path"] = str(args.executable_path.expanduser().resolve())
                else:
                    launch_options["channel"] = "chromium"
                context = playwright.chromium.launch_persistent_context(**launch_options)
                game_page = context.new_page()
                def record_page_error(page_name, exc):
                    result.setdefault("page_errors", []).append({
                        "page": page_name,
                        "message": getattr(exc, "message", str(exc)),
                        "stack": getattr(exc, "stack", None) or str(exc),
                    })
                def record_console_error(page_name, message):
                    if message.type == "error" and "favicon.ico" not in message.text:
                        result.setdefault("console_errors", []).append({
                            "page": page_name,
                            "text": message.text,
                            "location": message.location,
                        })
                game_page.on("pageerror", lambda exc: record_page_error("game", exc))
                game_page.on("console", lambda message: record_console_error("game", message))
                game_page.goto(result["game_url"], wait_until="domcontentloaded")
                game_page.wait_for_function(
                    "window.__ICE_SNAKE_LAB__?.isSimulator === true", timeout=15000
                )
                result["stage"] = "discover-extension"
                extension_id, worker_urls = extension_id_from_workers(context)
                result["extension_id"] = extension_id
                result["service_worker_urls"] = worker_urls
                atomic_report(report_path, result)

                result["stage"] = "open-extension-bridge"
                probe_page = context.new_page()
                probe_page.on("pageerror", lambda exc: record_page_error("extension-bridge", exc))
                probe_page.on("console", lambda message: record_console_error("extension-bridge", message))
                probe_url = f"chrome-extension://{extension_id}/ice-snake-lab-probe.html"
                probe_page.goto(probe_url, wait_until="domcontentloaded")
                probe_page.wait_for_function(
                    "window.ICE_SNAKE_LAB_PROBE?.extensionId", timeout=10000
                )
                result["probe_page"] = probe_url

                result["stage"] = "send-start"
                start = probe_page.evaluate("window.ICE_SNAKE_LAB_PROBE.start()")
                result["start"] = start
                if not start or not start.get("ok"):
                    raise RuntimeError(f"Extension START was not acknowledged: {start}")
                atomic_report(report_path, result)

                result["stage"] = "run-game"
                # The extension bridge is a second tab. Keep the game tab foreground:
                # Chromium can throttle requestAnimationFrame in background tabs.
                game_page.bring_to_front()
                result["game_visibility_before_run"] = game_page.evaluate(
                    "document.visibilityState"
                )
                wall_started = time.monotonic()
                game_page.wait_for_timeout(args.seconds * 1000)
                result["wall_seconds_elapsed"] = round(time.monotonic() - wall_started, 3)
                result["game_visibility_after_run"] = game_page.evaluate(
                    "document.visibilityState"
                )

                result["stage"] = "read-extension-log"
                log_data = probe_page.evaluate("window.ICE_SNAKE_LAB_PROBE.readLog()")
                state = game_page.evaluate("window.__ICE_SNAKE_LAB__.snapshot()")
                events = game_page.evaluate("window.__ICE_SNAKE_LAB__.events()")
                log_text = log_data.get("log") or ""
                pickups = [event for event in events if event.get("kind") == "pickup"]
                gifts = [event for event in pickups if event.get("type") == "gift"]
                non_gifts = [event.get("type") for event in pickups if event.get("type") != "gift"]
                game_overs = [event for event in events if event.get("kind") == "game-over"]
                actual_turns = [event for event in events if event.get("kind") == "turn"]
                confirmed_turns = count_confirmed_turns(log_text)
                autopilot_abort = (
                    "Защитная остановка" in log_text
                    or "ЗАЩИТНАЯ ОСТАНОВКА" in log_text
                    or "planner-requested-180-degree-turn" in log_text
                )
                result.update({
                    "state": state,
                    "status": log_data.get("status") or "",
                    "storage_keys": log_data.get("storage_keys", []),
                    "cdp_commands": log_text.count("ВВОД ПОДТВЕРЖДЁН CDP"),
                    "confirmed_turns": confirmed_turns,
                    "reverse_guard": log_text.count("ЗАЩИТА ОТ РАЗВОРОТА"),
                    "autopilot_abort": autopilot_abort,
                    "gift_pickups": len(gifts),
                    "non_gift_pickups": non_gifts,
                    "actual_turns": len(actual_turns),
                    "game_over_events": game_overs,
                    "simulator_events": events[-300:],
                    "extension_log_tail": log_text[-24000:],
                })

                failures = []
                if result["page_errors"]:
                    failures.append("browser JavaScript errors")
                if result["cdp_commands"] < 1:
                    failures.append("no confirmed CDP keyboard commands")
                if result["confirmed_turns"] < 1 or result["actual_turns"] < 1:
                    failures.append("no confirmed direction change")
                if result["autopilot_abort"]:
                    failures.append("autopilot protective stop")
                if game_overs or state.get("mode") == "over":
                    failures.append("snake collided / game over")
                if state.get("mode") != "playing":
                    failures.append(f"unexpected final game mode: {state.get('mode')}")
                if state.get("time", 0) < args.seconds * 1000 * 0.85:
                    failures.append("simulated game time did not reach the requested duration")
                if not gifts:
                    failures.append("no gift was collected during the test")
                if non_gifts:
                    failures.append(f"non-gift pickup detected: {non_gifts}")
                if state.get("score") != len(gifts) * 500:
                    failures.append("score does not match gift-only pickups")
                result["overall"] = "failed" if failures else "passed"
                result["failures"] = failures
                result["error"] = "; ".join(failures) if failures else None
                result["stage"] = "completed"
                atomic_report(report_path, result)
                print(json.dumps({
                    key: result.get(key) for key in [
                        "overall", "extension", "seconds_requested", "scenario", "seed",
                        "cdp_commands", "confirmed_turns", "actual_turns", "gift_pickups",
                        "non_gift_pickups", "autopilot_abort", "state", "failures", "error"
                    ]
                }, ensure_ascii=False, indent=2))

    except Exception as exc:
        result["overall"] = "blocked" if "ERR_BLOCKED_BY_ADMINISTRATOR" in str(exc) else "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()
        # Best-effort diagnostics even if startup failed after a page was created.
        try:
            if probe_page and not probe_page.is_closed():
                result["probe_log_on_failure"] = probe_page.evaluate(
                    "window.ICE_SNAKE_LAB_PROBE?.readLog?.()"
                )
        except Exception as read_exc:
            result["probe_read_error"] = repr(read_exc)
        try:
            if game_page and not game_page.is_closed():
                result["state_on_failure"] = game_page.evaluate(
                    "window.__ICE_SNAKE_LAB__?.snapshot?.()"
                )
                result["events_on_failure"] = game_page.evaluate(
                    "window.__ICE_SNAKE_LAB__?.events?.()"
                )
        except Exception as read_exc:
            result["simulator_read_error"] = repr(read_exc)
        print(
            f"EXTENSION SMOKE FAILED at stage '{result.get('stage')}': {result['error']}",
            file=sys.stderr,
        )
        print(f"Diagnostic report saved to: {report_path}", file=sys.stderr)
        print(result["traceback"], file=sys.stderr)

    finally:
        # Exiting the sync_playwright context already closes Chromium. Do not
        # call context.close() again after Playwright has torn down its pipe.
        stop_http_server(server, thread, stop_requested, server_errors)
        result["server_errors"] = server_errors
        result["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        if result.get("overall") == "running":
            result["overall"] = "failed"
            result["error"] = result.get("error") or "Test ended before completion"
        atomic_report(report_path, result)

    if result["overall"] != "passed":
        sys.exit(1)
    if result.get("cleanup_errors") or result.get("server_errors"):
        print("WARNING: test completed, but cleanup reported warnings", file=sys.stderr)


if __name__ == "__main__":
    main()
