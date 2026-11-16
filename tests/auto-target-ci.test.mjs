import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source=fs.readFileSync(new URL('../extensions/ice-snake/auto-target.js',import.meta.url),'utf8');
const sandbox={};sandbox.globalThis=sandbox;
vm.runInNewContext(source,sandbox,{filename:'auto-target.js'});
const A=sandbox.IceSnakeAutoTarget;

test('module exported from exact extension source',()=>assert.equal(typeof A.targetStatus,'function'));
test('default target 72000 +/- 500',()=>assert.equal(JSON.stringify(A.normalizeSettings({})),JSON.stringify({targetScore:72000,tolerance:500,autoResume:true,autoRestart:true})));
for(const [score,expected] of [[71499,false],[71500,true],[72000,true],[72500,true],[72501,true]]) {
 test('goal reached at '+score+' => '+expected,()=>assert.equal(A.targetStatus(score,A.DEFAULTS).reached,expected));
}
test('overshoot is separately reported',()=>{
 assert.equal(A.targetStatus(72501,A.DEFAULTS).overshoot,true);
 assert.equal(A.targetStatus(72500,A.DEFAULTS).withinRange,true);
});
test('zero tolerance obeyed',()=>assert.equal(A.targetStatus(71999,{targetScore:72000,tolerance:0}).reached,false));
test('custom target and tolerance',()=>assert.equal(A.targetStatus(79000,{targetScore:80000,tolerance:1000}).reached,true));
test('bad input cannot yield unrestricted targeting',()=>{for(const x of [Infinity,-500,0,NaN,'bad',1000001])assert.equal(A.normalizeSettings({targetScore:x}).targetScore,72000)});
test('configuration uses boolean toggles only',()=>assert.equal(A.normalizeSettings({autoRestart:'false'}).autoRestart,true));
test('restart delays increase but are capped',()=>{
 const now=100000;
 assert.equal(A.restartDelayMs([],now),1400);
 let prev=0;for(let count=1;count<20;count++) {
  const next=A.restartDelayMs(Array(count).fill(now-1000),now);
  assert.ok(next>=prev);prev=next;
 }
 assert.equal(prev,30000);
});
test('old retries expire after a minute',()=>assert.equal(A.restartDelayMs([100],200000),1400));
