#!/usr/bin/env python3
"""Run a genuine MV3 extension and CDP input against the lab Canvas in Chromium.

No original extension source is stored or published in this lab. Pass an existing
ZIP locally using --extension-zip. Temporary source patch changes ONLY URL
permissions/routing and banner text; not bot planning or timing algorithms.
"""
import argparse
import json
import re
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def log_message(self,*args):pass

def patch(extension,base,origin):
    manifest_path=extension/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['host_permissions']=[f'{origin}/games/snake/*']
    for script in manifest.get('content_scripts',[]):
        script['matches']=[f'{origin}/games/snake/*']
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    for filename in ['worker.js','popup.js']:
        path=extension/filename
        contents=path.read_text(encoding='utf-8')
        contents=contents.replace('https://dobrycola-promo.ru/games/snake/',base)
        path.write_text(contents,encoding='utf-8')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--extension-zip',required=True,type=Path,help='Local extension archive to evaluate; never uploaded by this script')
    parser.add_argument('--seconds',type=int,default=18,help='Length of actual browser session (default 18s)')
    parser.add_argument('--seed',type=int,default=2026)
    parser.add_argument('--scenario',choices=['mixed','edge-gifts','corners'],default='edge-gifts')
    parser.add_argument('--report',type=Path,default=Path('extension-smoke-report.json'))
    args=parser.parse_args()
    if not args.extension_zip.is_file():parser.error('ZIP not found')
    with tempfile.TemporaryDirectory(prefix='ice-snake-lab-') as folder, ThreadingHTTPServer(('127.0.0.1',0),Handler) as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        origin=f'http://127.0.0.1:{server.server_port}'
        base=f'{origin}/games/snake/'
        with zipfile.ZipFile(args.extension_zip) as z:
            if any(n.startswith('/') or '..' in Path(n).parts for n in z.namelist()):raise ValueError('ZIP has unsafe path')
            z.extractall(folder)
        choices=list(Path(folder).rglob('manifest.json'))
        if len(choices)!=1:raise RuntimeError('Expected one Chrome extension manifest in archive')
        ext=choices[0].parent
        patch(ext,base,origin)
        url=f'{base}?seed={args.seed}&scenario={args.scenario}'
        with sync_playwright() as p:
            context=p.chromium.launch_persistent_context(
                user_data_dir=str(Path(folder)/'chromium-profile'),channel='chromium',headless=True,
                args=[f'--disable-extensions-except={ext}',f'--load-extension={ext}'],viewport={'width':1360,'height':960})
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url,wait_until='domcontentloaded')
            page.wait_for_function('window.__ICE_SNAKE_LAB__?.isSimulator===true',timeout=10000)
            for _ in range(30):
                if context.service_workers:break
                page.wait_for_timeout(200)
            if not context.service_workers:raise RuntimeError('MV3 service worker did not start; Chrome may prohibit extensions')
            worker=context.service_workers[0]
            # Ask the real extension worker to start, just as popup.js does.
            start=worker.evaluate('''async () => {
              const tabs = await chrome.tabs.query({});
              const tab=tabs.find(t=>t.url?.includes('/games/snake/'));
              if(!tab)throw new Error('game tab not found');
              return await chrome.runtime.sendMessage({type:'START',tabId:tab.id});
            }''')
            if not start or not start.get('ok'):raise RuntimeError(f'Extension START failed: {start}')
            page.wait_for_timeout(args.seconds*1000)
            # Read only the extension's own log; the lab's fixture API is a diagnostic truth source.
            log=worker.evaluate('''async () => {
              const x=await chrome.storage.local.get(['lastSnakeLog','lastSnakeStatus']);
              return {log:x.lastSnakeLog||'',status:x.lastSnakeStatus||''};
            }''')
            state=page.evaluate('window.__ICE_SNAKE_LAB__.snapshot()')
            events=page.evaluate('window.__ICE_SNAKE_LAB__.events()')
            result={'extension':args.extension_zip.name,'seed':args.seed,'scenario':args.scenario,
              'seconds':args.seconds,'start':start,'state':state,'status':log['status'],
              'cdp_commands':log['log'].count('ВВОД ПОДТВЕРЖДЁН CDP'),
              'reverse_guard':log['log'].count('ЗАЩИТА ОТ РАЗВОРОТА'),
              'autopilot_abort':('Защитная остановка' in log['log']),
              'simulator_events':events[-200:],'page_errors':errors,'extension_log_tail':log['log'][-16000:]}
            args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({k:result[k] for k in ['extension','seed','scenario','seconds','status','cdp_commands','reverse_guard','autopilot_abort']},ensure_ascii=False))
            context.close();server.shutdown()
            if errors:raise RuntimeError('Browser JS errors: '+str(errors))
            if result['cdp_commands']<1:raise RuntimeError('No genuine CDP keypresses observed: check extension log in report')
            if result['autopilot_abort']:raise RuntimeError('Autopilot protective stop; inspect report')

if __name__=='__main__':main()