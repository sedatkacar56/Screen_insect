/* Screen Insect: browser version of desktop_bug_gun_v7.pyw
 * Same rules: bugs fight each other, a little man follows the mouse,
 * sword / hammer / fists / gun (limited ammo), hits only land in front. */
(function (root) {
  'use strict';

  // ---------------------------- settings ----------------------------
  const SIZE = 0.72;             // everything is drawn smaller than on the desktop
  const SPEED = 80;
  const MAX_BUGS = 5, MAX_BIG = 3;
  const SPAWN_MIN = 4, SPAWN_MAX = 10;
  const NO_DEATH_SECONDS = 20, MAX_EXTRA = 4;
  const AMMO_MAX = 8, AMMO_REGEN = 4.0, BULLET_DAMAGE = 30;
  const MAN_ENERGY = 100;

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const angdiff = (a, b) => ((a - b + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
  const rnd = (a, b) => a + Math.random() * (b - a);
  const hyp = Math.hypot;

  const SPECS = {
    beetle: {
      legs: [[11, 5, 9], [5, 0, 0], [-1, -5, -9]], ay: 6, ky: 14, fy: 21, width: 2, swing: 5,
      base: 1.0, scale: 1.0, r: 22, hp: 40, atk: 7, mdmg: 4, aggr: 0.5, sight: 160, rate: 0.9,
      weight: 3, strike: 90, rush: 1.6, creep: 1.0
    },
    cockroach: {
      legs: [[8, 3, 6], [2, 0, -2], [-4, -4, -10]], ay: 5, ky: 12, fy: 18, width: 1, swing: 6,
      base: 1.8, scale: 1.0, r: 20, hp: 30, atk: 5, mdmg: 3, aggr: 0.3, sight: 160, rate: 0.7,
      weight: 2, walk: [1, 3], edges: true, strike: 90, rush: 1.4, creep: 1.0
    },
    spider: {
      legs: [[8, 10, 19], [3, 6, 10], [-2, -5, -10], [-7, -11, -20]], ay: 5, ky: 15, fy: 29,
      width: 2, swing: 6, base: 0.8, scale: 1.1, r: 20, hp: 55, atk: 9, mdmg: 8, aggr: 0.8,
      sight: 280, rate: 0.85, weight: 1.2, eats: true, strike: 160, rush: 2.4, creep: 1.0
    },
    centipede: {
      legs: [], base: 0.9, scale: 0.8, r: 22, hp: 75, atk: 12, mdmg: 9, aggr: 0.9, sight: 330,
      rate: 0.8, weight: 0.8, eats: true, chain: 14, gap: 11, strike: 220, rush: 5.0, creep: 0.25
    },
    mantis: {
      legs: [[0, 6, 12], [-8, -4, -12]], ay: 3, ky: 11, fy: 17, width: 1, swing: 3,
      base: 0.5, scale: 1.3, r: 24, hp: 80, atk: 14, mdmg: 10, aggr: 0.9, sight: 240, rate: 0.9,
      weight: 0.8, eats: true, strike: 110, rush: 6.0, creep: 0
    },
    scorpion: {
      legs: [[8, 6, 9], [3, 2, 4], [-2, -3, -4], [-7, -7, -9]], ay: 6, ky: 13, fy: 19, width: 2,
      swing: 5, base: 0.7, scale: 1.8, r: 28, hp: 110, atk: 18, mdmg: 14, aggr: 0.9, sight: 300,
      rate: 1.0, weight: 0.6, eats: true, strike: 90, rush: 3.5, creep: 0.4
    },
    frog: {
      legs: [], base: 0.6, scale: 2.2, r: 22, hp: 140, atk: 12, mdmg: 12, aggr: 0.7, sight: 260,
      rate: 1.2, weight: 0.6, eats: true, walk: [1, 2], pause: [2, 6], strike: 70, rush: 3.0, creep: 0
    }
  };
  for (const k in SPECS) {
    const s = SPECS[k];
    s.power = s.hp * s.atk; s.big = s.hp >= 55;
    s.walk = s.walk || [3, 8]; s.pause = s.pause || [0.6, 3.0]; s.eats = !!s.eats;
  }

  // name, range, arc, dmg, swing time, cooldown, knockback, stun
  const WEAPONS = [
    ['SWORD', 52, 0.95, 22, 0.28, 0.45, 14, 0.0],
    ['HAMMER', 46, 0.70, 55, 0.50, 1.10, 30, 1.3],
    ['FISTS', 32, 0.60, 9, 0.16, 0.25, 8, 0.0],
    ['GUN', 0, 0.0, BULLET_DAMAGE, 0.12, 0.35, 10, 0.0]
  ];

  // ------------------------------ drawing helpers ------------------------------
  let ctx = null;
  function ellipse(cx, cy, rx, ry, n) {
    n = n || 18; const out = [];
    for (let i = 0; i < n; i++) { const t = 2 * Math.PI * i / n; out.push([cx + rx * Math.cos(t), cy + ry * Math.sin(t)]); }
    return out;
  }
  function makeDrawer(x, y, a, s) {
    const ca = Math.cos(a), sa = Math.sin(a);
    const T = (px, py) => [x + (px * ca - py * sa) * s, y + (px * sa + py * ca) * s];
    const poly = (pts, fill) => {
      ctx.beginPath();
      pts.forEach((p, i) => { const q = T(p[0], p[1]); if (i) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); });
      ctx.closePath(); ctx.fillStyle = fill; ctx.fill();
    };
    const line = (pts, w, col) => {
      ctx.beginPath();
      pts.forEach((p, i) => { const q = T(p[0], p[1]); if (i) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); });
      ctx.strokeStyle = col; ctx.lineWidth = Math.max(1, w * s); ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.stroke();
    };
    return { T, poly, line };
  }
  const BODY = '#101010', SHELL = '#2b2b2b', LEG = '#161616';

  // --------------------------------- Insect ---------------------------------
  class Insect {
    constructor(kind, w, h) {
      this.kind = kind; this.spec = SPECS[kind]; this.sc = SIZE * this.spec.scale;
      this.w = w; this.h = h;
      const side = 'lrtb'[Math.floor(Math.random() * 4)];
      if (side === 'l') { this.x = -60; this.y = rnd(80, h - 80); }
      else if (side === 'r') { this.x = w + 60; this.y = rnd(80, h - 80); }
      else if (side === 't') { this.x = rnd(80, w - 80); this.y = -60; }
      else { this.x = rnd(80, w - 80); this.y = h + 60; }
      this.target = this.newTarget();
      this.a = Math.atan2(this.target[1] - this.y, this.target[0] - this.x);
      this.state = 'walk'; this.timer = rnd(this.spec.walk[0], this.spec.walk[1]);
      this.phase = rnd(0, 6); this.t = 0; this.alive = true; this.moving = false; this.entered = false;
      this.freeze = 0; this.feast = 0; this.runT = 0; this.runBoost = 1;
      this.segs = []; for (let i = 0; i < (this.spec.chain || 0); i++) this.segs.push([this.x, this.y]);
      this.hp = this.maxhp = this.spec.hp; this.power = this.spec.power;
      this.bold = this.spec.aggr * rnd(0.8, 1.2); this.hates = Math.random() < this.spec.aggr;
      this.foe = null; this.fightT = 0; this.atkT = rnd(0.3, 1.0); this.first = false;
      this.lunge = 0; this.shake = 0; this.fleeT = 0; this.fleeFrom = [this.x, this.y]; this.waitT = 0;
      this.ox = 0; this.oy = 0;
    }
    get radius() { return this.spec.r * this.sc; }
    points() {
      const pts = [[this.x, this.y, this.radius]];
      for (let i = 3; i < this.segs.length; i += 4) pts.push([this.segs[i][0], this.segs[i][1], 7 * this.sc]);
      return pts;
    }
    newTarget() {
      const m = 60, w = this.w, h = this.h;
      if (this.spec.edges && Math.random() < 0.7) {
        if (Math.random() < 0.5) return [Math.random() < 0.5 ? 40 : w - 40, rnd(m, h - m)];
        return [rnd(m, w - m), Math.random() < 0.5 ? 40 : h - 40];
      }
      return [rnd(m, w - m), rnd(m, h - m)];
    }
    update(dt, goal, boost) {
      boost = boost || 1; this.t += dt; this.moving = false;
      if (this.feast > 0) { this.feast -= dt; return; }
      if (this.freeze > 0) { this.freeze -= dt; return; }
      if (goal) {
        this.target = goal; this.state = 'walk'; this.timer = 3;
        if (boost > 1) { this.runT = 0.8; this.runBoost = boost; }
      } else if (this.runT > 0) { this.runT -= dt; boost = this.runBoost; }
      if (this.state === 'walk') {
        let speed = SPEED * this.spec.base * boost;
        const tx = this.target[0], ty = this.target[1];
        const diff = angdiff(Math.atan2(ty - this.y, tx - this.x), this.a);
        const turn = (boost <= 1 ? 2.3 : 2.3 + (boost - 1) * 1.4) * dt;
        this.a += Math.max(-turn, Math.min(turn, diff));
        if (Math.abs(diff) > 1.0) speed *= boost <= 1 ? 0.4 : 0.55;
        this.x += Math.cos(this.a) * speed * dt; this.y += Math.sin(this.a) * speed * dt;
        this.moving = true; this.phase += speed * dt / (9 * this.sc);
        if (hyp(tx - this.x, ty - this.y) < 25 && !goal) this.target = this.newTarget();
        this.timer -= dt;
        if (this.timer <= 0 && boost <= 1 && !goal) { this.state = 'pause'; this.timer = rnd(this.spec.pause[0], this.spec.pause[1]); }
      } else {
        this.timer -= dt;
        if (this.timer <= 0) { this.state = 'walk'; this.timer = rnd(this.spec.walk[0], this.spec.walk[1]); this.target = this.newTarget(); }
      }
      this.keepOnScreen();
    }
    keepOnScreen() {
      if (this.x > 20 && this.x < this.w - 20 && this.y > 20 && this.y < this.h - 20) this.entered = true;
      if (this.entered) { this.x = clamp(this.x, 15, this.w - 15); this.y = clamp(this.y, 15, this.h - 15); }
      if (this.segs.length) this.follow();
    }
    follow() {
      const gap = this.spec.gap * this.sc; const pts = [[this.x, this.y]];
      for (let i = 1; i < this.segs.length; i++) {
        let qx = this.segs[i][0], qy = this.segs[i][1]; const p = pts[pts.length - 1];
        const d = hyp(p[0] - qx, p[1] - qy);
        if (d > gap) { qx = p[0] + (qx - p[0]) * gap / d; qy = p[1] + (qy - p[1]) * gap / d; }
        pts.push([qx, qy]);
      }
      this.segs = pts;
    }
    awayGoal(px, py) {
      const ang = Math.atan2(this.y - py, this.x - px); let tx = this.x, ty = this.y;
      for (const da of [0, 0.9, -0.9, 1.8, -1.8]) {
        tx = clamp(this.x + Math.cos(ang + da) * 400, 40, this.w - 40);
        ty = clamp(this.y + Math.sin(ang + da) * 400, 40, this.h - 40);
        if (hyp(tx - this.x, ty - this.y) > 120) break;
      }
      return [tx, ty];
    }
    // ------------------------------ drawing ------------------------------
    draw() {
      if (this.kind === 'centipede') this.drawCentipede(); else this.drawLegged();
      this.drawBar();
    }
    drawBar() {
      if (this.hp >= this.maxhp - 0.5 && !this.foe) return;
      const frac = clamp(this.hp / this.maxhp, 0, 1), w = clamp(26 * this.sc, 18, 56);
      const x = this.x + this.ox, y = this.y + this.oy - this.radius - 14;
      ctx.fillStyle = '#202020'; ctx.fillRect(x - w / 2 - 1, y - 3, w + 2, 6);
      ctx.fillStyle = frac > 0.5 ? '#4caf50' : frac > 0.25 ? '#e6b800' : '#d33a2c';
      ctx.fillRect(x - w / 2, y - 2, w * frac, 4);
    }
    drawLegged() {
      const sp = this.spec, s = this.sc;
      const D = makeDrawer(this.x + this.ox, this.y + this.oy, this.a, s);
      sp.legs.forEach((lg, i) => {
        for (const side of [1, -1]) {
          let sw;
          if (this.moving) { const off = ((i + (side > 0 ? 1 : 0)) % 2 === 0) ? 0 : Math.PI; sw = sp.swing * Math.sin(this.phase + off); }
          else sw = 1.2 * Math.sin(this.t * 7 + i * 1.7 + side);
          D.line([[lg[0], side * sp.ay], [lg[0] + lg[1], side * sp.ky], [lg[0] + lg[2] + sw, side * sp.fy]], sp.width, LEG);
        }
      });
      this['body_' + this.kind](D);
    }
    body_beetle(D) {
      D.poly(ellipse(-6, 0, 14, 10), BODY); D.poly(ellipse(9, 0, 8, 7), BODY); D.poly(ellipse(19, 0, 5, 5), BODY);
      D.line([[-19, 0], [7, 0]], 1, SHELL);
      const wig = 3 * Math.sin(this.t * 9);
      for (const side of [1, -1]) {
        D.line([[21, side * 2], [28, side * 6 + wig], [34, side * 5 - wig]], 1, LEG);
        D.line([[24, side], [31, side * (2 + 5 * this.lunge)]], 2, LEG);
      }
    }
    body_cockroach(D) {
      D.poly(ellipse(-4, 0, 15, 9), '#3b1f0e'); D.poly(ellipse(9, 0, 6, 6, 12), '#2a150a');
      D.line([[-18, 0], [5, 0]], 1, '#5a3418');
      const wig = 3 * Math.sin(this.t * 10);
      for (const side of [1, -1]) D.line([[13, side * 2], [24, side * 8 + wig], [38, side * 6 - wig]], 1, LEG);
    }
    body_spider(D) {
      D.poly(ellipse(-13, 0, 12, 9), BODY); D.poly(ellipse(4, 0, 8, 6.5), SHELL); D.poly(ellipse(-13, 0, 5, 4), SHELL);
      const fang = 1.2 * Math.sin(this.t * 9) + 2.5 * this.lunge;
      D.line([[11, -2], [14, -2 + fang]], 2, LEG); D.line([[11, 2], [14, 2 - fang]], 2, LEG);
      if (this.feast > 0) { D.poly(ellipse(19, 0, 9, 6), '#c4c4c4'); }
    }
    body_mantis(D) {
      D.poly(ellipse(-12, 0, 14, 4.5, 14), '#4f7a2c'); D.poly(ellipse(6, 0, 11, 3, 12), '#5a8a32'); D.poly(ellipse(20, 0, 4.5, 4, 10), '#6b9c3a');
      for (const side of [1, -1]) {
        D.poly(ellipse(22, side * 3, 1.5, 1.5, 6), BODY);
        if (this.lunge > 0.3) D.line([[12, side * 2], [28, side * 9], [42, side * 3]], 2, '#3f6624');
        else D.line([[12, side * 2], [21, side * 6], [17, side * 2]], 2, '#3f6624');
      }
      if (this.feast > 0) D.poly(ellipse(26, 0, 6, 4), '#c4c4c4');
    }
    body_scorpion(D) {
      D.poly(ellipse(0, 0, 13, 8, 16), '#5a4020'); D.poly(ellipse(10, 0, 6, 6, 12), '#4a3318');
      const sway = 2.5 * Math.sin(this.t * 4);
      for (const side of [1, -1]) { D.line([[10, side * 3], [19, side * 9], [27, side * 6]], 2, '#4a3318'); D.poly(ellipse(29, side * 6, 5, 3, 10), '#5a4020'); }
      const r = 16 * this.lunge;
      D.line([[-12, 0], [-24 + r, sway], [-31 + r * 1.5, -6 + sway], [-27 + r * 2, -15], [-17 + r * 2.6, -17]], 3, '#4a3318');
      D.poly([[-17 + r * 2.6, -20], [-10 + r * 2.6, -17], [-17 + r * 2.6, -14]], '#2a1c0a');
      if (this.feast > 0) D.poly(ellipse(32, 0, 6, 4), '#c4c4c4');
    }
    body_frog(D) {
      for (const side of [1, -1]) { D.line([[-6, side * 8], [-15, side * 17], [-4, side * 21]], 4, '#26561f'); D.line([[8, side * 8], [15, side * 13]], 3, '#26561f'); }
      D.poly(ellipse(0, 0, 14, 10), '#2f6b2a'); D.poly(ellipse(12, 0, 8, 8, 14), '#38792f');
      for (const side of [1, -1]) { D.poly(ellipse(15, side * 6, 3.2, 3.2, 8), '#d8d8a0'); D.poly(ellipse(16, side * 6, 1.4, 1.4, 6), BODY); }
      if (this.lunge > 0.3) D.poly(ellipse(19, 0, 3.5, 3, 8), '#7a1f2a');
    }
    drawCentipede() {
      const s = this.sc, n = this.segs.length, ox = this.ox, oy = this.oy;
      for (let i = n - 1; i >= 0; i--) {
        const x = this.segs[i][0] + ox, y = this.segs[i][1] + oy; let ang = this.a;
        if (i > 0) { const p = this.segs[i - 1]; if (p[0] !== this.segs[i][0] || p[1] !== this.segs[i][1]) ang = Math.atan2(p[1] - this.segs[i][1], p[0] - this.segs[i][0]); }
        const ca = Math.cos(ang), sa = Math.sin(ang), nx = -sa, ny = ca, ll = (14 + 10 * i / n) * s;
        const sw = this.moving ? 5 * s * Math.sin(this.phase * 1.5 + i * 0.9) : 1.2 * s * Math.sin(this.t * 6 + i);
        for (const side of [1, -1]) {
          ctx.beginPath(); ctx.moveTo(x + nx * 3 * s * side, y + ny * 3 * s * side);
          ctx.lineTo(x + nx * ll * 0.6 * side + ca * sw, y + ny * ll * 0.6 * side + sa * sw);
          ctx.lineTo(x + nx * ll * side + ca * sw * 1.6, y + ny * ll * side + sa * sw * 1.6);
          ctx.strokeStyle = LEG; ctx.lineWidth = 1; ctx.lineCap = 'round'; ctx.stroke();
        }
        const r = (i === 0 ? 6.5 : 5.2 - 1.5 * i / n) * s;
        ctx.fillStyle = BODY; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill();
        if (i % 2 === 0 && i > 0) { ctx.fillStyle = SHELL; ctx.beginPath(); ctx.arc(x, y, r * 0.55, 0, 7); ctx.fill(); }
      }
      const hx = this.segs[0][0] + ox, hy = this.segs[0][1] + oy, ca = Math.cos(this.a), sa = Math.sin(this.a);
      for (const side of [1, -1]) {
        const wig = 4 * s * Math.sin(this.t * 8 + side);
        ctx.beginPath(); ctx.moveTo(hx + ca * 6 * s, hy + sa * 6 * s);
        ctx.lineTo(hx + ca * 22 * s - sa * side * (8 * s + wig), hy + sa * 22 * s + ca * side * (8 * s + wig));
        ctx.lineTo(hx + ca * 38 * s - sa * side * (14 * s - wig), hy + sa * 38 * s + ca * side * (14 * s - wig));
        ctx.strokeStyle = LEG; ctx.lineWidth = 1; ctx.stroke();
      }
      if (this.feast > 0) { ctx.fillStyle = '#c4c4c4'; ctx.beginPath(); ctx.ellipse(hx + ca * 14 * s, hy + sa * 14 * s, 8 * s, 6 * s, this.a, 0, 7); ctx.fill(); }
    }
  }

  // ----------------------------------- Man -----------------------------------
  class Man {
    constructor(x, y) {
      this.x = x; this.y = y; this.a = 0; this.hp = MAN_ENERGY; this.maxhp = MAN_ENERGY;
      this.weapon = 3; this.swing = 0; this.swingCd = 0; this.hitDone = true; this.hurt = 0; this.ko = 0;
      this.calm = 0; this.phase = 0; this.walking = false; this.labelT = 2; this.t = 0;
      this.ammo = AMMO_MAX; this.fired = false; this.goto = null; this.run = false;
    }
    get active() { return this.ko <= 0; }
    setWeapon(i) { this.weapon = i; this.labelT = 1.6; this.goto = null; }
    nextWeapon() { this.setWeapon((this.weapon + 1) % WEAPONS.length); }
    trySwing() {
      if (this.ko > 0 || this.swing > 0 || this.swingCd > 0) return;
      const w = WEAPONS[this.weapon];
      if (w[0] === 'GUN') {
        if (this.goto) return;
        if (this.ammo < 1) { this.swingCd = 0.3; this.labelT = 1.0; return; }
        this.ammo -= 1; this.fired = true; this.swing = w[4]; this.swingCd = w[5]; this.hitDone = true; return;
      }
      this.swing = w[4]; this.swingCd = w[5]; this.hitDone = false;
    }
    progress() { const w = WEAPONS[this.weapon]; return this.swing > 0 ? 1 - this.swing / w[4] : 0; }
    damage(amount, fx, fy) {
      this.hp -= amount; this.hurt = 0.3; this.calm = 0;
      const d = hyp(this.x - fx, this.y - fy) || 1;
      this.x += (this.x - fx) / d * 10; this.y += (this.y - fy) / d * 10;
      if (this.hp <= 0) { this.hp = 0; this.ko = 6; this.swing = 0; }
    }
    update(dt, mx, my, w, h) {
      this.t += dt; this.hurt = Math.max(0, this.hurt - dt); this.swing = Math.max(0, this.swing - dt);
      this.swingCd = Math.max(0, this.swingCd - dt); this.labelT = Math.max(0, this.labelT - dt); this.walking = false;
      this.ammo = Math.min(AMMO_MAX, this.ammo + dt / AMMO_REGEN);
      if (this.ko > 0) { this.ko -= dt; if (this.ko <= 0) this.hp = this.maxhp * 0.5; return; }
      this.calm += dt;
      if (this.calm > 3 && this.hp < this.maxhp) this.hp = Math.min(this.maxhp, this.hp + 2 * dt);
      const gun = WEAPONS[this.weapon][0] === 'GUN';
      if (gun) {
        if (this.goto) {
          const gd = hyp(this.goto[0] - this.x, this.goto[1] - this.y);
          if (gd > 10) {
            const want = Math.atan2(this.goto[1] - this.y, this.goto[0] - this.x);
            this.a += clamp(angdiff(want, this.a), -12 * dt, 12 * dt);
            const sp = (this.run ? 330 : 160) * SIZE;
            this.x += Math.cos(this.a) * sp * dt; this.y += Math.sin(this.a) * sp * dt;
            this.walking = true; this.phase += sp * dt / (this.run ? 4 : 7);
          } else this.goto = null;
        } else if (hyp(mx - this.x, my - this.y) > 8) {
          this.a += clamp(angdiff(Math.atan2(my - this.y, mx - this.x), this.a), -9 * dt, 9 * dt);
        }
      } else {
        this.goto = null;
        const d = hyp(mx - this.x, my - this.y);
        if (d > 8 && this.swing <= 0) this.a += clamp(angdiff(Math.atan2(my - this.y, mx - this.x), this.a), -9 * dt, 9 * dt);
        if (d > 70) {
          const sp = Math.min(220 * SIZE, (d - 60) * 6);
          this.x += Math.cos(this.a) * sp * dt; this.y += Math.sin(this.a) * sp * dt;
          this.walking = true; this.phase += sp * dt / 7;
        }
      }
      this.x = clamp(this.x, 15, w - 15); this.y = clamp(this.y, 15, h - 15);
    }
    draw() {
      const s = SIZE, ca = Math.cos(this.a), sa = Math.sin(this.a);
      const D = makeDrawer(this.x, this.y, this.a, s), poly = D.poly, line = D.line;
      const frac = clamp(this.hp / this.maxhp, 0, 1), bx = this.x, by = this.y - 26 * s;
      ctx.fillStyle = '#202020'; ctx.fillRect(bx - 21, by - 4, 42, 8);
      ctx.fillStyle = frac > 0.5 ? '#3fa7ff' : frac > 0.25 ? '#e6b800' : '#d33a2c'; ctx.fillRect(bx - 20, by - 3, 40 * frac, 6);
      const name = WEAPONS[this.weapon][0];
      ctx.font = 'bold 11px system-ui, sans-serif'; ctx.textAlign = 'center';
      if (name === 'GUN') {
        const n = Math.floor(this.ammo);
        ctx.fillStyle = n ? '#222' : '#c0301e';
        ctx.fillText('GUN  ' + '|'.repeat(n) + '.'.repeat(AMMO_MAX - n), this.x, this.y + 30 * s);
      } else if (this.labelT > 0) { ctx.fillStyle = '#222'; ctx.fillText(name, this.x, this.y + 30 * s); }
      const cloth = this.hurt > 0 ? '#c03030' : '#2c4a8a', skin = '#e0b088';
      if (this.ko > 0) {
        poly(ellipse(0, 0, 11, 6), cloth); poly(ellipse(10, 0, 5, 5), skin);
        for (let i = 0; i < 3; i++) { const ang = this.t * 4 + i * 2.1; ctx.fillStyle = '#e6b800'; ctx.beginPath(); ctx.arc(this.x + 11 * Math.cos(ang), this.y - 14 + 4 * Math.sin(ang), 2, 0, 7); ctx.fill(); }
        return;
      }
      const stride = this.walking ? 5 * Math.sin(this.phase) : 0;
      for (const side of [1, -1]) poly(ellipse(stride * side, side * 4.5, 3.5, 2.4, 8), '#1a1a1a');
      poly(ellipse(0, 0, 5.5, 10, 14), cloth);
      const w = WEAPONS[this.weapon], p = this.progress(), arc = w[2], hand = [6, 8];
      let phi = this.swing > 0 ? arc - 2 * arc * (p * p * (3 - 2 * p)) : -0.2;
      if (name === 'GUN') phi = 0;
      line([[0, 9], hand], 3, skin); line([[0, -9], [5, -8]], 3, skin);
      if (name === 'SWORD') {
        const tx = hand[0] + 38 * Math.cos(phi), ty = hand[1] + 38 * Math.sin(phi);
        line([hand, [tx, ty]], 3, '#8d929b');
        const gx = hand[0] + 6 * Math.cos(phi), gy = hand[1] + 6 * Math.sin(phi);
        line([[gx - 4 * Math.sin(phi), gy + 4 * Math.cos(phi)], [gx + 4 * Math.sin(phi), gy - 4 * Math.cos(phi)]], 2, '#7a5a2a');
      } else if (name === 'HAMMER') {
        const ex = hand[0] + 28 * Math.cos(phi), ey = hand[1] + 28 * Math.sin(phi);
        line([hand, [ex, ey]], 3, '#6b4a22');
        const nx = -Math.sin(phi), ny = Math.cos(phi), fx = Math.cos(phi), fy = Math.sin(phi);
        poly([[ex - fx * 4 + nx * 7, ey - fy * 4 + ny * 7], [ex + fx * 9 + nx * 7, ey + fy * 9 + ny * 7], [ex + fx * 9 - nx * 7, ey + fy * 9 - ny * 7], [ex - fx * 4 - nx * 7, ey - fy * 4 - ny * 7]], '#6b6f76');
      } else if (name === 'GUN') {
        line([hand, [hand[0] + 17, hand[1]]], 4, '#3a3a3f'); line([[hand[0] + 2, hand[1]], [hand[0] + 1, hand[1] + 6]], 3, '#2a2a2e');
        line([[0, -9], [hand[0] + 9, hand[1] - 1]], 3, skin);
        if (this.swing > 0 && p < 0.7) { const fx = hand[0] + 20, fy = hand[1]; poly([[fx, fy], [fx + 6, fy - 4], [fx + 14, fy], [fx + 6, fy + 4]], '#ffb800'); }
      } else {
        const reach = this.swing > 0 ? 6 + 22 * Math.sin(p * Math.PI) : 6;
        poly(ellipse(hand[0] + reach, hand[1] - 3 * (1 - reach / 28), 3.6, 3.6, 8), skin); poly(ellipse(7, -8, 3.2, 3.2, 8), skin);
      }
      poly(ellipse(1, 0, 5.2, 5.2, 12), skin);
      poly([[-5, -5], [0, -6.5], [-1.5, 0], [0, 6.5], [-5, 5]], '#3a2a1a');
    }
  }

  // ---------------------------------- World ----------------------------------
  class World {
    constructor(w, h) {
      this.w = w; this.h = h; this.bugs = []; this.man = new Man(w / 2, h / 2);
      this.splats = []; this.fx = []; this.bullets = []; this.now = 0; this.lastDeath = 0;
      this.nextSpawn = 1.0; this.firstSpawns = 2; this.kills = 0; this.lastClick = -9;
    }
    spawn() {
      const live = this.bugs.filter(b => b.alive);
      const extra = Math.min(MAX_EXTRA, Math.floor((this.now - this.lastDeath) / NO_DEATH_SECONDS));
      if (live.length >= MAX_BUGS + extra) return;
      const big = live.filter(b => b.spec.big).length;
      const kinds = [], weights = [];
      for (const k in SPECS) { const sp = SPECS[k]; if (sp.big && big >= MAX_BIG + Math.floor(extra / 2)) continue; kinds.push(k); weights.push(sp.weight); }
      let r = Math.random() * weights.reduce((a, b) => a + b, 0), i = 0;
      while (i < weights.length - 1 && r > weights[i]) { r -= weights[i]; i++; }
      this.bugs.push(new Insect(kinds[i], this.w, this.h));
    }
    splat(x, y, col, scale) {
      const blobs = [], s = SIZE * Math.max(0.4, scale);
      for (let i = 0; i < 6; i++) { const a = rnd(0, 7), d = rnd(15, 38) * s; blobs.push([x + Math.cos(a) * d, y + Math.sin(a) * d, rnd(1.5, 4) * s]); }
      this.splats.push({ x, y, r: 13 * s, col, blobs, exp: this.now + 8 });
    }
    contact(a, b) { return (a.radius + b.radius) * 0.85 + 4; }
    nearest(ins, group, limit) {
      let best = null, bd = limit;
      for (const g of group) { const d = hyp(g.x - ins.x, g.y - ins.y); if (d < bd) { best = g; bd = d; } }
      return [best, bd];
    }
    damage(b, dmg, by) {
      b.hp -= dmg; b.shake = 0.3; this.fx.push({ x: b.x, y: b.y, size: 6 + Math.min(14, dmg * 0.4), exp: this.now + 0.2 });
      if (b.hp > 0) return;
      b.alive = false; b.hp = 0; this.lastDeath = this.now; this.kills++;
      let eaten = false;
      if (b.foe) { b.foe.foe = null; b.foe = null; }
      if (by) { by.foe = null; if (by.spec.eats) { by.feast = 3.5; eaten = true; } }
      if (!eaten) this.splat(b.x, b.y, b.kind === 'mantis' || b.kind === 'frog' ? '#1b2b14' : '#1b1b12', b.spec.scale * 0.8);
    }
    strike(a, b) {
      a.atkT = a.spec.rate * rnd(0.8, 1.3); a.lunge = 1;
      if (Math.random() < 0.75) {
        let dmg = a.spec.atk * rnd(0.6, 1.4);
        if (a.first) { a.first = false; if (a.spec.creep === 0) dmg *= 1.8; }
        this.damage(b, dmg, a);
      }
    }
    disengage(a, b) {
      a.foe = b.foe = null;
      const loser = a.hp / a.maxhp < b.hp / b.maxhp ? a : b, winner = loser === a ? b : a;
      loser.fleeT = 5; loser.fleeFrom = [winner.x, winner.y]; winner.freeze = 1.2;
    }
    manHit() {
      const m = this.man, w = WEAPONS[m.weapon], rng = w[1], arc = w[2], dmg = w[3], kb = w[6], stun = w[7];
      for (const b of this.bugs) {
        if (!b.alive) continue;
        for (const [px, py, pr] of b.points()) {
          const d = hyp(px - m.x, py - m.y);
          if (d - pr > rng * SIZE) continue;
          if (Math.abs(angdiff(Math.atan2(py - m.y, px - m.x), m.a)) > arc && d > pr) continue;
          this.damage(b, dmg * rnd(0.9, 1.1), null);
          if (b.alive) {
            const ang = Math.atan2(b.y - m.y, b.x - m.x); b.x += Math.cos(ang) * kb; b.y += Math.sin(ang) * kb;
            if (b.segs.length) b.follow();
            if (stun) { b.freeze = Math.max(b.freeze, stun); b.atkT = Math.max(b.atkT, stun); }
          }
          break;
        }
      }
    }
    think(ins, dt, live) {
      const spec = ins.spec, m = this.man;
      ins.atkT -= dt; ins.fleeT -= dt; ins.lunge = Math.max(0, ins.lunge - dt * 4); ins.shake = Math.max(0, ins.shake - dt);
      ins.ox = Math.cos(ins.a) * ins.lunge * 12 * ins.sc; ins.oy = Math.sin(ins.a) * ins.lunge * 12 * ins.sc;
      if (ins.shake > 0) { ins.ox += rnd(-4, 4) * ins.shake * 3; ins.oy += rnd(-4, 4) * ins.shake * 3; }
      if (ins.foe) {
        const f = ins.foe;
        if (!f.alive || f.foe !== ins) ins.foe = null;
        else {
          ins.fightT += dt;
          const ang = Math.atan2(f.y - ins.y, f.x - ins.x);
          ins.a += clamp(angdiff(ang, ins.a), -8 * dt, 8 * dt);
          const d = hyp(f.x - ins.x, f.y - ins.y), want = this.contact(ins, f);
          if (d > want * 1.05) { ins.x += Math.cos(ang) * 70 * dt; ins.y += Math.sin(ang) * 70 * dt; }
          else if (d < want * 0.7) { ins.x -= Math.cos(ang) * 40 * dt; ins.y -= Math.sin(ang) * 40 * dt; }
          ins.moving = true; ins.phase += dt * 8; ins.t += dt;
          if (ins.freeze > 0) ins.freeze -= dt; else if (ins.atkT <= 0) this.strike(ins, f);
          if (ins.alive && ins.foe) {
            if ((ins.hp < 0.25 * ins.maxhp && Math.random() < dt * 0.6) || ins.fightT > 25) this.disengage(ins, f);
          }
          ins.keepOnScreen(); return;
        }
      }
      let goal = null, boost = 1;
      const manOn = m.active, dm = hyp(m.x - ins.x, m.y - ins.y);
      // run from stronger fighters
      let threat = null, best = 1e9;
      for (const o of live) {
        if (o === ins || o.kind === ins.kind || o.feast > 0 || o.foe || o.fleeT > 0 || o.spec.creep === 0) continue;
        if (ins.power >= 0.8 * o.power) continue;
        const d = hyp(o.x - ins.x, o.y - ins.y);
        if (d < Math.max(70, o.spec.sight * 0.6 * SIZE) && d < best) { threat = o; best = d; }
      }
      if (ins.feast > 0) { /* eating */ }
      else if (threat) { goal = ins.awayGoal(threat.x, threat.y); boost = 1.7; }
      else if (ins.fleeT > 0) { goal = ins.awayGoal(ins.fleeFrom[0], ins.fleeFrom[1]); boost = 1.7; }
      else { const r = this.pickFight(ins, live, m, manOn, dm, dt); goal = r[0]; boost = r[1]; }
      if (ins.hp < ins.maxhp && !ins.foe) ins.hp = Math.min(ins.maxhp, ins.hp + ins.maxhp * 0.01 * dt);
      ins.update(dt, goal, boost);
    }
    pickFight(ins, live, m, manOn, dm, dt) {
      const spec = ins.spec; let target = null, tman = false;
      if (ins.hates && manOn && dm < spec.sight * SIZE + 120) { target = m; tman = true; }
      else {
        const ratioMax = 0.4 + 1.4 * ins.bold; let bd = spec.sight * SIZE;
        for (const o of live) {
          if (o === ins || o.kind === ins.kind || o.foe || o.power > ratioMax * ins.power) continue;
          const d = hyp(o.x - ins.x, o.y - ins.y); if (d < bd) { target = o; bd = d; }
        }
      }
      if (!target) { ins.waitT = 0; return [null, 1]; }
      const d = hyp(target.x - ins.x, target.y - ins.y), ang = Math.atan2(target.y - ins.y, target.x - ins.x);
      if (tman) {
        if (d <= ins.radius + 16) {
          ins.a += clamp(angdiff(ang, ins.a), -8 * dt, 8 * dt); ins.freeze = Math.max(ins.freeze, 0.05);
          if (ins.atkT <= 0) {
            ins.atkT = spec.rate * rnd(1.0, 1.5); ins.lunge = 1;
            m.damage(spec.mdmg * rnd(0.7, 1.3), ins.x, ins.y);
            this.fx.push({ x: m.x, y: m.y, size: 9, exp: this.now + 0.2 });
          }
          return [null, 1];
        }
      } else if (d <= this.contact(ins, target)) {
        ins.foe = target; target.foe = ins; ins.fightT = target.fightT = 0; ins.first = true; target.first = false;
        ins.atkT = rnd(0.2, 0.5); target.atkT = rnd(0.4, 0.9); return [null, 1];
      }
      if (d < spec.strike * ins.sc) return [[target.x, target.y], spec.rush];
      if (spec.creep === 0) {
        ins.waitT += dt;
        if (ins.waitT > 3) return [[target.x, target.y], 0.35];
        ins.freeze = 0.1; ins.a += clamp(angdiff(ang, ins.a), -3 * dt, 3 * dt); return [null, 1];
      }
      return [[target.x, target.y], spec.creep];
    }
    click(mx, my, isDouble) {
      const m = this.man;
      if (isDouble && WEAPONS[m.weapon][0] === 'GUN' && m.active) { m.goto = [mx, my]; m.run = hyp(mx - m.x, my - m.y) > 250 * SIZE; }
      else m.trySwing();
    }
    tick(dt, mx, my) {
      this.now += dt; const m = this.man;
      const was = m.swing > 0; m.update(dt, mx, my, this.w, this.h);
      if (was && !m.hitDone && m.progress() >= 0.5) { m.hitDone = true; this.manHit(); }
      if (m.fired) {
        m.fired = false; const ca = Math.cos(m.a), sa = Math.sin(m.a), k = SIZE;
        this.bullets.push({ x: m.x + (24 * ca - 8 * sa) * k, y: m.y + (24 * sa + 8 * ca) * k, vx: ca * 760, vy: sa * 760, dist: 0 });
      }
      for (let i = this.bullets.length - 1; i >= 0; i--) {
        const bl = this.bullets[i]; bl.x += bl.vx * dt; bl.y += bl.vy * dt; bl.dist += 760 * dt;
        let hit = false;
        for (const b of this.bugs) {
          if (!b.alive) continue;
          for (const [px, py, pr] of b.points()) if (hyp(px - bl.x, py - bl.y) < pr + 4) {
            this.damage(b, BULLET_DAMAGE * rnd(0.9, 1.1), null);
            if (b.alive) { b.x += bl.vx / 760 * 8; b.y += bl.vy / 760 * 8; if (b.segs.length) b.follow(); }
            hit = true; break;
          }
          if (hit) break;
        }
        if (hit || bl.dist > 700 || bl.x < -20 || bl.x > this.w + 20 || bl.y < -20 || bl.y > this.h + 20) this.bullets.splice(i, 1);
      }
      if (this.now >= this.nextSpawn) {
        this.spawn();
        if (this.firstSpawns > 0) { this.firstSpawns--; this.nextSpawn = this.now + 2; } else this.nextSpawn = this.now + rnd(SPAWN_MIN, SPAWN_MAX);
      }
      const live = this.bugs.filter(b => b.alive);
      for (const b of live) if (b.alive) this.think(b, dt, live);
      this.splats = this.splats.filter(s => this.now < s.exp);
      this.fx = this.fx.filter(f => this.now < f.exp);
      this.bugs = this.bugs.filter(b => b.alive);
    }
    draw() {
      for (const s of this.splats) {
        ctx.globalAlpha = clamp((s.exp - this.now) / 2, 0, 1); ctx.fillStyle = s.col;
        ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, 7); ctx.fill();
        for (const b of s.blobs) { ctx.beginPath(); ctx.arc(b[0], b[1], b[2], 0, 7); ctx.fill(); }
      }
      ctx.globalAlpha = 1;
      for (const b of this.bugs) b.draw();
      this.man.draw();
      for (const bl of this.bullets) {
        ctx.beginPath(); ctx.moveTo(bl.x, bl.y); ctx.lineTo(bl.x - bl.vx / 760 * 16, bl.y - bl.vy / 760 * 16);
        ctx.strokeStyle = '#d98a00'; ctx.lineWidth = 3; ctx.lineCap = 'round'; ctx.stroke();
      }
      for (const f of this.fx) {
        for (let i = 0; i < 6; i++) {
          const ang = i * Math.PI / 3 + this.now * 5;
          ctx.beginPath(); ctx.moveTo(f.x + Math.cos(ang) * f.size * 0.4, f.y + Math.sin(ang) * f.size * 0.4);
          ctx.lineTo(f.x + Math.cos(ang) * f.size, f.y + Math.sin(ang) * f.size);
          ctx.strokeStyle = '#e6a800'; ctx.lineWidth = 2; ctx.stroke();
        }
      }
    }
  }

  // ------------------------------- page glue -------------------------------
  function start(canvas, hooks) {
    ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    const world = new World(W, H);
    let mx = W / 2 + 120, my = H / 2, last = 0, lastDown = -9;
    const pos = e => { const r = canvas.getBoundingClientRect(); return [(e.clientX - r.left) * W / r.width, (e.clientY - r.top) * H / r.height]; };
    canvas.addEventListener('mousemove', e => { [mx, my] = pos(e); });
    canvas.addEventListener('mousedown', e => {
      [mx, my] = pos(e); const t = performance.now() / 1000; const dbl = t - lastDown < 0.4; lastDown = dbl ? -9 : t;
      world.click(mx, my, dbl); e.preventDefault();
    });
    canvas.addEventListener('contextmenu', e => e.preventDefault());
    window.addEventListener('keydown', e => {
      if (e.key === 'F9' || e.key === 'q' || e.key === 'Q') { world.man.nextWeapon(); hooks && hooks.onWeapon && hooks.onWeapon(world.man.weapon); e.preventDefault(); }
      const n = '1234'.indexOf(e.key);
      if (n >= 0) { world.man.setWeapon(n); hooks && hooks.onWeapon && hooks.onWeapon(n); }
    });
    function frame(ts) {
      const t = ts / 1000, dt = Math.min(t - last, 0.05); last = t;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#d8d4c6'; ctx.fillRect(0, 0, W, H);
      world.tick(dt, mx, my); world.draw();
      hooks && hooks.onFrame && hooks.onFrame(world);
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(t => { last = t / 1000; frame(t); });
    return world;
  }

  const api = { start, World, Insect, Man, SPECS, WEAPONS, setCtx: c => { ctx = c; } };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.ScreenInsect = api;
})(typeof window !== 'undefined' ? window : globalThis);
