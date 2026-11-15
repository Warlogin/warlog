#!/usr/bin/env python3
"""Negative control: a deliberately unsafe mock MV3 extension must FAIL the release gate.

This runs real Playwright + CDP in GitHub Actions, without exposing any private
extension ZIP. It cannot certify the actual Dobry Cola autopilot.
"""
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"tests"/"fixtures"/"mock-extension"


def main():
    with tempfile.TemporaryDirectory(prefix="mock-mv3-negative-") as d:
        tmp=Path(d)
        archive=tmp/"mock-extension.zip"
        report=tmp/"mock-report.json"
        with zipfile.ZipFile(archive,"w") as z:
            for p in FIXTURE.rglob("*"):
                if p.is_file():
                    z.write(p,str(p.relative_to(FIXTURE)))
        cmd=[
            sys.executable,str(ROOT/"scripts"/"extension_smoke.py"),
            "--extension-zip",str(archive),"--seconds","4",
            "--seed","2026","--scenario","edge-gifts",
            "--report",str(report)
        ]
        completed=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,text=True,timeout=90)
        if not report.is_file():
            raise AssertionError("No diagnostic report from actual mock MV3 extension run\n"+completed.stdout[-2500:])
        d=json.loads(report.read_text(encoding="utf-8"))
        requirements=[
            d.get("overall")=="failed",
            d.get("start",{}).get("ok") is True,
            d.get("cdp_commands",0)>=1,
            bool(d.get("game_over_events")),
            any("snake collided / game over" in x for x in d.get("failures",[])),
            d.get("log_source")=="worker-memory",
        ]
        if not all(requirements):
            summary={k:d.get(k) for k in [
                "runner_version","overall","stage","start","cdp_commands",
                "game_over_events","log_source","failures","error","traceback"]}
            raise AssertionError("Negative-control E2E contract failed\n"+
                json.dumps(summary,ensure_ascii=False,indent=2)+"\n"+
                completed.stdout[-2500:])
        print("PASS: synthetic MV3 START, actual CDP key, live log and expected Game Over correctly rejected")


if __name__=="__main__":
    main()
