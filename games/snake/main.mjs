import { IceSnakeSimulator,GRID } from '../../sim/engine.mjs';
const params=new URLSearchParams(location.search);
const scenario=params.get('scenario')||'mixed';
const speed=Number(params.get('speed'))||236;
const engine=new IceSnakeSimulator({seed:Number(params.get('seed'))||42,scenario,speed,
 giftIntervalMs:Number(params.get('spawnMs'))||1800,
 giftTtlMs:Number(params.get('ttlMs'))||14000,
 fixedLength:params.get('grow')!=='1'});
const canvas=document.getElementById('snakeCanvas');
const ctx=canvas.getContext('2d');
const menu=document.getElementById('menu');const button=document.getElementById('play');
const title=document.getElementById('menu-title');const description=document.getElementById('menu-description');
const names=['rink','moose','red','blue','gift','girl','flake','drift','speed'];
const images=Object.fromEntries(names.map(name=>{const im=new Image();im.src=`./assets/${name}.png`;return[name,im];}));
const draw=(kind,x,y,w=40,h=40)=>{const im=images[kind];if(im?.complete&&im.naturalWidth)ctx.drawImage(im,x-w/2,y-h/2,w,h);};
const scores=()=>{document.getElementById('score').textContent=String(engine.score);
 document.getElementById('len').textContent=String(engine.length);
 document.getElementById('best').textContent=String(engine.best);
 const sec=Math.floor(engine.time/1000);document.getElementById('clock').textContent=String(Math.floor(sec/60)).padStart(2,'0')+':'+String(sec%60).padStart(2,'0');};
function render(){ctx.clearRect(0,0,canvas.width,canvas.height);
 draw('rink',GRID.canvasWidth/2,GRID.canvasHeight/2,GRID.canvasWidth,GRID.canvasHeight);
 // Draw no real snake sprites on menu; the actual extension must detect gameplay correctly.
 if(engine.mode!=='start'){
   for(const item of engine.items)draw(item.kind,item.x,item.y);
   for(let index=engine.length-1;index>=1;index--){const p=engine.positionBack(index*40);draw(index%2?'blue':'red',p.x,p.y);}
   const h=engine.position();draw('moose',h.x,h.y);
 }
}
function showMenu(){if(engine.mode==='playing'){menu.hidden=true;return;}
 menu.hidden=false;
 title.textContent=engine.mode==='over'?'Игра окончена':engine.mode==='paused'?'Пауза':'Ледовая змейка';
 description.textContent=engine.mode==='over'?`Очки: ${engine.score}`:engine.mode==='paused'?'Продолжите игру':'Учебная симуляция';
 button.textContent=engine.mode==='over'?'Играть заново':engine.mode==='paused'?'Продолжить':'Играть';}
button.addEventListener('click',()=>{engine.start();showMenu();});
document.addEventListener('keydown',event=>{
 if(['ArrowRight','ArrowLeft','ArrowUp','ArrowDown','Space'].includes(event.code)||event.key===' '){
   event.preventDefault();engine.key(event.key===' '?'Space':event.code);
   showMenu();
 }
});
window.__ICE_SNAKE_LAB__={
 version:'0.1.0',isSimulator:true,snapshot:()=>engine.snapshot(),
 // Test-only fixture API, never used by extension or production gameplay.
 forceGift:(x,y)=>engine.spawn('gift',{x,y},60000),
 forceObject:(kind,x,y)=>engine.spawn(kind,{x,y},60000),
 setSpeed:value=>{engine.speed=Number(value);},
 events:()=>engine.events.slice(),restart:()=>{engine.reset();showMenu();}
};
let last=0;
function loop(now){const dt=last?now-last:0;last=now;engine.step(dt);scores();showMenu();render();requestAnimationFrame(loop);}
requestAnimationFrame(loop);