import test from 'node:test';
import assert from 'node:assert/strict';
import {IceSnakeSimulator} from '../sim/engine.mjs';

// Durable minimal reproduction of the two incident sequences from user logs.
// This tests the simulator input semantics; real extension behavior is checked separately.
const tick=(s,ms)=>{for(let t=0;t<ms;t+=10)s.step(Math.min(ms-t,10));};
test('v0.6.8: false reverse immediately after launch would be rejected',()=>{
 const s=new IceSnakeSimulator({seed:1});s.start();
 assert.equal(s.key('ArrowLeft'),false); // Actual reverse is unsafe: lab must not ignore this guard.
 assert.ok(s.events.some(e=>e.kind==='reverse-rejected'));
});
test('v0.6.7 34050 incident: right-up-left does not get mistaken for right-left',()=>{
 const s=new IceSnakeSimulator({seed:1,giftIntervalMs:100000});s.start();
 // Right -> Up at first intersection, Left at the next one.
 assert.equal(s.key('ArrowUp'),true);tick(s,180);
 assert.equal(s.direction,'ArrowUp');
 assert.equal(s.key('ArrowLeft'),true);tick(s,180);
 assert.equal(s.direction,'ArrowLeft');
 assert.deepEqual(s.events.filter(e=>e.kind==='turn').map(e=>e.direction),['ArrowUp','ArrowLeft']);
});
test('v0.6.7 30900 incident: up-left-down sequence stays legal',()=>{
 const s=new IceSnakeSimulator({seed:1,giftIntervalMs:100000});s.start();
 s.key('ArrowUp');tick(s,180);s.key('ArrowLeft');tick(s,180);
 assert.equal(s.key('ArrowDown'),true);tick(s,180);
 assert.equal(s.direction,'ArrowDown');
});