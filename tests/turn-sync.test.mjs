import test from 'node:test';
import assert from 'node:assert/strict';
import { TurnSync, opposite, forwardDistance } from '../logic/turn-sync.mjs';

function newSync(options={}) {
 const t=new TurnSync({heading:'ArrowRight',...options});
 t.observe({x:747,y:261,timeMs:0});
 return t;
}
test('2026-11-16 incident: 1 px before turn must not dispatch',()=>{
 const t=newSync({estimatedDispatchLatencyMs:70});
 t.observe({x:786,y:261,timeMs:165});
 const r=t.propose({direction:'ArrowDown',point:{x:787,y:262},commandId:1321,timeMs:165});
 assert.equal(r.ok,false); assert.equal(r.reason,'insufficient-lead');
 assert.ok(r.requiredLeadPx>20);
});
test('a CDP acknowledgement does not confirm an actual turn',()=>{
 const t=newSync();
 const a=t.propose({direction:'ArrowDown',point:{x:787,y:262},commandId:1321,timeMs:0});
 assert.equal(a.ok,true);
 assert.equal(t.markSent({commandId:1321,timeMs:0}).ok,true);
 assert.equal(t.propose({direction:'ArrowUp',point:{x:827,y:262},commandId:1322,timeMs:10}).reason,'pending-turn');
 t.observe({x:767,y:261,timeMs:80});
 assert.notEqual(t.heading,'ArrowDown');
 assert.ok(t.pending);
 t.observe({x:789,y:261,timeMs:170});
 t.observe({x:825,y:261,timeMs:320});
 assert.equal(t.pending.phase,'overdue');
 assert.equal(t.holdForSafety,false); // Can still accept a delayed turn.
});
test('the delayed original turn confirms using actual displacement (not command receipt)',()=>{
 const t=newSync();
 t.propose({direction:'ArrowDown',point:{x:787,y:262},commandId:1321,timeMs:0});
 t.markSent({commandId:1321,timeMs:0});
 for (const p of [[767,261,80],[789,261,170],[825,261,320],[827,266,340],[827,274,380]]) {
   var result=t.observe({x:p[0],y:p[1],timeMs:p[2]});
 }
 assert.equal(result.phase,'confirmed');
 assert.equal(t.heading,'ArrowDown');
 assert.equal(t.pending,null);
 assert.equal(t.events.at(-1).type,'observed-turn-confirmed');
});
test('a pending turn is never superseded by a contradictory command',()=>{
 const t=newSync();
 t.propose({direction:'ArrowDown',point:{x:787,y:261},commandId:'a',timeMs:0});
 t.markSent({commandId:'a',timeMs:0});
 assert.equal(t.propose({direction:'ArrowUp',point:{x:827,y:261},commandId:'b',timeMs:1}).reason,'pending-turn');
 assert.equal(t.cancelUnsent('a'),false);
 assert.equal(t.pending.commandId,'a');
});
test('beyond one cell without confirmed turn requests safety hold',()=>{
 const t=newSync();
 t.propose({direction:'ArrowDown',point:{x:787,y:261},commandId:1,timeMs:0});
 t.markSent({commandId:1,timeMs:0});
 t.observe({x:806,y:261,timeMs:250});
 const result=t.observe({x:838,y:261,timeMs:400});
 assert.equal(result.phase,'safety-hold');
 assert.equal(t.propose({direction:'ArrowDown',point:{x:867,y:261},commandId:2,timeMs:410}).reason,'safety-hold');
});
test('reserve cannot be sent twice; unsent reservations are cancellable',()=>{
 const t=newSync();
 t.propose({direction:'ArrowDown',point:{x:787,y:261},commandId:1,timeMs:0});
 assert.equal(t.cancelUnsent(1),true);
 assert.equal(t.markSent({commandId:1,timeMs:3}).ok,false);
 assert.equal(t.pending,null);
});
test('reverse and far-away waypoints rejected; forward distance oriented correctly',()=>{
 const t=newSync();
 assert.equal(opposite('ArrowRight','ArrowLeft'),true);
 assert.equal(forwardDistance({x:10,y:5},{x:20,y:5},'ArrowRight'),10);
 assert.equal(t.propose({direction:'ArrowLeft',point:{x:787,y:261},commandId:1,timeMs:0}).reason,'reverse-turn');
 assert.equal(t.propose({direction:'ArrowUp',point:{x:947,y:261},commandId:2,timeMs:0}).reason,'turn-too-far');
});
test('no false positive from stationary/noisy 1px movement',()=>{
 const t=newSync();
 t.propose({direction:'ArrowDown',point:{x:787,y:261},commandId:1,timeMs:0});
 t.markSent({commandId:1,timeMs:0});
 t.observe({x:749,y:261,timeMs:10});
 t.observe({x:750,y:262,timeMs:15});
 assert.ok(t.pending);
 assert.equal(t.heading,'ArrowRight');
});
test('when game restarts, reset removes stale locks',()=>{
 const t=newSync();
 t.propose({direction:'ArrowDown',point:{x:787,y:261},commandId:1,timeMs:0});
 t.markSent({commandId:1,timeMs:0});
 t.reset({heading:'ArrowRight'});
 assert.equal(t.pending,null);
 assert.equal(t.holdForSafety,false);
});
