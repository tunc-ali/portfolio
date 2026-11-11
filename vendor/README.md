# vendor/

Externe bibliotheken staan hier lokaal (geen CDN), met vaste versie.

## three.bundle.min.js

- **Bibliotheek:** three.js **r187** (npm `three@0.187.0`) + `examples/jsm/controls/OrbitControls.js` uit hetzelfde pakket
- **Licentie:** MIT — zie `LICENSE-three.txt` (Copyright © 2010-2026 three.js authors)
- **Bron:** https://www.npmjs.com/package/three/v/0.187.0 · https://github.com/mrdoob/three.js
- **Inhoud:** één ES-module met alleen de klassen die de site gebruikt (tree-shaking),
  zodat er geen import-map of bare `'three'`-import nodig is. De broncode is niet aangepast.

Zo is het bestand gemaakt (opnieuw doen bij een versie-update):

```
npm install three@0.187.0 esbuild
npx esbuild vendor-entry.js --bundle --format=esm --minify --target=es2020 --outfile=vendor/three.bundle.min.js
```

`vendor-entry.js`:

```js
export {
  WebGLRenderer, Scene, PerspectiveCamera, Color, Vector2, Vector3, Group, Raycaster,
  BufferGeometry, BufferAttribute, Float32BufferAttribute,
  SphereGeometry, BoxGeometry, OctahedronGeometry, IcosahedronGeometry, CylinderGeometry,
  TorusGeometry, RingGeometry, EdgesGeometry,
  Mesh, Line, LineSegments, LineLoop, Points, Sprite,
  MeshBasicMaterial, LineBasicMaterial, LineDashedMaterial, PointsMaterial, SpriteMaterial,
  CanvasTexture, AdditiveBlending, DoubleSide, MathUtils,
} from 'three';
export { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
```

Gebruikt door `js/scene-core.js` (en daarmee `js/topology.js` en `js/globe.js`).

## fonts/

- **JetBrains Mono** (400, 500) en **Barlow Condensed** (600, 700, 800), woff2, subset *latin*
- **Licentie:** SIL Open Font License 1.1 — zie `fonts/LICENSE-jetbrains-mono.txt` en `fonts/LICENSE-barlow-condensed.txt`
- **Bron:** npm `@fontsource/jetbrains-mono@5.3.0` en `@fontsource/barlow-condensed@5.3.0` (map `files/`), ongewijzigd
- Ingeladen via `@font-face` bovenaan `css/base.css` met `font-display: swap`.
  Een extra gewicht nodig? Bestand hier toevoegen en een `@font-face`-regel bijschrijven.
