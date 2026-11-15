/* Synthetic negative-control fixture for testing the CI extension runner.
 * This is NOT the Dobry Cola autopilot or any user-private source.
 */
'use strict';
const BASE='https://dobrycola-promo.ru/games/snake/';
const sessions=new Map();
const key={type:'rawKeyDown',key:'ArrowUp',code:'ArrowUp',
  windowsVirtualKeyCode:38,nativeVirtualKeyCode:38};
function message(tabId,text){
  const s=sessions.get(tabId);
  if(s)s.log.push(new Date().toLocaleTimeString('ru-RU')+' '+text);
}
chrome.runtime.onMessage.addListener((req,sender,reply)=>{
  (async()=>{
    const tabId=req.tabId ?? sender.tab?.id;
    if(req.type==='START'){
      const tab=await chrome.tabs.get(tabId);
      if(!tab.url?.startsWith(BASE))throw new Error('Not the fixture game URL');
      await chrome.debugger.attach({tabId},'1.3');
      sessions.set(tabId,{log:[]});
      message(tabId,'Mock MV3 controller: starting simulator');
      await chrome.scripting.executeScript({target:{tabId},
        func:()=>document.getElementById('play')?.click()});
      await new Promise(resolve=>setTimeout(resolve,350));
      await chrome.debugger.sendCommand({tabId},'Input.dispatchKeyEvent',key);
      await chrome.debugger.sendCommand({tabId},'Input.dispatchKeyEvent',{...key,type:'keyUp'});
      message(tabId,'ВВОД ПОДТВЕРЖДЁН CDP: команда #1 ArrowUp');
      return {ok:true};
    }
    if(req.type==='GET_LOG'){
      const s=sessions.get(tabId);
      return {ok:true,log:s?.log.join('\n')||''};
    }
    return {ok:true};
  })().then(reply).catch(err=>reply({ok:false,error:err.message}));
  return true;
});
