import test from 'node:test';
import assert from 'node:assert/strict';
import { TurnSync, perpendicular } from '../logic/turn-sync.mjs';

const dirs = {
  ArrowUp: [0,-1], ArrowRight:[1,0], ArrowDown:[0,1], ArrowLeft:[-1,0]
};
const add=(p,d,n)=>({x:p.x+dirs[d][0]*n,y:p.y+dirs[d][1]*n});

for(const from of Object.keys(dirs)) {
 for(const to of Object.keys(dirs).filter(to=>perpendicular(from,to))) {
   test('observed confirmation: '+from+' => '+to,()=>{
     const origin={x:510,y:340};
     const point=add(origin,from,40);
     const sync=new TurnSync({heading:from});
     sync.observe({...origin,timeMs:0});
     assert.equal(sync.propose({direction:to,point,commandId:from+'/'+to,timeMs:0}).ok,true);
     sync.markSent({commandId:from+'/'+to,timeMs:0});
     const p1=add(origin,from,30);
     const p2=point;
     const p3=add(point,to,4);
     const p4=add(point,to,10);
     for (const [i,p] of [p1,p2,p3,p4].entries()) {
       var result=sync.observe({...p,timeMs:(i+1)*100});
     }
     assert.equal(result.phase,'confirmed');
     assert.equal(sync.heading,to);
     assert.equal(sync.pending,null);
   });
 }
}

for (const corner of [
 {name:'top-left',from:'ArrowUp',to:'ArrowRight',target:{x:232,y:222}},
 {name:'top-right',from:'ArrowUp',to:'ArrowLeft',target:{x:906,y:222}},
 {name:'bottom-left',from:'ArrowDown',to:'ArrowRight',target:{x:232,y:499}},
 {name:'bottom-right',from:'ArrowDown',to:'ArrowLeft',target:{x:906,y:499}}
]) {
 test('corner motion confirmation: '+corner.name,()=>{
  const start=add(corner.target,corner.from,-40);
  const t=new TurnSync({heading:corner.from});
  t.observe({...start,timeMs:0});
  assert.equal(t.propose({direction:corner.to,point:corner.target,commandId:1,timeMs:0}).ok,true);
  t.markSent({commandId:1,timeMs:0});
  t.observe({...corner.target,timeMs:150});
  t.observe({...add(corner.target,corner.to,4),timeMs:175});
  const result=t.observe({...add(corner.target,corner.to,10),timeMs:200});
  assert.equal(result.phase,'confirmed');
 });
}

test('lead margin increases with estimated latency and speed',()=>{
 const t=new TurnSync({heading:'ArrowRight',speedPxPerSec:250,estimatedDispatchLatencyMs:120});
 assert.equal(t.requiredLeadPx,37);
 t.observe({x:700,y:380,timeMs:0});
 assert.equal(t.propose({direction:'ArrowUp',point:{x:730,y:380},commandId:1,timeMs:0}).reason,'insufficient-lead');
});
