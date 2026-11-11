// globe.js — wereldbol met gesimuleerde verkeersbogen (homepagina)
//
// Data: json/globe.json (voorbeelddata: steden, bogen, landpunten).
// Eén heldere boog vertrekt vanaf de locatie van de bezoeker; die komt van
// js/ip-location.js (event "visitor-geo" / data-geo-lat|lon op <html>).
// Geen locatie bekend → die boog wordt gewoon niet getekend.

import {
  THREE, createStage, createLabel, placeLabel, glowTexture, palette,
  reducedMotion, lightMode,
} from './scene-core.js';

const DATA_URL = new URL('../json/globe.json', import.meta.url);
const R = 1;
const ARC_POINTS = 64;

/** Breedte/lengte → punt op een bol met straal r. */
function toVec(lat, lon, r = R) {
  const phi = THREE.MathUtils.degToRad(90 - lat);
  const theta = THREE.MathUtils.degToRad(lon + 180);
  return new THREE.Vector3(
    -r * Math.sin(phi) * Math.cos(theta),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.sin(theta),
  );
}

/** Punten van een boog over de bol (grootcirkel, in het midden hoger). */
function arcPoints(a, b) {
  const angle = a.angleTo(b);
  const lift = 0.05 + angle * 0.11;
  const pts = [];
  for (let i = 0; i < ARC_POINTS; i++) {
    const t = i / (ARC_POINTS - 1);
    // sferische interpolatie
    const s = Math.sin(angle) || 1;
    const p = a.clone().multiplyScalar(Math.sin((1 - t) * angle) / s)
      .add(b.clone().multiplyScalar(Math.sin(t * angle) / s));
    pts.push(p.normalize().multiplyScalar(R + Math.sin(Math.PI * t) * lift));
  }
  return pts;
}

function kmBetween(a, b) {
  return a.angleTo(b) * 6371;
}

export async function init(column) {
  const stageEl = column.querySelector('.globe-stage');

  const res = await fetch(DATA_URL);
  if (!res.ok) throw new Error(`globe.json: HTTP ${res.status}`);
  const data = await res.json();

  const pal = palette();
  const glowTex = glowTexture(pal.accent);

  let controls;
  const stage = createStage(stageEl, {
    fov: 38,
    label: stageEl.dataset.canvasLabel,
    onFrame: animate,
    onRender: updateLabel,
  });
  const { scene, camera, canvas } = stage;
  stageEl.querySelector('.scene-loading')?.remove();

  const globe = new THREE.Group();
  scene.add(globe);

  // Donkere bol (verbergt de achterkant) + zachte gloed erachter
  globe.add(new THREE.Mesh(
    new THREE.SphereGeometry(R * 0.995, lightMode ? 32 : 48, lightMode ? 24 : 32),
    new THREE.MeshBasicMaterial({ color: pal.bg }),
  ));
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({
    map: glowTex, transparent: true, opacity: 0.16, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
  halo.scale.setScalar(3.3);
  halo.renderOrder = -1;
  scene.add(halo);

  // Land als puntenwolk (zelfde beeldtaal als de kaart in de hero)
  const step = lightMode ? 2 : 1;           // lichte modus: de helft van de punten
  const positions = [];
  for (let i = 0; i < data.dots.length; i += 2 * step) {
    const v = toVec(data.dots[i] / 10, data.dots[i + 1] / 10, R * 1.002);
    positions.push(v.x, v.y, v.z);
  }
  const dotsGeo = new THREE.BufferGeometry();
  dotsGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  globe.add(new THREE.Points(dotsGeo, new THREE.PointsMaterial({
    color: pal.accent2, size: lightMode ? 0.026 : 0.017, sizeAttenuation: true,
  })));

  // Steden
  const cities = data.cities.map(c => ({ ...c, v: toVec(c.lat, c.lon) }));
  const cityMat = new THREE.SpriteMaterial({ map: glowTex, transparent: true, opacity: 0.9, depthWrite: false, blending: THREE.AdditiveBlending });

  // ── Bogen ───────────────────────────────────────────────────
  const arcs = [];
  function addArc(a, b, { bright = false } = {}) {
    const pts = arcPoints(a, b);
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    // vaste, zwakke baan + bewegend helder stuk ("trail")
    globe.add(new THREE.Line(geo, new THREE.LineBasicMaterial({
      color: bright ? pal.accent : pal.accent2, transparent: true, opacity: bright ? 0.5 : 0.28,
    })));
    const trail = new THREE.Line(geo.clone(), new THREE.LineBasicMaterial({ color: bright ? pal.text : pal.accent }));
    globe.add(trail);
    const arc = { trail, offset: Math.random() * 2, speed: 0.35 + Math.random() * 0.25, bright };
    if (reducedMotion) trail.visible = false;      // statisch: alleen de baan
    arcs.push(arc);
    return arc;
  }

  const arcList = lightMode ? data.arcs.slice(0, 5) : data.arcs;
  const used = new Set();
  for (const [i, j] of arcList) {
    addArc(cities[i].v, cities[j].v);
    used.add(i); used.add(j);
  }
  for (const i of used) {
    const s = new THREE.Sprite(cityMat);
    s.scale.setScalar(0.09);
    s.position.copy(cities[i].v).multiplyScalar(1.005);
    globe.add(s);
  }

  // ── Bezoeker ────────────────────────────────────────────────
  let visitor = null;               // { marker, pos (lokaal), label }
  function setVisitor(lat, lon) {
    if (visitor || !Number.isFinite(lat) || !Number.isFinite(lon)) return;
    const v = toVec(lat, lon);
    const marker = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glowTexture(pal.text), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }));
    marker.scale.setScalar(0.2);
    marker.position.copy(v).multiplyScalar(1.01);
    globe.add(marker);

    // Bestemming: eerste voorbeeldstad op minstens 1500 km (anders is de boog onzichtbaar kort)
    const dest = cities.find(c => kmBetween(v, c.v) >= 1500);
    if (dest) addArc(v, dest.v, { bright: true });

    visitor = { marker, pos: marker.position, label: createLabel(stageEl, stageEl.dataset.you || '') };
    visitor.label.classList.add('is-active');
    faceTowards(v);
    stage.invalidate();
  }

  // Draai de bol zo dat punt v naar de camera wijst
  function faceTowards(v) {
    globe.rotation.y = -Math.atan2(v.x, v.z);
    globe.rotation.x = THREE.MathUtils.clamp(Math.asin(v.y / v.length()) * 0.45, -0.4, 0.4);
  }
  faceTowards(toVec(48, 10));       // standaard: Europa vooraan

  // ── Camera + besturing (alleen draaien) ─────────────────────
  camera.position.set(0, 0, 3.8);
  controls = new THREE.OrbitControls(camera, canvas);
  controls.enablePan = false;
  controls.enableZoom = false;
  controls.enableDamping = !reducedMotion;
  controls.rotateSpeed = 0.6;
  controls.minPolarAngle = Math.PI * 0.25;
  controls.maxPolarAngle = Math.PI * 0.75;
  controls.autoRotate = !reducedMotion;
  controls.autoRotateSpeed = 0.6;
  canvas.style.touchAction = 'pan-y';
  controls.addEventListener('change', stage.invalidate);
  controls.update();

  canvas.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    globe.rotation.y += e.key === 'ArrowLeft' ? -0.2 : 0.2;
    e.preventDefault();
    stage.invalidate();
  });

  // Locatie: al bekend, of komt nog binnen
  const ds = document.documentElement.dataset;
  if (ds.geoLat !== undefined) setVisitor(Number(ds.geoLat), Number(ds.geoLon));
  document.addEventListener('visitor-geo', e => setVisitor(e.detail.lat, e.detail.lon));

  // ── Lus ─────────────────────────────────────────────────────
  const TRAIL = 14;                 // lengte van het heldere stuk, in punten
  function animate(dt, time) {
    controls.update();
    for (const arc of arcs) {
      // kop loopt van begin tot voorbij het einde, daarna korte pauze
      const cycle = ((time * arc.speed + arc.offset) % 1.6) / 1.0;
      const head = Math.floor(cycle * (ARC_POINTS + TRAIL));
      const start = Math.max(0, head - TRAIL);
      const end = Math.min(ARC_POINTS, head);
      arc.trail.geometry.setDrawRange(start, Math.max(0, end - start));
    }
    if (visitor) visitor.marker.scale.setScalar(0.2 + Math.sin(time * 3) * 0.05);
  }

  const world = new THREE.Vector3();
  const toCam = new THREE.Vector3();
  function updateLabel() {
    if (!visitor) return;
    visitor.marker.getWorldPosition(world);
    // Alleen tonen als het punt aan de voorkant van de bol ligt
    toCam.copy(camera.position).sub(world);
    if (world.dot(toCam) <= 0) { visitor.label.style.visibility = 'hidden'; return; }
    placeLabel(visitor.label, world, stage, 0, 8);
  }

  stage.invalidate();
}
