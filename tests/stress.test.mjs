import test from 'node:test';
import assert from 'node:assert/strict';
import {IceSnakeSimulator, GRID, REVERSE, EDGE_CELLS} from '../sim/engine.mjs';

const allCorners = new Set(['0,0', '17,0', '17,9', '0,9']);
const serialize = c => [c.x, c.y].join(',');

test('stress matrix: gifts are neither replaced nor silently lost across 90 seeded runs', () => {
  for (const scenario of ['mixed', 'edge-gifts', 'corners']) {
    for (let seed = 1; seed <= 30; seed++) {
      const s = new IceSnakeSimulator({
        scenario, seed, speed: 0, giftIntervalMs: 700, giftTtlMs: 1450
      });
      s.start();
      const seen = new Set();
      for (let tick = 0; tick < 900; tick++) {
        s.step(100);
        const live = s.items.filter(item => item.kind === 'gift');
        assert.ok(live.length <= 1, scenario + '/' + seed + ': overlapping gifts');
        const spawns = s.events.filter(e => e.kind === 'spawn' && e.type === 'gift');
        const expiry = s.events.filter(e => e.kind === 'expire' && e.type === 'gift');
        const pickup = s.events.filter(e => e.kind === 'pickup' && e.type === 'gift');
        assert.equal(
          spawns.length, expiry.length + pickup.length + live.length,
          scenario + '/' + seed + ': a gift was silently overwritten'
        );
        if (live.length) {
          const cell = serialize(live[0].cell);
          seen.add(cell);
          assert.notEqual(cell, '17,1', 'girl cell must not host a gift');
          assert.notEqual(cell, '7,5', 'stationary head cell must not host a gift');
        }
        assert.equal(s.score, 0, 'stationary head must not collect rewards');
        assert.equal(s.mode, 'playing');
      }
      if (scenario === 'corners') {
        for (const corner of allCorners) assert.ok(seen.has(corner), 'missing corner ' + corner);
      }
      if (scenario === 'edge-gifts') {
        for (const cell of EDGE_CELLS) {
          // This edge cell is occupied by the permanent non-target girl sprite.
          // Spawning a gift there would contradict the simulator avoidance rule.
          if (serialize(cell) === '17,1') continue;
          assert.ok(seen.has(serialize(cell)), 'missing available edge cell ' + serialize(cell));
        }
      }
    }
  }
});

test('stress matrix: determinism is stable across 64 seeds', () => {
  for (let seed = 1; seed <= 64; seed++) {
    const opts = {scenario:'mixed', seed, speed:0, giftTtlMs:1200, giftIntervalMs:600};
    const a = new IceSnakeSimulator(opts), b = new IceSnakeSimulator(opts);
    a.start(); b.start();
    for (let t = 0; t < 20000; t += 100) {a.step(100); b.step(100);}
    assert.deepEqual(a.events, b.events, 'different event stream for seed ' + seed);
  }
});

test('stress matrix: no immediate reverse can modify a pending direction', () => {
  const s = new IceSnakeSimulator({seed:2026, speed:0});
  s.start();
  const desired = 'ArrowUp';
  assert.equal(s.key(desired), true);
  const pending = s.queued;
  for (let i=0;i<1000;i++) {
    assert.equal(s.key(REVERSE[s.direction]), false);
    assert.equal(s.queued, pending, 'reverse guard erased the valid queued turn');
    assert.equal(s.direction, 'ArrowRight');
    assert.equal(s.mode, 'playing');
  }
});

test('stress matrix: no edge cell is ever omitted by enumeration', () => {
  assert.equal(EDGE_CELLS.length, 2*(GRID.cols+GRID.rows)-4);
  const seen = new Set(EDGE_CELLS.map(serialize));
  assert.equal(seen.size, EDGE_CELLS.length);
  for (let x=0;x<GRID.cols;x++) {
    assert.ok(seen.has(x+',0'));
    assert.ok(seen.has(x+','+(GRID.rows-1)));
  }
  for (let y=0;y<GRID.rows;y++) {
    assert.ok(seen.has('0,'+y));
    assert.ok(seen.has((GRID.cols-1)+','+y));
  }
});
