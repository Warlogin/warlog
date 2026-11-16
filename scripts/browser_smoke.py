#!/usr/bin/env python3
"""Playwright visual browser smoke: actual Canvas and keyboard, not a stub."""
import argparse
import json
import os
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def log_message(self,*args):pass

def run():
    with ThreadingHTTPServer(('127.0.0.1',0),Handler) as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}/games/snake/?scenario=edge-gifts&seed=2026&spawnMs=10000'
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chromium',headless=True)
            page=browser.new_page(viewport={'width':1300,'height':950})
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url,wait_until='networkidle')
            page.wait_for_function('window.__ICE_SNAKE_LAB__?.isSimulator===true')
            assert page.locator('#snakeCanvas').count()==1
            assert page.locator('#play').inner_text()=='Играть'
            page.locator('#play').click()
            page.wait_for_function("window.__ICE_SNAKE_LAB__.snapshot().mode==='playing'")
            page.evaluate("window.__ICE_SNAKE_LAB__.forceGift(8,5)")
            page.wait_for_function("window.__ICE_SNAKE_LAB__.snapshot().score >= 500",timeout=2500)
            assert page.locator('#score').inner_text()=='500'
            # Don't let the snake run head-first into a wall: turn upward before x=914.
            page.keyboard.press('ArrowUp')
            page.wait_for_function("window.__ICE_SNAKE_LAB__.snapshot().direction==='ArrowUp'",timeout=2500)
            page.keyboard.press('Space')
            page.wait_for_function("window.__ICE_SNAKE_LAB__.snapshot().mode==='paused'",timeout=2500)
            position=page.evaluate('window.__ICE_SNAKE_LAB__.snapshot().head')
            page.wait_for_timeout(250)
            assert page.evaluate('window.__ICE_SNAKE_LAB__.snapshot().head')==position
            assert not errors,errors
            print(json.dumps({'ok':True,'url':url,'score':500,'turn':'ArrowUp','pause':'verified','js_errors':0},ensure_ascii=False))
            browser.close()
        server.shutdown()

if __name__=='__main__':
    try:run()
    except Exception as exc:
        print(f'BROWSER SMOKE NOT PASSED: {exc}',file=sys.stderr)
        raise