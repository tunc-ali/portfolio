// scene-core.js — gedeelde basis voor de 3D-scènes (topology.js, globe.js)
//
// - three.js komt lokaal uit vendor/ (zie vendor/README.md)
// - kleuren komen uit de CSS-variabelen in base.css → geen nieuwe kleuren
// - rendert alleen wanneer de scène in beeld is én de tab zichtbaar is
// - prefers-reduced-motion: geen animatielus, alleen tekenen bij interactie
// - lichte modus (smal scherm / touch / weinig cores): lagere pixel ratio

import * as THREE from '../vendor/three.bundle.min.js';
export { THREE };

export const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
export const lightMode =
  window.matchMedia('(max-width: 900px), (pointer: coarse)').matches ||
  (navigator.hardwareConcurrency || 8) <= 4;

/** Kleuren uit het bestaande palet (base.css). */
export function palette() {
  const css = getComputedStyle(document.documentElement);
  const get = name => new THREE.Color(css.getPropertyValue(name).trim());
  return {
    bg: get('--bg'), bg3: get('--bg3'),
    border: get('--border2'),
    accent: get('--accent'), accent2: get('--accent2'), accentDim: get('--accent-dim'),
    text: get('--text'), textDim: get('--text-dim'),
  };
}

/** Zachte gloed-textuur (radiale gradient) voor sprites. */
export function glowTexture(color) {
  const size = 64;
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  const rgb = `${Math.round(color.r * 255)},${Math.round(color.g * 255)},${Math.round(color.b * 255)}`;
  const grad = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grad.addColorStop(0, `rgba(${rgb},1)`);
  grad.addColorStop(0.25, `rgba(${rgb},0.55)`);
  grad.addColorStop(1, `rgba(${rgb},0)`);
  g.fillStyle = grad;
  g.fillRect(0, 0, size, size);
  return new THREE.CanvasTexture(c);
}

/**
 * Maakt renderer + camera + scène in `container` en beheert de render-lus.
 *   onFrame(dt, time)  → animatiestap (niet aangeroepen bij reduced motion)
 *   onRender()         → na elke getekende frame (bv. labels positioneren)
 * Geeft { scene, camera, renderer, canvas, invalidate, size } terug.
 */
export function createStage(container, { fov = 40, label = '', onFrame = () => {}, onRender = () => {} } = {}) {
  const renderer = new THREE.WebGLRenderer({
    antialias: !lightMode,
    alpha: true,
    powerPreference: lightMode ? 'low-power' : 'default',
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, lightMode ? 1.25 : 2));
  renderer.setClearColor(0x000000, 0);

  const canvas = renderer.domElement;
  canvas.tabIndex = 0;
  canvas.setAttribute('role', 'img');
  if (label) canvas.setAttribute('aria-label', label);
  container.appendChild(canvas);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(fov, 1, 0.1, 100);
  const size = { w: 1, h: 1 };

  let inView = false;
  let raf = 0;
  let dirty = true;
  let last = 0;

  function frame(now) {
    raf = 0;
    const dt = Math.min((now - last) / 1000 || 0, 0.05);
    last = now;
    if (!reducedMotion) onFrame(dt, now / 1000);
    renderer.render(scene, camera);
    onRender();
    dirty = false;
    schedule();
  }

  function schedule() {
    if (raf || !inView || document.hidden) return;
    if (!reducedMotion || dirty) raf = requestAnimationFrame(frame);
  }

  function invalidate() {
    dirty = true;
    schedule();
  }

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (!w || !h) return;
    size.w = w; size.h = h;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    invalidate();
  }

  new ResizeObserver(resize).observe(container);
  new IntersectionObserver(([entry]) => {
    inView = entry.isIntersecting;
    last = performance.now();
    schedule();
  }).observe(container);
  document.addEventListener('visibilitychange', () => { last = performance.now(); schedule(); });

  resize();
  return { scene, camera, renderer, canvas, invalidate, size, resize };
}

/** HTML-label dat een 3D-punt volgt (scherpe tekst, erft het lettertype van de site). */
export function createLabel(container, text) {
  const el = document.createElement('span');
  el.className = 'scene-label';
  el.setAttribute('aria-hidden', 'true');
  el.textContent = text;
  container.appendChild(el);
  return el;
}

const _v = new THREE.Vector3();
/** Zet `el` op de schermpositie van wereldpunt `pos` (+ offset in px). */
export function placeLabel(el, pos, stage, dx = 0, dy = 0) {
  _v.copy(pos).project(stage.camera);
  const visible = _v.z < 1;
  el.style.visibility = visible ? 'visible' : 'hidden';
  if (!visible) return;
  const x = (_v.x * 0.5 + 0.5) * stage.size.w + dx;
  const y = (-_v.y * 0.5 + 0.5) * stage.size.h + dy;
  el.style.transform = `translate(-50%, 0) translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
}
