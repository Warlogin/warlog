// Independent simulator, not recovered/copy-pasted Dobry Cola source.
// Geometry is inferred from v0.6.7–v0.6.9 diagnostic logs. Every unspecified
// original-game mechanic is intentionally configurable and marked approximate.
export const GRID = Object.freeze({cols: 18, rows: 10, cell: 40, x0: 234, y0: 144,
  canvasWidth: 1148, canvasHeight: 646});
export const DIRECTIONS = Object.freeze({ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]});
export const REVERSE = Object.freeze({ArrowRight: 'ArrowLeft', ArrowLeft: 'ArrowRight', ArrowUp: 'ArrowDown', ArrowDown: 'ArrowUp'});
const TYPES = ['gift', 'flake', 'drift', 'speed'];
export const point = (x, y) => ({x: GRID.x0 + x*GRID.cell, y: GRID.y0 + y*GRID.cell});
export function seeded(seed = 1) {
  let n = (Number(seed) >>> 0) || 1;
  return () => {n ^= n << 13;n ^= n >>> 17;n ^= n << 5;return (n >>> 0) / 4294967296;};
}
export function inBounds(c) {return c.x>=0&&c.x<GRID.cols&&c.y>=0&&c.y<GRID.rows;}
export function cellFromPoint(p) {return {x:Math.round((p.x-GRID.x0)/GRID.cell), y:Math.round((p.y-GRID.y0)/GRID.cell)};}
const distance = (a,b) => Math.hypot(a.x-b.x,a.y-b.y);
const edgeList = [
  ...Array.from({length: GRID.cols},(_,x)=>({x,y:0})),
  ...Array.from({length: GRID.rows},(_,y)=>({x:GRID.cols-1,y})),
  ...Array.from({length: GRID.cols},(_,i)=>({x:GRID.cols-1-i,y:GRID.rows-1})),
  ...Array.from({length: GRID.rows},(_,i)=>({x:0,y:GRID.rows-1-i}))
].filter((c,i,a)=>a.findIndex(p=>p.x===c.x&&p.y===c.y)===i);
export const EDGE_CELLS = Object.freeze(edgeList);

export class IceSnakeSimulator {
  constructor({seed=1,scenario='mixed',speed=236,giftIntervalMs=1800,giftTtlMs=14000,
    fixedLength=true}={}) {
    this.config={seed,scenario,speed,giftIntervalMs,giftTtlMs,fixedLength};
    this.rng=seeded(seed);
    this.reset();
  }
  reset() {
    this.rng=seeded(this.config.seed);
    this.mode='start';this.score=0;this.best=0;this.length=3;
    this.speed=this.config.speed;
    this.time=0;this.totalDistance=0;this.progress=0;
    this.cell={x:7,y:5};this.direction='ArrowRight';this.queued=null;
    this.path=[{...point(7,5),d:0},{...point(6,5),d:-40},{...point(5,5),d:-80}];
    this.items=[];this.events=[];this.giftCounter=0;this.spawnAt=1000;
    // This is a deliberately non-target pickup mimicking girl@916,184 in the logs.
    this.spawn('girl',{x:17,y:1},Infinity);
    this.events.push({time:0,kind:'reset'});
    return this.snapshot();
  }
  start() {if(['start','over'].includes(this.mode)){if(this.mode==='over')this.reset();this.mode='playing';return true;}if(this.mode==='paused'){this.mode='playing';return true;}return false;}
  pause() {if(this.mode==='playing'){this.mode='paused';return true;}return false;}
  key(key) {
    if(key==='Space'){if(this.mode==='playing')this.pause();else if(this.mode==='paused')this.start();return true;}
    if(!DIRECTIONS[key]||this.mode!=='playing')return false;
    // The underlying game typically rejects immediate reversals. One
    // direction can be queued for the next lattice intersection.
    if(key===REVERSE[this.direction]){this.events.push({time:this.time,kind:'reverse-rejected',key});return false;}
    if(key===this.direction){this.queued=null;return true;}
    this.queued=key;this.events.push({time:this.time,kind:'queued',key});return true;
  }
  position(){const d=DIRECTIONS[this.direction];const p=point(this.cell.x,this.cell.y);return{x:p.x+d[0]*this.progress,y:p.y+d[1]*this.progress};}
  positionBack(back){const goal=this.totalDistance-back;const p=this.position();
    if(this.path.length===0)return p;
    const path=[{...p,d:this.totalDistance},...this.path];
    for(let i=0;i<path.length-1;i++){
      const a=path[i],b=path[i+1];if(a.d>=goal&&b.d<=goal){const f=(goal-b.d)/Math.max(.00001,a.d-b.d);return {x:b.x+(a.x-b.x)*f,y:b.y+(a.y-b.y)*f};}
    }
    return {x:path.at(-1).x,y:path.at(-1).y};
  }
  atItem(item){return distance(this.position(),item)<=19;}
  spawn(type,cell,ttl=10000) {
    if(!inBounds(cell))throw new Error('spawn outside board');
    const item={kind:type,cell:{...cell},...point(cell.x,cell.y),expiresAt:this.time+ttl};
    this.items=this.items.filter(x=>x.kind!==type);
    this.items.push(item);this.events.push({time:this.time,kind:'spawn',type,cell:{...cell}});
    return item;
  }
  spawnGift() {
    const forbidden=new Set([`${this.cell.x},${this.cell.y}`,...this.items.map(x=>`${x.cell.x},${x.cell.y}`)]);
    let list;
    if(this.config.scenario==='edge-gifts')list=EDGE_CELLS;
    else if(this.config.scenario==='corners')list=[{x:0,y:0},{x:17,y:0},{x:17,y:9},{x:0,y:9}];
    else list=Array.from({length:180},(_,i)=>({x:i%18,y:Math.floor(i/18)}));
    const start=this.config.scenario==='edge-gifts'||this.config.scenario==='corners'?
      this.giftCounter%list.length:Math.floor(this.rng()*list.length);
    const chosen=Array.from({length:list.length},(_,i)=>list[(start+i)%list.length])
      .find(c=>!forbidden.has(`${c.x},${c.y}`));
    this.giftCounter++;
    if(chosen)this.spawn('gift',chosen,this.config.giftTtlMs);
  }
  collect() {
    const head=this.position();
    const keep=[];
    for(const item of this.items){
      if(distance(head,item)<21){
        const value={gift:500,girl:50,flake:50,speed:100,drift:0}[item.kind]??0;
        this.score+=value;this.best=Math.max(this.best,this.score);
        if(item.kind==='speed')this.speed=this.config.speed*1.35;
        if(!this.config.fixedLength&&item.kind==='gift')this.length++;
        this.events.push({time:this.time,kind:'pickup',type:item.kind,value,score:this.score});
      } else keep.push(item);
    }
    this.items=keep;
  }
  step(dtMs) {
    if(this.mode!=='playing')return this.snapshot();
    // Limit huge wall-clock gaps, as a browser game usually does while tab is hidden.
    const delta=Math.max(0,Math.min(100,Number(dtMs)||0));
    this.time+=delta;
    this.items=this.items.filter(item=>item.expiresAt>this.time);
    if(this.time>=this.spawnAt){this.spawnGift();this.spawnAt+=this.config.giftIntervalMs;}
    let left=delta*this.speed/1000;
    let guard=0;
    while(left>1e-7&&this.mode==='playing'&&guard++<10){
      const segment=Math.min(left,GRID.cell-this.progress);
      const before=this.position();
      this.progress+=segment;this.totalDistance+=segment;left-=segment;
      this.path.unshift({...before,d:this.totalDistance-segment});
      while(this.path.length>2&&this.path.at(-1).d<this.totalDistance-200) this.path.pop();
      this.collect();
      if(this.progress>=GRID.cell-1e-6){
        const v=DIRECTIONS[this.direction];this.cell={x:this.cell.x+v[0],y:this.cell.y+v[1]};this.progress=0;
        if(!inBounds(this.cell)){this.mode='over';this.events.push({time:this.time,kind:'game-over',reason:'wall',score:this.score});break;}
        if(this.queued){
          this.direction=this.queued;this.queued=null;
          this.events.push({time:this.time,kind:'turn',direction:this.direction,cell:{...this.cell}});
        }
        this.collect();
      }
    }
    return this.snapshot();
  }
  snapshot(){return{mode:this.mode,score:this.score,length:this.length,direction:this.direction,
    queued:this.queued,head:this.position(),cell:{...this.cell},speed:this.speed,
    time:this.time,items:this.items.map(x=>({...x})),events:this.events.length};}
}