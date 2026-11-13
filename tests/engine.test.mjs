import test from 'node:test';
import assert from 'node:assert/strict';
import {IceSnakeSimulator, GRID, DIRECTIONS, REVERSE, EDGE_CELLS, seeded, point, cellFromPoint} from '../sim/engine.mjs';

const game=(options={})=>{const s=new IceSnakeSimulator({seed:42,giftIntervalMs:100000,...options});s.start();return s;};
const advance=(s,ms)=>{for(let i=0;i<ms;i+=20)s.step(Math.min(20,ms-i));return s.snapshot();};
const resetEvents=s=>s.events.splice(0,s.events.length);

test('geometry: exactly 18 x 10 cells with 40-pixel spacing',()=>{
 assert.equal(GRID.cols*GRID.rows,180);
 assert.deepEqual(point(0,0),{x:234,y:144});
 assert.deepEqual(point(17,9),{x:914,y:504});
 assert.deepEqual(cellFromPoint(point(17,9)),{x:17,y:9});
});
test('perimeter enumeration covers 52 unique cells including four corners',()=>{
 assert.equal(EDGE_CELLS.length,2*(18+10)-4);
 assert.equal(new Set(EDGE_CELLS.map(p=>`${p.x},${p.y}`)).size,52);
 for(const c of [[0,0],[17,0],[0,9],[17,9]]) assert.ok(EDGE_CELLS.some(p=>p.x===c[0]&&p.y===c[1]));
});
test('initial state has a right-facing three-segment snake',()=>{
 const s=new IceSnakeSimulator();const st=s.snapshot();
 assert.equal(st.mode,'start');assert.deepEqual(st.head,point(7,5));assert.equal(st.direction,'ArrowRight');assert.equal(st.length,3);
});
test('game begins only on start()',()=>{const s=new IceSnakeSimulator();s.step(100);assert.deepEqual(s.position(),point(7,5));s.start();s.step(100);assert.ok(s.position().x>514);});
test('continuous motion moves approximately 236 pixels each second',()=>{
 const s=game({speed:236});advance(s,500);assert.ok(Math.abs(s.totalDistance-118)<1);
});
test('right to up is accepted and applies at next grid junction',()=>{
 const s=game();s.key('ArrowUp');advance(s,190);assert.equal(s.direction,'ArrowUp');assert.deepEqual(s.cell,{x:8,y:5});
});
test('turn sequence Right-Up-Left-Down works on successive intersections',()=>{
 const s=game();s.key('ArrowUp');advance(s,180);assert.equal(s.direction,'ArrowUp');
 s.key('ArrowLeft');advance(s,180);assert.equal(s.direction,'ArrowLeft');
 s.key('ArrowDown');advance(s,180);assert.equal(s.direction,'ArrowDown');
 const turns=s.events.filter(x=>x.kind==='turn').map(x=>x.direction);
 assert.deepEqual(turns,['ArrowUp','ArrowLeft','ArrowDown']);
});
test('true immediate 180-degree reversal is rejected',()=>{
 const s=game();assert.equal(s.key('ArrowLeft'),false);assert.equal(s.queued,null);
 assert.equal(s.events.at(-1).kind,'reverse-rejected');
});
test('reverse after confirmed Up is Down, but Left is valid',()=>{
 const s=game();s.key('ArrowUp');advance(s,180);
 assert.equal(s.key('ArrowDown'),false);assert.equal(s.key('ArrowLeft'),true);
});
test('queued keyboard input cannot change direction before junction',()=>{
 const s=game();advance(s,60);s.key('ArrowUp');advance(s,30);
 assert.equal(s.direction,'ArrowRight');assert.ok(s.progress<40);
});
test('when heading into wall game-over happens',()=>{
 const s=game({giftIntervalMs:1e8});advance(s,2000);
 assert.equal(s.mode,'over');assert.equal(s.events.at(-1).reason,'wall');
});
test('reset after game-over correctly restores position and score',()=>{
 const s=game();advance(s,2000);assert.equal(s.mode,'over');s.start();assert.deepEqual(s.position(),point(7,5));assert.equal(s.mode,'playing');
});
test('Space toggles game pause while avoiding implicit movement',()=>{
 const s=game();advance(s,150);s.key('Space');const p=s.position();advance(s,500);assert.deepEqual(s.position(),p);s.key('Space');advance(s,60);assert.notDeepEqual(s.position(),p);
});
test('gift in the head path yields 500 points',()=>{
 const s=game();s.spawn('gift',{x:8,y:5});advance(s,170);assert.equal(s.score,500);
 assert.equal(s.events.filter(x=>x.kind==='pickup').at(-1).type,'gift');
});
test('gift does not necessarily cause growth (observed v0.6.7 length=3)',()=>{
 const s=game();s.spawn('gift',{x:8,y:5});advance(s,200);assert.equal(s.length,3);
});
test('growing variant increases length by one',()=>{
 const s=game({fixedLength:false});s.spawn('gift',{x:8,y:5});advance(s,200);assert.equal(s.length,4);
});
test('girl is not a gift and has a different reward',()=>{
 const s=game();s.spawn('girl',{x:8,y:5});advance(s,200);assert.equal(s.score,50);
});
test('edge gift scenario cycles through all perimeter positions',()=>{
 const s=game({scenario:'edge-gifts'});
 s.items=[];const cells=[];
 for(let i=0;i<52;i++){s.items=[];s.spawnGift();cells.push(s.items.at(-1).cell);}
 assert.equal(new Set(cells.map(p=>`${p.x},${p.y}`)).size,52);
});
test('scheduled gift spawn does not replace an uncollected edge gift',()=>{
 const s=game({scenario:'edge-gifts',giftIntervalMs:1800,giftTtlMs:14000,speed:0});
 advance(s,1000);
 const first={...s.items.find(x=>x.kind==='gift').cell};
 assert.deepEqual(first,{x:0,y:0});
 advance(s,1800);
 assert.deepEqual(s.items.find(x=>x.kind==='gift').cell,first);
 assert.equal(s.events.filter(x=>x.kind==='spawn'&&x.type==='gift').length,1);
 assert.equal(s.giftCounter,1);
});
test('next edge gift appears only after the previous gift expires',()=>{
 const s=game({scenario:'edge-gifts',giftIntervalMs:1000,giftTtlMs:1500,speed:0});
 advance(s,1000);
 const first={...s.items.find(x=>x.kind==='gift').cell};
 advance(s,1000);
 assert.deepEqual(s.items.find(x=>x.kind==='gift').cell,first);
 advance(s,1000);
 const gifts=s.items.filter(x=>x.kind==='gift');
 assert.equal(gifts.length,1);
 assert.deepEqual(gifts[0].cell,{x:1,y:0});
});
test('corner scenario covers all four corners before repeating',()=>{
 const s=game({scenario:'corners'});s.items=[];const cells=[];
 for(let i=0;i<4;i++){s.items=[];s.spawnGift();cells.push(s.items.at(-1).cell);}
 assert.deepEqual(cells,[{x:0,y:0},{x:17,y:0},{x:17,y:9},{x:0,y:9}]);
});
test('deterministic seeds produce identical item trajectories',()=>{
 const a=game({seed:2026}),b=game({seed:2026});
 for(let i=0;i<100;i++){a.step(50);b.step(50)}
 assert.deepEqual(a.events,b.events);
});
test('different seeds change random sequence',()=>{
 const a=game({seed:123456}),b=game({seed:987654});a.spawnGift();b.spawnGift();
 assert.notDeepEqual(a.items.find(i=>i.kind==='gift').cell,b.items.find(i=>i.kind==='gift').cell);
});
test('expired gifts are removed from simulation',()=>{
 const s=game({giftTtlMs:100});s.spawn('gift',{x:12,y:5},100);advance(s,150);
 assert.equal(s.items.filter(x=>x.kind==='gift').length,0);
});
test('turns are rejected when game is not active',()=>{
 const s=new IceSnakeSimulator();assert.equal(s.key('ArrowUp'),false);assert.equal(s.queued,null);
});
test('every direction has a unique opposite',()=>{
 for(const x of Object.keys(DIRECTIONS))assert.equal(REVERSE[REVERSE[x]],x);
});