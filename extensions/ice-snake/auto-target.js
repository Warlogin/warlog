/* Independent, deterministic target/recovery policy; no direct game-state access. */
((root) => {
  'use strict';
  const DEFAULTS = Object.freeze({targetScore:72000, tolerance:500, autoResume:true, autoRestart:true});
  function whole(value, fallback, min, max) {
    const n=Number(value);
    return Number.isSafeInteger(n) && n>=min && n<=max ? n : fallback;
  }
  function normalizeSettings(value = {}) {
    const v=value && typeof value==='object' ? value : {};
    return {
      targetScore:whole(v.targetScore,DEFAULTS.targetScore,1000,1000000),
      tolerance:whole(v.tolerance,DEFAULTS.tolerance,0,5000),
      autoResume:typeof v.autoResume==='boolean'?v.autoResume:DEFAULTS.autoResume,
      autoRestart:typeof v.autoRestart==='boolean'?v.autoRestart:DEFAULTS.autoRestart
    };
  }
  function targetStatus(score,config) {
    const settings=normalizeSettings(config);
    const n=Math.max(0,Number(score)||0),lower=Math.max(0,settings.targetScore-settings.tolerance),upper=settings.targetScore+settings.tolerance;
    return {
      reached:n>=lower, score:n, lower, upper, target:settings.targetScore,
      withinRange:n>=lower&&n<=upper, overshoot:n>upper,
      remaining:Math.max(0,lower-n)
    };
  }
  // Limit repeated reload storms: successful rounds keep retrying, but failures within
  // 60 seconds back off rather than consuming an unbounded number of sessions.
  function restartDelayMs(recentTimes, now) {
    const recent=(Array.isArray(recentTimes)?recentTimes:[]).filter(t=>Number.isFinite(t)&&t<=now&&now-t<60000);
    return Math.min(30000,Math.round(1400*Math.pow(1.7,recent.length)));
  }
  const api={DEFAULTS,normalizeSettings,targetStatus,restartDelayMs};
  root.IceSnakeAutoTarget=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
