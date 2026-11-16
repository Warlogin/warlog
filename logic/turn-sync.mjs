/**
 * Ice Snake v0.6.15 candidate: observed-motion-first turn interlock.
 * Independent module; it does not replace an installed Chrome extension.
 *
 * Contract:
 *   1. call observe({x,y,timeMs}) for each real head observation,
 *   2. use propose({direction,point,commandId,timeMs}) before sending a CDP key,
 *   3. call markSent({commandId,timeMs}) only on a successful CDP dispatch,
 *   4. do not send a second turn while pending is non-null,
 *   5. after missed/overdue notification, replan from OBSERVED heading.
 *
 * No direct DOM, Chrome or CDP dependencies. Does not alter score/state.
 */

const AXIS = Object.freeze({
  ArrowRight: [1, 0], ArrowLeft: [-1, 0],
  ArrowUp: [0, -1], ArrowDown: [0, 1]
});

export function isDirection(direction) { return Object.hasOwn(AXIS, direction); }
export function opposite(a, b) {
  if (!isDirection(a) || !isDirection(b)) return false;
  return AXIS[a][0] === -AXIS[b][0] && AXIS[a][1] === -AXIS[b][1];
}
export function perpendicular(a, b) {
  if (!isDirection(a) || !isDirection(b)) return false;
  return Math.abs(AXIS[a][0]) !== Math.abs(AXIS[b][0]);
}
export function forwardDistance(head, target, direction) {
  if (!isDirection(direction)) throw new Error('invalid direction');
  const [vx, vy] = AXIS[direction];
  return (target.x - head.x) * vx + (target.y - head.y) * vy;
}
function projectDelta(dx, dy, direction) {
  const [vx, vy] = AXIS[direction];
  return dx * vx + dy * vy;
}
function motionDirection(dx, dy, minDeltaPx) {
  if (Math.hypot(dx, dy) < minDeltaPx) return null;
  if (Math.abs(dx) > Math.abs(dy) * 1.8) return dx > 0 ? 'ArrowRight' : 'ArrowLeft';
  if (Math.abs(dy) > Math.abs(dx) * 1.8) return dy > 0 ? 'ArrowDown' : 'ArrowUp';
  return null;
}

export class TurnSync {
  constructor({
    heading = null, speedPxPerSec = 235, estimatedDispatchLatencyMs = 70,
    cellPx = 40, leadReservePx = 7, minLeadPx = 12,
    missedTolerancePx = 7, confirmationMotionPx = 6, minMotionPx = 1,
    maximumOverduePx = 40
  } = {}) {
    if (heading !== null && !isDirection(heading)) throw new Error('invalid heading');
    if (!(speedPxPerSec > 0 && cellPx > 0 && estimatedDispatchLatencyMs >= 0)) {
      throw new Error('invalid speed/latency/cell size');
    }
    this.heading = heading;
    this.speedPxPerSec = speedPxPerSec;
    this.estimatedDispatchLatencyMs = estimatedDispatchLatencyMs;
    this.cellPx = cellPx;
    this.leadReservePx = leadReservePx;
    this.minLeadPx = minLeadPx;
    this.missedTolerancePx = missedTolerancePx;
    this.confirmationMotionPx = confirmationMotionPx;
    this.minMotionPx = minMotionPx;
    this.maximumOverduePx = maximumOverduePx;
    this.last = null;
    this.pending = null;
    this.holdForSafety = false;
    this.events = [];
  }

  get requiredLeadPx() {
    return Math.max(this.minLeadPx,
      this.speedPxPerSec * this.estimatedDispatchLatencyMs / 1000 + this.leadReservePx);
  }

  _event(type, data = {}) {
    const event = {type, ...data};
    this.events.push(event);
    return event;
  }

  /** No commands may be superseded by another while a previous turn is unresolved. */
  propose({direction, point, commandId, timeMs}) {
    if (!isDirection(direction)) return {ok:false, reason:'invalid-direction'};
    if (this.holdForSafety) return {ok:false, reason:'safety-hold'};
    if (this.pending) return {ok:false, reason:'pending-turn', pendingId:this.pending.commandId};
    if (!this.last || !isDirection(this.heading)) return {ok:false, reason:'no-observed-heading'};
    if (!perpendicular(this.heading, direction)) return {
      ok:false, reason:opposite(this.heading,direction)?'reverse-turn':'non-perpendicular-turn'
    };
    if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) {
      return {ok:false,reason:'invalid-turn-point'};
    }
    const distance = forwardDistance(this.last, point, this.heading);
    if (distance < this.requiredLeadPx) {
      this._event('replan-required', {commandId, reason:'insufficient-lead', distancePx:distance,
        requiredLeadPx:this.requiredLeadPx, timeMs});
      return {ok:false, reason:'insufficient-lead', distancePx:distance,
        requiredLeadPx:this.requiredLeadPx};
    }
    if (distance > this.cellPx * 2) return {ok:false, reason:'turn-too-far'};
    this.pending = {
      commandId, from:this.heading, direction, point:{x:point.x,y:point.y},
      start:{x:this.last.x,y:this.last.y}, proposedAtMs:timeMs,
      sentAtMs:null, phase:'reserved', lateralProgressPx:0,
      consecutiveTargetMotion:0, overdueEmitted:false
    };
    return {ok:true, command:direction, commandId, distancePx:distance};
  }

  /** May be called ONLY after the transport actually transmitted the command. */
  markSent({commandId,timeMs}) {
    if (!this.pending || this.pending.commandId !== commandId || this.pending.phase !== 'reserved') {
      return {ok:false,reason:'no-matching-reservation'};
    }
    this.pending.sentAtMs = timeMs;
    this.pending.phase = 'await-observed-motion';
    return {ok:true};
  }

  /** Cancel only a reservation that was NOT sent. Never cancel an in-flight CDP command. */
  cancelUnsent(commandId) {
    if (this.pending?.commandId !== commandId || this.pending.phase !== 'reserved') return false;
    this.pending = null;
    return true;
  }

  observe({x,y,timeMs}) {
    if (![x,y,timeMs].every(Number.isFinite)) throw new Error('invalid observation');
    const now = {x,y,timeMs};
    if (!this.last) { this.last=now; return {phase:'initialized', heading:this.heading}; }
    if (timeMs < this.last.timeMs) throw new Error('non-monotonic time');
    const dx=x-this.last.x, dy=y-this.last.y;
    const observedMotion=motionDirection(dx,dy,this.minMotionPx);
    this.last=now;
    if (!this.pending) {
      if (observedMotion) this.heading=observedMotion;
      return {phase:'idle',heading:this.heading};
    }
    const p=this.pending;
    if (p.phase==='reserved') return {phase:'reserved',heading:this.heading};

    if (observedMotion===p.direction) {
      p.consecutiveTargetMotion += 1;
      p.lateralProgressPx += Math.max(0,projectDelta(dx,dy,p.direction));
      if (p.consecutiveTargetMotion >= 2 && p.lateralProgressPx >= this.confirmationMotionPx) {
        this.pending=null;
        this.heading=p.direction;
        this.holdForSafety=false;
        const event=this._event('observed-turn-confirmed',{commandId:p.commandId,
          from:p.from,to:p.direction,timeMs,travelPx:p.lateralProgressPx});
        return {phase:'confirmed',heading:this.heading,event};
      }
    } else {
      p.consecutiveTargetMotion=0;
      // Do not use CDP success as turn success. While an input may be buffered,
      // preserve the interlock and prohibit all conflicting instructions.
      if (observedMotion && observedMotion!==p.from) {
        this.heading=observedMotion;
        this.holdForSafety=true;
        const event=this._event('unexpected-heading',{commandId:p.commandId,
          expected:p.direction,actual:observedMotion,timeMs});
        return {phase:'desynchronized',heading:this.heading,event};
      }
    }
    const beyond= -forwardDistance(now,p.point,p.from);
    if (beyond > this.missedTolerancePx && !p.overdueEmitted) {
      p.phase='overdue';p.overdueEmitted=true;
      this._event('turn-overdue',{commandId:p.commandId, direction:p.direction,
        distanceBeyondPx:beyond,timeMs});
    }
    if (beyond > this.maximumOverduePx) {
      this.holdForSafety=true;
      return {phase:'safety-hold',heading:this.heading,
        reason:'unconfirmed-turn-beyond-one-cell',distanceBeyondPx:beyond};
    }
    return {phase:p.phase,heading:this.heading,distanceBeyondPx:beyond};
  }

  /** After a game stop/restart, outstanding events can be dropped explicitly. */
  reset({heading=null}={}) {
    if (heading !== null && !isDirection(heading)) throw new Error('invalid heading');
    this.pending=null; this.last=null; this.holdForSafety=false; this.heading=heading;
    this.events=[];
  }
}
