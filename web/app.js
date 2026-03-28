// =============================================
// 🔭 TELESCOPE WEB - APPLICATION ENGINE
// =============================================

// ---- Celestial Math Engine ----
class CelestialEngine {
  constructor(lat, lon) {
    this.latitude = lat;
    this.longitude = lon;
    this.locationName = "Phoenix, AZ";
  }

  setLocation(lat, lon, name) {
    this.latitude = lat;
    this.longitude = lon;
    this.locationName = name || `${lat.toFixed(2)}°, ${lon.toFixed(2)}°`;
  }

  calculateLST() {
    const now = new Date();
    const jd = this.julianDate(now);
    const T = (jd - 2451545.0) / 36525.0;
    let gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T * T;
    gmst = ((gmst % 360) + 360) % 360;
    return (gmst + this.longitude + 360) % 360;
  }

  julianDate(date) {
    const y = date.getUTCFullYear();
    const m = date.getUTCMonth() + 1;
    const d = date.getUTCDate() + date.getUTCHours() / 24 + date.getUTCMinutes() / 1440 + date.getUTCSeconds() / 86400;
    let jy = y, jm = m;
    if (m <= 2) { jy--; jm += 12; }
    const A = Math.floor(jy / 100);
    const B = 2 - A + Math.floor(A / 4);
    return Math.floor(365.25 * (jy + 4716)) + Math.floor(30.6001 * (jm + 1)) + d + B - 1524.5;
  }

  raDecToAltAz(ra, dec) {
    const lst = this.calculateLST();
    const ha = ((lst - ra + 360) % 360) * Math.PI / 180;
    const decR = dec * Math.PI / 180;
    const latR = this.latitude * Math.PI / 180;

    const sinAlt = Math.sin(decR) * Math.sin(latR) + Math.cos(decR) * Math.cos(latR) * Math.cos(ha);
    const alt = Math.asin(sinAlt) * 180 / Math.PI;

    let cosAz = (Math.sin(decR) - Math.sin(latR) * sinAlt) / (Math.cos(latR) * Math.cos(alt * Math.PI / 180));
    cosAz = Math.max(-1, Math.min(1, cosAz));
    let az = Math.acos(cosAz) * 180 / Math.PI;
    if (Math.sin(ha) > 0) az = 360 - az;

    return { altitude: alt, azimuth: az };
  }

  angularDistance(ra1, dec1, ra2, dec2) {
    const r1 = ra1 * Math.PI / 180, d1 = dec1 * Math.PI / 180;
    const r2 = ra2 * Math.PI / 180, d2 = dec2 * Math.PI / 180;
    const dra = r2 - r1, ddec = d2 - d1;
    const a = Math.sin(ddec / 2) ** 2 + Math.cos(d1) * Math.cos(d2) * Math.sin(dra / 2) ** 2;
    return Math.asin(Math.sqrt(a)) * 2 * 180 / Math.PI;
  }

  isNighttime() {
    const hour = new Date().getHours();
    return hour < 6 || hour >= 18;
  }

  getMoonPhase() {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    const day = now.getDate();
    let c = 0, e = 0, jd = 0, b = 0;
    if (month < 3) { c = 4716; e = 1524; } else { c = 4716; e = 1524; }
    const a2 = Math.floor((14 - month) / 12);
    const y = year + 4800 - a2;
    const m = month + 12 * a2 - 3;
    jd = day + Math.floor((153 * m + 2) / 5) + 365 * y + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400) - 32045;
    const daysSinceNew = (jd - 2451550.1) % 29.530588853;
    const phase = ((daysSinceNew + 29.530588853) % 29.530588853);
    const illumination = (1 - Math.cos(phase / 29.530588853 * 2 * Math.PI)) / 2 * 100;

    let phaseName;
    if (phase < 1.85) phaseName = "New Moon";
    else if (phase < 5.53) phaseName = "Waxing Crescent";
    else if (phase < 9.22) phaseName = "First Quarter";
    else if (phase < 12.91) phaseName = "Waxing Gibbous";
    else if (phase < 16.61) phaseName = "Full Moon";
    else if (phase < 20.30) phaseName = "Waning Gibbous";
    else if (phase < 23.99) phaseName = "Last Quarter";
    else if (phase < 27.68) phaseName = "Waning Crescent";
    else phaseName = "New Moon";

    // Approximate moon RA/Dec (simplified)
    const moonLon = (phase / 29.53 * 360 + 180) % 360;
    return {
      phase: phaseName,
      illumination: Math.round(illumination),
      ra: moonLon,
      dec: -5 + 10 * Math.sin(moonLon * Math.PI / 180),
      phaseAngle: phase / 29.53
    };
  }

  getPlanetPositions() {
    const now = new Date();
    const jd = this.julianDate(now);
    const daysSinceJ2000 = jd - 2451545.0;
    const positions = {};

    for (const [name, orbit] of Object.entries(PLANET_ORBITS)) {
      const meanLon = (orbit.lon0 + orbit.lonRate * daysSinceJ2000) % 360;
      const ra = ((meanLon + 360) % 360);
      const dec = orbit.i * Math.sin(ra * Math.PI / 180) * 0.5;
      const altAz = this.raDecToAltAz(ra, dec);

      positions[name] = {
        ra, dec,
        altitude: altAz.altitude,
        azimuth: altAz.azimuth,
        visible: altAz.altitude > 0,
        distance_au: orbit.a
      };
    }
    return positions;
  }

  getVisibleStars(minAlt = 10) {
    return STARS.filter(s => {
      if (!s.ra || !s.dec) return false;
      const { altitude } = this.raDecToAltAz(s.ra, s.dec);
      return altitude >= minAlt;
    }).map(s => {
      const { altitude, azimuth } = this.raDecToAltAz(s.ra, s.dec);
      return { ...s, altitude, azimuth };
    }).sort((a, b) => a.magnitude - b.magnitude);
  }
}

// ---- Star Map (Canvas) ----
class StarMap {
  constructor(canvas, engine) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.engine = engine;

    // View state
    this.centerRA = 180;
    this.centerDec = 20;
    this.zoom = 1.0;
    this.showConstellations = true;
    this.showLabels = true;
    this.showGrid = false;
    this.showMessier = true;

    // Interaction state
    this.isDragging = false;
    this.dragStart = { x: 0, y: 0 };
    this.hoveredObject = null;
    this.selectedObject = null;

    // Telescope crosshair
    this.telescopeRA = null;
    this.telescopeDec = null;
    this.isSlewing = false;
    this.slewTargetRA = null;
    this.slewTargetDec = null;

    this.resize();
    this.bindEvents();
    this.animate();
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width * devicePixelRatio;
    this.canvas.height = rect.height * devicePixelRatio;
    this.canvas.style.width = rect.width + 'px';
    this.canvas.style.height = rect.height + 'px';
    this.ctx.scale(devicePixelRatio, devicePixelRatio);
    this.W = rect.width;
    this.H = rect.height;
  }

  bindEvents() {
    window.addEventListener('resize', () => this.resize());

    this.canvas.addEventListener('mousedown', (e) => {
      this.isDragging = true;
      this.dragStart = { x: e.clientX, y: e.clientY, ra: this.centerRA, dec: this.centerDec };
    });

    window.addEventListener('mousemove', (e) => {
      if (this.isDragging) {
        const dx = e.clientX - this.dragStart.x;
        const dy = e.clientY - this.dragStart.y;
        const scale = 360 / (this.W * this.zoom);
        this.centerRA = ((this.dragStart.ra + dx * scale) + 360) % 360;
        this.centerDec = Math.max(-90, Math.min(90, this.dragStart.dec + dy * scale));
      } else {
        const rect = this.canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        this.updateHover(mx, my);
      }
    });

    window.addEventListener('mouseup', () => this.isDragging = false);

    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 0.9 : 1.1;
      this.zoom = Math.max(0.3, Math.min(8, this.zoom * factor));
    }, { passive: false });

    this.canvas.addEventListener('click', (e) => {
      if (this.hoveredObject) {
        app.selectObject(this.hoveredObject);
      }
    });

    this.canvas.addEventListener('dblclick', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const coords = this.screenToRADec(mx, my);
      if (coords) this.gotoRADec(coords.ra, coords.dec);
    });
  }

  raDecToScreen(ra, dec) {
    let dra = ra - this.centerRA;
    if (dra > 180) dra -= 360;
    if (dra < -180) dra += 360;

    const pixPerDeg = this.W * this.zoom / 360;
    const x = this.W / 2 - dra * pixPerDeg;
    const y = this.H / 2 - (dec - this.centerDec) * pixPerDeg;
    return { x, y };
  }

  screenToRADec(sx, sy) {
    const pixPerDeg = this.W * this.zoom / 360;
    const dra = -(sx - this.W / 2) / pixPerDeg;
    const ddec = -(sy - this.H / 2) / pixPerDeg;
    return {
      ra: ((this.centerRA + dra) + 360) % 360,
      dec: Math.max(-90, Math.min(90, this.centerDec + ddec))
    };
  }

  getStarColor(type) {
    const colors = {
      'O': '#9bb0ff', 'B': '#aabfff', 'A': '#cad7ff', 'F': '#f8f7ff',
      'G': '#fff4ea', 'K': '#ffd2a1', 'M': '#ffcc6f'
    };
    return colors[type?.[0]?.toUpperCase()] || '#ccc';
  }

  getStarSize(mag) {
    const base = Math.max(1, 6 - mag * 0.5);
    return base * Math.sqrt(this.zoom) * 0.7;
  }

  updateHover(mx, my) {
    let closest = null;
    let minDist = 20;

    const allObjects = [
      ...STARS.filter(s => s.ra && s.dec).map(s => ({ ...s, objType: 'star' })),
      ...MESSIER_OBJECTS.map(m => ({ ...m, objType: 'messier' })),
    ];

    // Add planets
    const planets = this.engine.getPlanetPositions();
    for (const [name, pos] of Object.entries(planets)) {
      const pd = PLANETS.find(p => p.name === name);
      if (pd) allObjects.push({ ...pd, ra: pos.ra, dec: pos.dec, objType: 'planet' });
    }

    for (const obj of allObjects) {
      if (!obj.ra) continue;
      const pos = this.raDecToScreen(obj.ra, obj.dec);
      const d = Math.hypot(pos.x - mx, pos.y - my);
      if (d < minDist) {
        minDist = d;
        closest = obj;
      }
    }

    this.hoveredObject = closest;
    this.canvas.style.cursor = closest ? 'pointer' : 'grab';

    // Update tooltip
    const tooltip = document.getElementById('tooltip');
    if (closest) {
      tooltip.innerHTML = `<div class="tooltip-name">${closest.name}</div><div class="tooltip-meta">${closest.constellation || closest.type || ''}</div>`;
      tooltip.classList.add('active');
      const rect = this.canvas.getBoundingClientRect();
      const pos = this.raDecToScreen(closest.ra, closest.dec);
      tooltip.style.left = (rect.left + pos.x + 16) + 'px';
      tooltip.style.top = (rect.top + pos.y - 10) + 'px';
    } else {
      tooltip.classList.remove('active');
    }
  }

  gotoRADec(ra, dec) {
    if (this.isSlewing) return;
    this.isSlewing = true;
    this.slewTargetRA = ra;
    this.slewTargetDec = dec;
    this.telescopeRA = this.telescopeRA ?? this.centerRA;
    this.telescopeDec = this.telescopeDec ?? this.centerDec;

    const startRA = this.centerRA;
    const startDec = this.centerDec;
    const startTelRA = this.telescopeRA;
    const startTelDec = this.telescopeDec;
    const startTime = performance.now();
    const duration = 1500;

    const animate = (now) => {
      let t = Math.min(1, (now - startTime) / duration);
      t = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; // easeInOutCubic

      let dra = ra - startRA;
      if (dra > 180) dra -= 360;
      if (dra < -180) dra += 360;
      this.centerRA = ((startRA + dra * t) + 360) % 360;
      this.centerDec = startDec + (dec - startDec) * t;

      let tdra = ra - startTelRA;
      if (tdra > 180) tdra -= 360;
      if (tdra < -180) tdra += 360;
      this.telescopeRA = ((startTelRA + tdra * t) + 360) % 360;
      this.telescopeDec = startTelDec + (dec - startTelDec) * t;

      if (t < 1) {
        requestAnimationFrame(animate);
      } else {
        this.isSlewing = false;
        this.telescopeRA = ra;
        this.telescopeDec = dec;
        app.updateHUD();
      }
    };
    requestAnimationFrame(animate);
    app.updateHUD();
  }

  draw() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.W, this.H);

    // Background gradient
    const grad = ctx.createRadialGradient(this.W / 2, this.H / 2, 0, this.W / 2, this.H / 2, this.W * 0.8);
    grad.addColorStop(0, '#0d1025');
    grad.addColorStop(1, '#06080f');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, this.W, this.H);

    // Subtle background stars
    if (!this._bgStars) {
      this._bgStars = [];
      for (let i = 0; i < 400; i++) {
        this._bgStars.push({
          ra: Math.random() * 360,
          dec: Math.random() * 180 - 90,
          size: Math.random() * 0.8 + 0.3,
          alpha: Math.random() * 0.4 + 0.1
        });
      }
    }
    for (const s of this._bgStars) {
      const pos = this.raDecToScreen(s.ra, s.dec);
      if (pos.x < -10 || pos.x > this.W + 10 || pos.y < -10 || pos.y > this.H + 10) continue;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, s.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(200, 210, 240, ${s.alpha * (0.5 + 0.5 * Math.sin(performance.now() / 2000 + s.ra))})`;
      ctx.fill();
    }

    // Grid
    if (this.showGrid) {
      ctx.strokeStyle = 'rgba(74, 158, 255, 0.06)';
      ctx.lineWidth = 0.5;
      for (let ra = 0; ra < 360; ra += 15) {
        const p1 = this.raDecToScreen(ra, -90);
        const p2 = this.raDecToScreen(ra, 90);
        ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
      }
      for (let dec = -90; dec <= 90; dec += 15) {
        ctx.beginPath();
        for (let ra = 0; ra <= 360; ra += 2) {
          const p = this.raDecToScreen(ra, dec);
          ra === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
        }
        ctx.stroke();
      }
    }

    // Constellation lines
    if (this.showConstellations) {
      ctx.strokeStyle = 'rgba(74, 158, 255, 0.2)';
      ctx.lineWidth = 1;
      for (const [constName, lines] of Object.entries(CONSTELLATION_LINES)) {
        for (const [name1, name2] of lines) {
          const s1 = STARS.find(s => s.name === name1);
          const s2 = STARS.find(s => s.name === name2);
          if (!s1?.ra || !s2?.ra) continue;
          const p1 = this.raDecToScreen(s1.ra, s1.dec);
          const p2 = this.raDecToScreen(s2.ra, s2.dec);
          if (Math.hypot(p2.x - p1.x, p2.y - p1.y) > this.W) continue;
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }
      }
    }

    // Messier objects
    if (this.showMessier) {
      for (const m of MESSIER_OBJECTS) {
        const pos = this.raDecToScreen(m.ra, m.dec);
        if (pos.x < -20 || pos.x > this.W + 20 || pos.y < -20 || pos.y > this.H + 20) continue;
        const size = Math.max(3, (8 - m.mag) * 0.8) * Math.sqrt(this.zoom) * 0.5;

        // Fuzzy glow for deep sky objects
        const glow = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, size * 3);
        glow.addColorStop(0, 'rgba(167, 139, 250, 0.5)');
        glow.addColorStop(0.5, 'rgba(167, 139, 250, 0.15)');
        glow.addColorStop(1, 'rgba(167, 139, 250, 0)');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, size * 3, 0, Math.PI * 2);
        ctx.fill();

        // Core
        ctx.fillStyle = 'rgba(200, 180, 255, 0.7)';
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, size, 0, Math.PI * 2);
        ctx.fill();

        if (this.showLabels && this.zoom > 1.5) {
          ctx.fillStyle = 'rgba(167, 139, 250, 0.7)';
          ctx.font = `${Math.max(9, 10 * Math.sqrt(this.zoom) * 0.5)}px Inter`;
          ctx.textAlign = 'left';
          ctx.fillText(m.name, pos.x + size + 5, pos.y + 3);
        }
      }
    }

    // Stars
    const starsToRender = STARS.filter(s => s.ra !== null && s.dec !== null);
    for (const star of starsToRender) {
      const pos = this.raDecToScreen(star.ra, star.dec);
      if (pos.x < -20 || pos.x > this.W + 20 || pos.y < -20 || pos.y > this.H + 20) continue;

      // Skip very dim stars at low zoom
      if (star.magnitude > 8 && this.zoom < 2) continue;
      if (star.magnitude > 12 && this.zoom < 4) continue;

      const size = this.getStarSize(star.magnitude);
      const color = this.getStarColor(star.type);

      // Glow for bright stars
      if (star.magnitude < 2) {
        const glow = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, size * 4);
        glow.addColorStop(0, color + '40');
        glow.addColorStop(1, color + '00');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, size * 4, 0, Math.PI * 2);
        ctx.fill();
      }

      // Star dot
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, size, 0, Math.PI * 2);
      ctx.fill();

      // Labels for bright stars
      if (this.showLabels && star.magnitude < (this.zoom > 2 ? 6 : 2)) {
        ctx.fillStyle = 'rgba(232, 236, 244, 0.6)';
        ctx.font = `${Math.max(9, 11 * Math.sqrt(this.zoom) * 0.5)}px Inter`;
        ctx.textAlign = 'left';
        ctx.fillText(star.name, pos.x + size + 4, pos.y + 3);
      }
    }

    // Planets
    const planetPositions = this.engine.getPlanetPositions();
    for (const [name, pos] of Object.entries(planetPositions)) {
      const screenPos = this.raDecToScreen(pos.ra, pos.dec);
      if (screenPos.x < -20 || screenPos.x > this.W + 20 || screenPos.y < -20 || screenPos.y > this.H + 20) continue;

      const pd = PLANETS.find(p => p.name === name);
      const color = pd?.color || '#ffcc00';
      const size = 4 * Math.sqrt(this.zoom) * 0.7;

      // Planet glow
      const glow = ctx.createRadialGradient(screenPos.x, screenPos.y, 0, screenPos.x, screenPos.y, size * 3);
      glow.addColorStop(0, color + '60');
      glow.addColorStop(1, color + '00');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(screenPos.x, screenPos.y, size * 3, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(screenPos.x, screenPos.y, size, 0, Math.PI * 2);
      ctx.fill();

      if (this.showLabels) {
        ctx.fillStyle = color;
        ctx.font = `bold ${Math.max(10, 11 * Math.sqrt(this.zoom) * 0.5)}px Inter`;
        ctx.textAlign = 'left';
        ctx.fillText(name, screenPos.x + size + 5, screenPos.y + 3);
      }
    }

    // Moon
    const moon = this.engine.getMoonPhase();
    const moonPos = this.raDecToScreen(moon.ra, moon.dec);
    if (moonPos.x > -30 && moonPos.x < this.W + 30 && moonPos.y > -30 && moonPos.y < this.H + 30) {
      const moonSize = 8 * Math.sqrt(this.zoom) * 0.7;
      const glow = ctx.createRadialGradient(moonPos.x, moonPos.y, 0, moonPos.x, moonPos.y, moonSize * 4);
      glow.addColorStop(0, 'rgba(200, 210, 230, 0.3)');
      glow.addColorStop(1, 'rgba(200, 210, 230, 0)');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(moonPos.x, moonPos.y, moonSize * 4, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#d4d8e0';
      ctx.beginPath();
      ctx.arc(moonPos.x, moonPos.y, moonSize, 0, Math.PI * 2);
      ctx.fill();

      if (this.showLabels) {
        ctx.fillStyle = '#d4d8e0';
        ctx.font = `bold ${Math.max(10, 11 * Math.sqrt(this.zoom) * 0.5)}px Inter`;
        ctx.textAlign = 'left';
        ctx.fillText(`Moon (${moon.phase})`, moonPos.x + moonSize + 5, moonPos.y + 3);
      }
    }

    // Telescope crosshair
    if (this.telescopeRA !== null && this.telescopeDec !== null) {
      const tp = this.raDecToScreen(this.telescopeRA, this.telescopeDec);
      const cr = 30;
      ctx.strokeStyle = this.isSlewing ? 'rgba(255, 50, 50, 0.8)' : 'rgba(50, 255, 100, 0.7)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);

      // Outer circle
      ctx.beginPath();
      ctx.arc(tp.x, tp.y, cr, 0, Math.PI * 2);
      ctx.stroke();

      // Crosshair lines
      ctx.beginPath();
      ctx.moveTo(tp.x - cr - 10, tp.y); ctx.lineTo(tp.x - 8, tp.y);
      ctx.moveTo(tp.x + 8, tp.y); ctx.lineTo(tp.x + cr + 10, tp.y);
      ctx.moveTo(tp.x, tp.y - cr - 10); ctx.lineTo(tp.x, tp.y - 8);
      ctx.moveTo(tp.x, tp.y + 8); ctx.lineTo(tp.x, tp.y + cr + 10);
      ctx.stroke();
      ctx.setLineDash([]);

      // Center dot
      ctx.fillStyle = this.isSlewing ? 'rgba(255, 50, 50, 0.8)' : 'rgba(50, 255, 100, 0.7)';
      ctx.beginPath();
      ctx.arc(tp.x, tp.y, 2, 0, Math.PI * 2);
      ctx.fill();
    }

    // Highlight hovered/selected
    const highlight = this.hoveredObject || this.selectedObject;
    if (highlight && highlight.ra) {
      const hp = this.raDecToScreen(highlight.ra, highlight.dec);
      ctx.strokeStyle = 'rgba(74, 158, 255, 0.6)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(hp.x, hp.y, 14, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  animate() {
    this.draw();
    requestAnimationFrame(() => this.animate());
  }
}

// ---- Main Application ----
class App {
  constructor() {
    this.engine = new CelestialEngine(33.4484, -112.074);
    this.selectedObject = null;
    this.selectedType = null;

    this.initCanvas();
    this.initSidebar();
    this.initSearch();
    this.initTopbar();
    this.initLocationModal();
    this.startClock();
    this.tryGeolocation();
  }

  initCanvas() {
    const canvas = document.getElementById('star-map-canvas');
    this.starMap = new StarMap(canvas, this.engine);

    // Map control buttons
    document.getElementById('btn-constellations').addEventListener('click', (e) => {
      this.starMap.showConstellations = !this.starMap.showConstellations;
      e.target.classList.toggle('active', this.starMap.showConstellations);
    });
    document.getElementById('btn-labels').addEventListener('click', (e) => {
      this.starMap.showLabels = !this.starMap.showLabels;
      e.target.classList.toggle('active', this.starMap.showLabels);
    });
    document.getElementById('btn-grid').addEventListener('click', (e) => {
      this.starMap.showGrid = !this.starMap.showGrid;
      e.target.classList.toggle('active', this.starMap.showGrid);
    });
    document.getElementById('btn-messier').addEventListener('click', (e) => {
      this.starMap.showMessier = !this.starMap.showMessier;
      e.target.classList.toggle('active', this.starMap.showMessier);
    });

    document.getElementById('btn-zoom-in').addEventListener('click', () => {
      this.starMap.zoom = Math.min(8, this.starMap.zoom * 1.3);
    });
    document.getElementById('btn-zoom-out').addEventListener('click', () => {
      this.starMap.zoom = Math.max(0.3, this.starMap.zoom / 1.3);
    });
  }

  initSidebar() {
    // Tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tabGroup = btn.closest('.sidebar-section');
        tabGroup.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        tabGroup.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
      });
    });

    this.populateStarList();
    this.populatePlanetList();
    this.populateConstellationList();
    this.populateMessierList();
    this.updateSkyStatus();
  }

  populateStarList() {
    const list = document.getElementById('star-list');
    const visible = this.engine.getVisibleStars(10);
    const brightest = visible.slice(0, 25);
    list.innerHTML = '';

    if (brightest.length === 0) {
      list.innerHTML = '<li style="padding:10px;color:var(--text-muted);font-size:0.82rem;">No stars currently visible.</li>';
      return;
    }

    for (const star of brightest) {
      const li = document.createElement('li');
      li.className = 'object-item';
      li.innerHTML = `
        <div class="object-dot" style="background:${this.starMap.getStarColor(star.type)};box-shadow:0 0 4px ${this.starMap.getStarColor(star.type)}"></div>
        <div class="object-info">
          <div class="object-name">${star.name}</div>
          <div class="object-meta">${star.constellation} · ${star.altitude?.toFixed(0) || '?'}° alt</div>
        </div>
        <div class="object-mag">${star.magnitude > 0 ? '+' : ''}${star.magnitude}</div>
      `;
      li.addEventListener('click', () => this.selectObject({ ...star, objType: 'star' }));
      list.appendChild(li);
    }
  }

  populatePlanetList() {
    const list = document.getElementById('planet-list');
    const positions = this.engine.getPlanetPositions();
    list.innerHTML = '';

    for (const planet of PLANETS) {
      const pos = positions[planet.name];
      const li = document.createElement('li');
      li.className = 'object-item';
      const isVis = pos?.visible;
      li.innerHTML = `
        <div class="object-dot" style="background:${planet.color};box-shadow:0 0 4px ${planet.color}"></div>
        <div class="object-info">
          <div class="object-name">${planet.name}</div>
          <div class="object-meta">${planet.type} · ${isVis ? pos.altitude.toFixed(0) + '° alt' : 'Below horizon'}</div>
        </div>
        <div class="object-mag" style="color:${isVis ? 'var(--accent-green)' : 'var(--text-muted)'}">${isVis ? '✓' : '–'}</div>
      `;
      li.addEventListener('click', () => this.selectObject({ ...planet, ra: pos?.ra, dec: pos?.dec, objType: 'planet', altitude: pos?.altitude }));
      list.appendChild(li);
    }
  }

  populateConstellationList() {
    const container = document.getElementById('constellation-list');
    container.innerHTML = '';
    const constellations = [...new Set(STARS.map(s => s.constellation).filter(c => c && c !== 'Solar System' && c !== 'Unknown'))].sort();

    for (const name of constellations) {
      const chip = document.createElement('div');
      chip.className = 'constellation-chip';
      chip.textContent = name;
      chip.addEventListener('click', () => this.selectObject({ name, objType: 'constellation' }));
      container.appendChild(chip);
    }
  }

  populateMessierList() {
    const list = document.getElementById('messier-list');
    list.innerHTML = '';

    for (const m of MESSIER_OBJECTS) {
      const { altitude } = this.engine.raDecToAltAz(m.ra, m.dec);
      const isVis = altitude > 0;
      const li = document.createElement('li');
      li.className = 'object-item';
      li.innerHTML = `
        <div class="object-dot" style="background:var(--accent-purple);box-shadow:0 0 4px var(--accent-purple)"></div>
        <div class="object-info">
          <div class="object-name">${m.name}</div>
          <div class="object-meta">${m.type} · ${m.constellation}</div>
        </div>
        <div class="object-mag">${m.mag}</div>
      `;
      li.addEventListener('click', () => this.selectObject({ ...m, objType: 'messier' }));
      list.appendChild(li);
    }
  }

  updateSkyStatus() {
    const dot = document.getElementById('sky-status-dot');
    const text = document.getElementById('sky-status-text');
    const isNight = this.engine.isNighttime();
    dot.className = 'sky-status-dot' + (isNight ? '' : ' daytime');
    text.textContent = isNight ? '🌃 Nighttime – Good for stargazing!' : '☀️ Daytime – Stars not visible';
  }

  initSearch() {
    const input = document.getElementById('search-input');
    const results = document.getElementById('search-results');

    input.addEventListener('input', () => {
      const q = input.value.trim().toLowerCase();
      if (q.length < 2) { results.classList.remove('active'); return; }

      const matches = [];
      for (const s of STARS) {
        if (s.name.toLowerCase().includes(q)) matches.push({ ...s, objType: 'star', icon: '⭐' });
      }
      for (const p of PLANETS) {
        if (p.name.toLowerCase().includes(q)) matches.push({ ...p, objType: 'planet', icon: '🪐' });
      }
      for (const m of MESSIER_OBJECTS) {
        if (m.name.toLowerCase().includes(q)) matches.push({ ...m, objType: 'messier', icon: '🌌' });
      }
      for (const [name] of Object.entries(CONSTELLATION_INFO)) {
        if (name.toLowerCase().includes(q)) matches.push({ name, objType: 'constellation', icon: '✨' });
      }

      if (matches.length === 0) { results.classList.remove('active'); return; }

      results.innerHTML = '';
      for (const m of matches.slice(0, 10)) {
        const div = document.createElement('div');
        div.className = 'search-result-item';
        div.innerHTML = `
          <div class="search-result-icon">${m.icon}</div>
          <div>
            <div class="search-result-name">${m.name}</div>
            <div class="search-result-type">${m.objType} ${m.constellation ? '· ' + m.constellation : ''}</div>
          </div>
        `;
        div.addEventListener('click', () => {
          this.selectObject(m);
          input.value = '';
          results.classList.remove('active');
        });
        results.appendChild(div);
      }
      results.classList.add('active');
    });

    document.addEventListener('click', (e) => {
      if (!e.target.closest('.search-container')) results.classList.remove('active');
    });
  }

  initTopbar() {
    document.getElementById('location-display').addEventListener('click', () => {
      document.getElementById('location-modal').classList.add('active');
    });
  }

  initLocationModal() {
    const modal = document.getElementById('location-modal');
    document.getElementById('location-cancel').addEventListener('click', () => modal.classList.remove('active'));
    document.getElementById('location-save').addEventListener('click', () => {
      const lat = parseFloat(document.getElementById('input-lat').value);
      const lon = parseFloat(document.getElementById('input-lon').value);
      const name = document.getElementById('input-location-name').value || undefined;
      if (!isNaN(lat) && !isNaN(lon)) {
        this.engine.setLocation(lat, lon, name);
        this.refreshAll();
        document.getElementById('loc-name').textContent = this.engine.locationName;
      }
      modal.classList.remove('active');
    });
    document.getElementById('location-detect').addEventListener('click', () => {
      this.tryGeolocation();
      modal.classList.remove('active');
    });
  }

  tryGeolocation() {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          this.engine.setLocation(pos.coords.latitude, pos.coords.longitude, 'Your Location');
          document.getElementById('loc-name').textContent = this.engine.locationName;
          this.refreshAll();
        },
        () => { /* keep default Phoenix */ }
      );
    }
  }

  refreshAll() {
    this.populateStarList();
    this.populatePlanetList();
    this.populateMessierList();
    this.updateSkyStatus();
  }

  startClock() {
    const update = () => {
      const now = new Date();
      document.getElementById('time-display').textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    };
    update();
    setInterval(update, 1000);
  }

  selectObject(obj) {
    this.selectedObject = obj;
    this.selectedType = obj.objType;

    const card = document.getElementById('detail-card');
    const empty = document.getElementById('detail-empty');
    card.classList.add('active');
    empty.style.display = 'none';

    // Pan map to object
    if (obj.ra !== undefined && obj.ra !== null && obj.dec !== undefined && obj.dec !== null) {
      this.starMap.gotoRADec(obj.ra, obj.dec);
      this.starMap.selectedObject = obj;
    }

    this.renderDetailCard(obj);
  }

  renderDetailCard(obj) {
    const type = obj.objType;
    const header = document.getElementById('detail-header');
    const body = document.getElementById('detail-body');

    if (type === 'star') {
      this.renderStarDetail(obj, header, body);
    } else if (type === 'planet') {
      this.renderPlanetDetail(obj, header, body);
    } else if (type === 'messier') {
      this.renderMessierDetail(obj, header, body);
    } else if (type === 'constellation') {
      this.renderConstellationDetail(obj, header, body);
    }
  }

  renderStarDetail(star, header, body) {
    const typeInfo = SPECTRAL_TYPE_INFO[star.type?.[0]?.toUpperCase()] || {};
    const color = typeInfo.color || '#ccc';
    const constInfo = CONSTELLATION_INFO[star.constellation] || {};

    header.innerHTML = `
      <div class="detail-type-badge badge-star">⭐ Star</div>
      <div class="detail-name">${star.name}</div>
      <div class="detail-subtitle">${star.constellation} · ${typeInfo.label || star.type}-type</div>
      <div class="spectral-bar" style="background:linear-gradient(90deg, ${color}, ${color}88)"></div>
    `;

    let gotoBtnHTML = '';
    if (star.ra !== null && star.dec !== null) {
      gotoBtnHTML = `<button class="goto-btn" onclick="app.gotoTarget(${star.ra}, ${star.dec})">🎯 Point Telescope Here</button>`;
    }

    body.innerHTML = `
      <div class="detail-section">
        <div class="detail-section-title"><span>📊</span> Properties</div>
        <div class="stats-grid">
          <div class="stat-item"><div class="stat-label">Magnitude</div><div class="stat-value">${star.magnitude}</div></div>
          <div class="stat-item"><div class="stat-label">Temperature</div><div class="stat-value">${star.temperature?.toLocaleString()} K</div></div>
          <div class="stat-item"><div class="stat-label">Distance</div><div class="stat-value">${star.distance} ly</div></div>
          <div class="stat-item"><div class="stat-label">Radius</div><div class="stat-value">${star.radius}× Sun</div></div>
          ${star.ra ? `<div class="stat-item"><div class="stat-label">RA</div><div class="stat-value">${star.ra.toFixed(2)}°</div></div>` : ''}
          ${star.dec !== null ? `<div class="stat-item"><div class="stat-label">Dec</div><div class="stat-value">${star.dec > 0 ? '+' : ''}${star.dec.toFixed(2)}°</div></div>` : ''}
        </div>
        ${gotoBtnHTML}
      </div>
      <div class="detail-section">
        <div class="detail-section-title"><span>🔬</span> Spectral Type</div>
        <div class="prose-text">${typeInfo.description || 'Unknown spectral type.'}</div>
        ${typeInfo.tempRange ? `<div class="prose-text" style="margin-top:6px;color:var(--text-muted)">Temperature range: ${typeInfo.tempRange}</div>` : ''}
      </div>
      ${constInfo.mythology ? `
      <div class="detail-section">
        <div class="detail-section-title"><span>🌌</span> Constellation: ${star.constellation}</div>
        <div class="prose-text" style="margin-bottom:8px"><strong>${constInfo.description}</strong></div>
        <div class="prose-text">${constInfo.mythology}</div>
      </div>
      <div class="detail-section">
        <div class="detail-section-title"><span>⭐</span> Features</div>
        <div class="prose-text">${constInfo.features}</div>
        <div class="prose-text" style="margin-top:8px;color:var(--accent-cyan)">📅 Best season: ${constInfo.best_season}</div>
      </div>
      ` : ''}
    `;
  }

  renderPlanetDetail(planet, header, body) {
    header.innerHTML = `
      <div class="detail-type-badge badge-planet">🪐 Planet</div>
      <div class="detail-name">${planet.name}</div>
      <div class="detail-subtitle">${planet.type}</div>
    `;

    let gotoBtnHTML = '';
    if (planet.ra !== undefined && planet.ra !== null) {
      gotoBtnHTML = `<button class="goto-btn" onclick="app.gotoTarget(${planet.ra}, ${planet.dec})">🎯 Point Telescope Here</button>`;
    }

    body.innerHTML = `
      <div class="detail-section">
        <div class="detail-section-title"><span>📊</span> Properties</div>
        <div class="stats-grid">
          <div class="stat-item"><div class="stat-label">Distance from Sun</div><div class="stat-value">${planet.distance_million_km} M km</div></div>
          <div class="stat-item"><div class="stat-label">Diameter</div><div class="stat-value">${planet.diameter_km?.toLocaleString()} km</div></div>
          <div class="stat-item"><div class="stat-label">Mass</div><div class="stat-value">${planet.mass_earth_masses}× Earth</div></div>
          <div class="stat-item"><div class="stat-label">Orbital Period</div><div class="stat-value">${planet.orbital_period_days?.toLocaleString()} days</div></div>
          <div class="stat-item"><div class="stat-label">Day Length</div><div class="stat-value">${planet.rotation_period_hours} hrs</div></div>
          <div class="stat-item"><div class="stat-label">Known Moons</div><div class="stat-value">${planet.moons}</div></div>
        </div>
        ${gotoBtnHTML}
      </div>
      <div class="detail-section">
        <div class="detail-section-title"><span>📖</span> Mythology</div>
        <div class="prose-text">${planet.mythology || 'No mythology available.'}</div>
      </div>
      <div class="detail-section">
        <div class="detail-section-title"><span>🌟</span> Fun Facts</div>
        <div class="prose-text">${planet.fun_facts || 'No facts available.'}</div>
      </div>
    `;
  }

  renderMessierDetail(m, header, body) {
    const constInfo = CONSTELLATION_INFO[m.constellation] || {};

    header.innerHTML = `
      <div class="detail-type-badge badge-messier">🌌 ${m.type}</div>
      <div class="detail-name">${m.name}</div>
      <div class="detail-subtitle">${m.constellation}</div>
    `;

    let gotoBtnHTML = '';
    if (m.ra !== undefined) {
      gotoBtnHTML = `<button class="goto-btn" onclick="app.gotoTarget(${m.ra}, ${m.dec})">🎯 Point Telescope Here</button>`;
    }

    body.innerHTML = `
      <div class="detail-section">
        <div class="detail-section-title"><span>📊</span> Properties</div>
        <div class="stats-grid">
          <div class="stat-item"><div class="stat-label">Type</div><div class="stat-value">${m.type}</div></div>
          <div class="stat-item"><div class="stat-label">Magnitude</div><div class="stat-value">${m.mag}</div></div>
          <div class="stat-item"><div class="stat-label">Distance</div><div class="stat-value">${m.distance_ly?.toLocaleString()} ly</div></div>
          <div class="stat-item"><div class="stat-label">RA / Dec</div><div class="stat-value">${m.ra.toFixed(1)}° / ${m.dec > 0 ? '+' : ''}${m.dec.toFixed(1)}°</div></div>
        </div>
        ${gotoBtnHTML}
      </div>
      <div class="detail-section">
        <div class="detail-section-title"><span>🔭</span> Description</div>
        <div class="prose-text">${m.description}</div>
      </div>
      ${constInfo.mythology ? `
      <div class="detail-section">
        <div class="detail-section-title"><span>🌌</span> Constellation: ${m.constellation}</div>
        <div class="prose-text">${constInfo.mythology}</div>
      </div>
      ` : ''}
    `;
  }

  renderConstellationDetail(c, header, body) {
    const info = CONSTELLATION_INFO[c.name] || {};
    const starsInConst = STARS.filter(s => s.constellation === c.name && s.ra)
      .sort((a, b) => a.magnitude - b.magnitude);

    header.innerHTML = `
      <div class="detail-type-badge badge-constellation">✨ Constellation</div>
      <div class="detail-name">${c.name}</div>
      <div class="detail-subtitle">${info.description || ''}</div>
    `;

    const starListHTML = starsInConst.map(s => {
      const color = this.starMap.getStarColor(s.type);
      return `<li class="const-star-item" onclick="app.selectObject({...STARS.find(st=>st.name==='${s.name.replace(/'/g,"\\'")}'), objType:'star'})">
        <div class="const-star-dot" style="background:${color};box-shadow:0 0 4px ${color}"></div>
        ${s.name} <span style="color:var(--text-muted);margin-left:auto;font-family:var(--font-mono);font-size:0.72rem">${s.magnitude}</span>
      </li>`;
    }).join('');

    // Center map on brightest star in constellation
    let gotoBtnHTML = '';
    if (starsInConst.length > 0) {
      const brightest = starsInConst[0];
      gotoBtnHTML = `<button class="goto-btn" onclick="app.gotoTarget(${brightest.ra}, ${brightest.dec})">🎯 Point Telescope at ${brightest.name}</button>`;
    }

    body.innerHTML = `
      ${info.mythology ? `
      <div class="detail-section">
        <div class="detail-section-title"><span>📖</span> Mythology</div>
        <div class="prose-text">${info.mythology}</div>
      </div>` : ''}
      ${info.features ? `
      <div class="detail-section">
        <div class="detail-section-title"><span>⭐</span> Features</div>
        <div class="prose-text">${info.features}</div>
        ${info.best_season ? `<div class="prose-text" style="margin-top:8px;color:var(--accent-cyan)">📅 Best season: ${info.best_season}</div>` : ''}
      </div>` : ''}
      <div class="detail-section">
        <div class="detail-section-title"><span>🌟</span> Stars in ${c.name} (${starsInConst.length})</div>
        <ul class="const-star-list">${starListHTML || '<li style="color:var(--text-muted)">No cataloged stars.</li>'}</ul>
        ${gotoBtnHTML}
      </div>
    `;
  }

  gotoTarget(ra, dec) {
    this.starMap.gotoRADec(ra, dec);
  }

  updateHUD() {
    const readout = document.getElementById('hud-readout');
    if (this.starMap.telescopeRA !== null) {
      readout.classList.add('active');
      const status = this.starMap.isSlewing ? '<span class="slew-status">SLEWING</span>' : 'TRACKING';
      let nearest = 'DEEP SPACE';
      let minDist = Infinity;

      // Find nearest object
      for (const s of STARS) {
        if (!s.ra) continue;
        const d = this.engine.angularDistance(this.starMap.telescopeRA, this.starMap.telescopeDec, s.ra, s.dec);
        if (d < minDist) { minDist = d; nearest = s.name; }
      }

      readout.innerHTML = `
        POSITION: ${this.starMap.telescopeRA.toFixed(2)}° / ${this.starMap.telescopeDec > 0 ? '+' : ''}${this.starMap.telescopeDec.toFixed(2)}°<br>
        STATUS:   ${status}<br>
        NEAREST:  ${minDist < 2 ? nearest.toUpperCase() : 'DEEP SPACE'}
      `;
    }
  }
}

// ---- Initialize ----
let app;
document.addEventListener('DOMContentLoaded', () => {
  app = new App();
});
