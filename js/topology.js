// topology.js — interactieve 3D-netwerktopologie op de homepagina
//
// Structuur (posities, links) : json/topology.json   (taalonafhankelijk)
// Teksten (label, rol, tech)  : de <ul class="topo-list"> in de pagina,
//                               door build.py gevuld uit json/nl.json / en.json
// De lijst blijft de toegankelijke weergave: elke knop selecteert dezelfde node.

import {
  THREE, createStage, createLabel, placeLabel, glowTexture, palette,
  reducedMotion, lightMode,
} from './scene-core.js';

const DATA_URL = new URL('../json/topology.json', import.meta.url);
const WAN_ROOT = 'internet';              // "traffic trail" loopt van de node naar het internet

// Vorm per node-type (bewust eenvoudig: draadmodel in de accentkleur)
function geometryFor(type) {
  switch (type) {
    case 'cloud':    return new THREE.IcosahedronGeometry(0.46, 1);
    case 'firewall': return new THREE.BoxGeometry(1.0, 0.5, 0.3);
    case 'core':     return new THREE.OctahedronGeometry(0.55);
    case 'switch':   return new THREE.BoxGeometry(1.0, 0.2, 0.5);
    case 'ap':       return new THREE.CylinderGeometry(0.36, 0.36, 0.1, 16);
    case 'lab':      return new THREE.IcosahedronGeometry(0.44, 0);
    default:         return new THREE.BoxGeometry(0.42, 0.8, 0.42);   // server
  }
}

export async function init(section) {
  const stageEl = section.querySelector('.topo-stage');
  const panel = section.querySelector('.topo-panel');
  const panelBody = section.querySelector('.topo-panel-body');
  const items = new Map([...section.querySelectorAll('.topo-list li[data-node]')].map(li => [li.dataset.node, li]));

  const res = await fetch(DATA_URL);
  if (!res.ok) throw new Error(`topology.json: HTTP ${res.status}`);
  const data = await res.json();

  const pal = palette();
  const glowTex = glowTexture(pal.accent);

  let controls;
  const stage = createStage(stageEl, {
    fov: 40,
    label: stageEl.dataset.canvasLabel,
    onFrame: animate,
    onRender: updateLabels,
  });
  const { scene, camera, canvas } = stage;
  stageEl.querySelector('.scene-loading')?.remove();

  // ── Nodes ───────────────────────────────────────────────────
  const nodes = new Map();          // id → { def, group, pos, edges, glow, label, links: [] }
  const hitTargets = [];

  for (const def of data.nodes) {
    const group = new THREE.Group();
    group.position.fromArray(def.pos);

    const geo = geometryFor(def.type);
    // Dichte kern verbergt lijnen erachter; randen in accentkleur
    group.add(new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: pal.bg3 })));
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(geo),
      new THREE.LineBasicMaterial({ color: def.zone === 'lab' ? pal.accent2 : pal.accent }),
    );
    group.add(edges);

    const glow = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glowTex, transparent: true, opacity: 0.22,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    glow.scale.setScalar(2.2);
    group.add(glow);

    // Onzichtbaar, ruimer klikdoel (ook voor vingers)
    const hit = new THREE.Mesh(new THREE.SphereGeometry(0.75, 8, 8), new THREE.MeshBasicMaterial({ visible: false }));
    hit.userData.id = def.id;
    group.add(hit);
    hitTargets.push(hit);

    scene.add(group);
    const li = items.get(def.id);
    const text = li ? li.querySelector('.topo-item').textContent : def.id;
    nodes.set(def.id, { def, group, pos: group.position, edges, glow, label: createLabel(stageEl, text), links: [] });
  }

  // Geïsoleerd segment: gestreepte ring rond het lab
  const lab = [...nodes.values()].find(n => n.def.zone === 'lab');
  if (lab) {
    const pts = [];
    for (let i = 0; i <= 48; i++) {
      const a = (i / 48) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(a) * 1.15, 0, Math.sin(a) * 1.15));
    }
    const ring = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineDashedMaterial({ color: pal.accent2, dashSize: 0.14, gapSize: 0.1, transparent: true, opacity: 0.8 }),
    );
    ring.computeLineDistances();
    ring.rotation.x = Math.PI / 2.6;
    lab.group.add(ring);
  }

  // ── Links ───────────────────────────────────────────────────
  const links = data.links.map(([a, b]) => {
    const A = nodes.get(a), B = nodes.get(b);
    const isLab = A.def.zone === 'lab' || B.def.zone === 'lab';
    const mat = isLab
      ? new THREE.LineDashedMaterial({ color: pal.accent2, dashSize: 0.18, gapSize: 0.14, transparent: true, opacity: 0.55 })
      : new THREE.LineBasicMaterial({ color: pal.accent2, transparent: true, opacity: 0.55 });
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([A.pos, B.pos]), mat);
    if (isLab) line.computeLineDistances();
    scene.add(line);
    const link = { a, b, line, mat, zone: isLab ? 'lab' : 'corp' };
    A.links.push(link); B.links.push(link);
    return link;
  });

  // ── Pakketjes: lopen willekeurig over links van hun eigen zone ──
  // (lab-pakketjes komen dus nooit in het bedrijfsnetwerk en omgekeerd)
  const packetMat = new THREE.SpriteMaterial({
    map: glowTex, transparent: true, opacity: 0.95,
    blending: THREE.AdditiveBlending, depthWrite: false,
  });
  const packets = [];
  function spawnPacket(zone) {
    const pool = links.filter(l => l.zone === zone);
    const link = pool[Math.floor(Math.random() * pool.length)];
    const forward = Math.random() < 0.5;
    const sprite = new THREE.Sprite(packetMat);
    sprite.scale.setScalar(0.34);
    scene.add(sprite);
    packets.push({
      sprite, link, zone,
      from: forward ? link.a : link.b, to: forward ? link.b : link.a,
      t: Math.random(), speed: 0.35 + Math.random() * 0.35,
    });
  }
  if (!reducedMotion) {
    const corpCount = lightMode ? 8 : 18;
    for (let i = 0; i < corpCount; i++) spawnPacket('corp');
    for (let i = 0; i < 2; i++) spawnPacket('lab');
  }

  function stepPacket(p, dt) {
    const A = nodes.get(p.from).pos, B = nodes.get(p.to).pos;
    p.t += (p.speed * dt * 3) / Math.max(A.distanceTo(B), 0.5);
    if (p.t >= 1) {
      // Aangekomen: kies een volgende link in dezelfde zone (liefst niet terug)
      const here = nodes.get(p.to);
      let options = here.links.filter(l => l.zone === p.zone && l !== p.link);
      if (!options.length) options = here.links.filter(l => l.zone === p.zone);
      const next = options[Math.floor(Math.random() * options.length)];
      p.from = here.def.id;
      p.to = next.a === p.from ? next.b : next.a;
      p.link = next;
      p.t = 0;
      return;
    }
    p.sprite.position.lerpVectors(A, B, p.t);
  }

  // ── Selectie + "traffic trail" naar het internet ────────────
  const traceMat = new THREE.SpriteMaterial({
    map: glowTexture(pal.text), transparent: true, opacity: 1,
    blending: THREE.AdditiveBlending, depthWrite: false,
  });
  const tracers = [0, 1, 2].map(() => {
    const s = new THREE.Sprite(traceMat);
    s.scale.setScalar(0.5);
    s.visible = false;
    scene.add(s);
    return s;
  });
  let selected = null;
  let trail = [];                 // posities van de node tot het internet
  let trailLength = 0;

  function pathToRoot(id) {
    // Breedte-eerst zoeken over de links
    const prev = new Map([[id, null]]);
    const queue = [id];
    while (queue.length) {
      const cur = queue.shift();
      if (cur === WAN_ROOT) break;
      for (const l of nodes.get(cur).links) {
        const other = l.a === cur ? l.b : l.a;
        if (!prev.has(other)) { prev.set(other, { from: cur, link: l }); queue.push(other); }
      }
    }
    const path = [];
    let cur = WAN_ROOT;
    while (prev.get(cur)) { path.unshift(prev.get(cur).link); cur = prev.get(cur).from; }
    return prev.has(WAN_ROOT) ? path : [];
  }

  function select(id, { focusPanel = false } = {}) {
    selected = nodes.has(id) ? id : null;
    const path = selected ? pathToRoot(selected) : [];

    for (const l of links) {
      const on = path.includes(l);
      l.mat.color.copy(on ? pal.accent : pal.accent2);
      l.mat.opacity = selected ? (on ? 1 : 0.22) : 0.55;
    }
    for (const [nid, n] of nodes) {
      const on = nid === selected;
      n.group.scale.setScalar(on ? 1.25 : 1);
      n.glow.material.opacity = on ? 0.6 : 0.22;
      n.label.classList.toggle('is-active', on);
      const li = items.get(nid);
      if (li) li.querySelector('.topo-item').setAttribute('aria-pressed', String(on));
    }

    // Route voor de tracers: node → … → internet
    trail = [];
    if (selected && path.length) {
      let cur = selected;
      trail.push(nodes.get(cur).pos);
      for (const l of path) { cur = l.a === cur ? l.b : l.a; trail.push(nodes.get(cur).pos); }
    }
    trailLength = 0;
    for (let i = 1; i < trail.length; i++) trailLength += trail[i - 1].distanceTo(trail[i]);
    tracers.forEach(s => { s.visible = trail.length > 1 && !reducedMotion; });

    // Infopaneel vullen met de tekst uit de lijst (zelfde bron als de fallback)
    panelBody.replaceChildren();
    const li = selected && items.get(selected);
    if (li) {
      panelBody.append(...[...li.querySelector('.topo-detail').children].map(el => el.cloneNode(true)));
      panel.hidden = false;
      if (focusPanel) panel.querySelector('.topo-close').focus({ preventScroll: true });
    } else {
      panel.hidden = true;
    }

    if (selected) controls.autoRotate = false;
    if (reducedMotion) applyShift(wantedShift());
    stage.invalidate();
  }

  function stepTracers(time) {
    if (trail.length < 2) return;
    tracers.forEach((s, i) => {
      let d = ((time * 2.2 + i * (trailLength / tracers.length)) % trailLength);
      for (let k = 1; k < trail.length; k++) {
        const seg = trail[k - 1].distanceTo(trail[k]);
        if (d <= seg) { s.position.lerpVectors(trail[k - 1], trail[k], d / seg); break; }
        d -= seg;
      }
    });
  }

  // ── Camera + besturing ──────────────────────────────────────
  const target = new THREE.Vector3(0.4, 0.1, 0);
  const home = new THREE.Vector3();
  function fitCamera() {
    // Afstand zo kiezen dat de hele topologie past: hoogte bepaalt op breed
    // scherm, breedte op smal (staand) scherm
    const dist = Math.max(12.5, 15.5 / camera.aspect);
    home.set(0.4, 1.6, dist);
  }
  fitCamera();
  camera.position.copy(home);

  controls = new THREE.OrbitControls(camera, canvas);
  controls.target.copy(target);
  controls.enablePan = false;
  controls.enableDamping = !reducedMotion;
  controls.minDistance = 6;
  controls.maxDistance = 32;
  controls.minPolarAngle = Math.PI * 0.2;
  controls.maxPolarAngle = Math.PI * 0.8;
  controls.autoRotate = !reducedMotion;
  controls.autoRotateSpeed = 0.5;
  // Scrollwiel zoomt pas nadat er in het beeld geklikt is, zodat de pagina
  // gewoon blijft scrollen wanneer de muis toevallig boven de scène hangt.
  controls.enableZoom = false;
  // Verticaal vegen op touch blijft de pagina scrollen; horizontaal = draaien
  canvas.style.touchAction = 'pan-y';
  controls.addEventListener('change', stage.invalidate);
  let touched = false;
  controls.addEventListener('start', () => { controls.autoRotate = false; touched = true; });
  controls.update();

  canvas.addEventListener('pointerdown', () => { controls.enableZoom = true; });
  canvas.addEventListener('pointerleave', () => { controls.enableZoom = false; });
  canvas.addEventListener('blur', () => { controls.enableZoom = false; });

  function zoomBy(factor) {
    const offset = camera.position.clone().sub(controls.target);
    touched = true;
    const len = THREE.MathUtils.clamp(offset.length() * factor, controls.minDistance, controls.maxDistance);
    camera.position.copy(controls.target).add(offset.setLength(len));
    controls.update();
    stage.invalidate();
  }
  function rotateBy(angle) {
    const offset = camera.position.clone().sub(controls.target);
    offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), angle);
    camera.position.copy(controls.target).add(offset);
    controls.autoRotate = false;
    controls.update();
    stage.invalidate();
  }
  function resetView() {
    fitCamera();
    camera.position.copy(home);
    controls.target.copy(target);
    controls.update();
    select(null);
    touched = false;
    controls.autoRotate = !reducedMotion;
    stage.invalidate();
  }

  section.querySelectorAll('.topo-tool').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.zoom === 'in') zoomBy(0.82);
      else if (btn.dataset.zoom === 'out') zoomBy(1.22);
      else resetView();
    });
  });

  canvas.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') { rotateBy(-0.18); e.preventDefault(); }
    else if (e.key === 'ArrowRight') { rotateBy(0.18); e.preventDefault(); }
    else if (e.key === '+' || e.key === '=') zoomBy(0.82);
    else if (e.key === '-') zoomBy(1.22);
    else if (e.key === 'Escape') select(null);
  });

  // ── Klikken / hover (raycasting) ────────────────────────────
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  function pick(e) {
    const r = canvas.getBoundingClientRect();
    pointer.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(hitTargets, false)[0];
    return hit ? hit.object.userData.id : null;
  }
  let downAt = null;
  canvas.addEventListener('pointerdown', (e) => { downAt = { x: e.clientX, y: e.clientY }; });
  canvas.addEventListener('pointerup', (e) => {
    if (!downAt) return;
    const moved = Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y);
    downAt = null;
    if (moved > 6) return;                 // dat was slepen, geen klik
    const id = pick(e);
    select(id === selected ? null : id);
  });
  if (!lightMode) {
    canvas.addEventListener('pointermove', (e) => {
      if (e.buttons) return;
      canvas.style.cursor = pick(e) ? 'pointer' : '';
    });
  }

  // Lijst-knoppen (toetsenbord / schermlezer) selecteren dezelfde node
  for (const [id, li] of items) {
    li.querySelector('.topo-item').addEventListener('click', () => select(id === selected ? null : id));
  }
  // Paneel sluiten: toetsenbordfocus terug naar de knop van die node in de lijst
  function closePanel() {
    const back = selected && items.get(selected)?.querySelector('.topo-item');
    const hadFocus = panel.contains(document.activeElement);
    select(null);
    if (back && hadFocus) back.focus({ preventScroll: true });
  }
  panel.querySelector('.topo-close').addEventListener('click', closePanel);
  panel.addEventListener('keydown', (e) => { if (e.key === 'Escape') closePanel(); });

  // ── Lus ─────────────────────────────────────────────────────
  function animate(dt, time) {
    controls.update();
    for (const p of packets) stepPacket(p, dt);
    stepTracers(time);
    if (selected) nodes.get(selected).edges.rotation.y += dt * 0.6;
    const want = wantedShift();
    if (Math.abs(want - shift) > 0.5) applyShift(shift + (want - shift) * Math.min(1, dt * 8));
  }

  // Labels plaatsen; overlappende labels verbergen (geselecteerde node heeft voorrang)
  function updateLabels() {
    const placed = [];
    const order = [...nodes.values()].sort((a, b) => (b.def.id === selected) - (a.def.id === selected));
    for (const n of order) {
      placeLabel(n.label, n.pos, stage, 0, 26 * n.group.scale.x);
      if (n.label.style.visibility === 'hidden') continue;
      const r = n.label.getBoundingClientRect();
      const clash = placed.some(q => r.left < q.right + 4 && r.right > q.left - 4 && r.top < q.bottom + 2 && r.bottom > q.top - 2);
      if (clash) n.label.style.visibility = 'hidden';
      else placed.push(r);
    }
  }

  // Op breed scherm ligt het infopaneel rechts over het beeld: schuif de
  // projectie dan naar links zodat het paneel geen nodes bedekt.
  let shift = 0;
  function applyShift(px) {
    shift = px;
    if (Math.abs(px) < 0.5) camera.clearViewOffset();
    else camera.setViewOffset(stage.size.w, stage.size.h, px, 0, stage.size.w, stage.size.h);
    stage.invalidate();
  }
  function wantedShift() {
    const overlay = !panel.hidden && getComputedStyle(panel).position === 'absolute';
    return overlay ? panel.offsetWidth / 2 : 0;
  }

  // Bij formaatwijziging opnieuw inpassen, zolang de bezoeker het beeld nog niet zelf bewoog
  new ResizeObserver(() => {
    applyShift(wantedShift());
    if (touched) return;
    fitCamera();
    camera.position.copy(home);
    controls.update();
  }).observe(stageEl);

  stage.invalidate();
}
