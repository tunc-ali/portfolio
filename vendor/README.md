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

## sveltia-cms/

- **Bibliotheek:** Sveltia CMS **0.270.0** (npm `@sveltia/cms@0.270.0`), gebruikt door `admin/`
- **Licentie:** MIT — zie `sveltia-cms/LICENSE.txt`
- **Bron:** https://www.npmjs.com/package/@sveltia/cms/v/0.270.0 · https://github.com/sveltia/sveltia-cms
- **Inhoud:** `dist/sveltia-cms.js` en `dist/chunks/` uit het pakket, ongewijzigd, zonder `.map`-bestanden.
  `chunks/` moet erbij: Sveltia laadt die modules eerst naast `sveltia-cms.js` en anders van unpkg
  (dat de CSP van `/admin` blokkeert).
- **Controle van het pakket** (npm registry):
  - integrity `sha512-Stnnsl8m5LDjdir7yWY/ebKIrtcw6wRXUWF03MwXddFopZxQGktSUL02Zm/LPtXvgeS/vpAeSr66ZdVzek5ZEA==`
  - shasum (sha1) `eec3cf74cefa87e54d6f6442c8e6254bf7747d9c`
- **SHA-256 per bestand:** zie `sveltia-cms/SHA256SUMS`. Hoofdbestand:
  `sveltia-cms.js` = `7553aeb6af162a6f9e13ebef8b82918b397c42fa82edb82c3a143a562f602fbe`

Controleren op Windows (PowerShell, in `D:\mijnwebsite`):

```powershell
Get-FileHash vendor\sveltia-cms\sveltia-cms.js -Algorithm SHA256
```

Bijwerken naar een nieuwe versie (bv. `X.Y.Z`):

```
npm view @sveltia/cms@X.Y.Z dist.integrity          # noteren
npm pack @sveltia/cms@X.Y.Z                          # sveltia-cms-X.Y.Z.tgz
# integrity van het .tgz vergelijken met de registry, dan uitpakken en
# dist/sveltia-cms.js + dist/chunks/ (zonder *.map) + LICENSE.txt hierheen kopiëren,
# SHA256SUMS opnieuw maken, deze sectie bijwerken en eerst testen in een deploy preview.
```
