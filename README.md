# Vellum (Agent Bridge Edition)

> **Fork Repository**: [linnnn89/Vellum-Agent-Bridge](https://github.com/linnnn89/Vellum-Agent-Bridge)  
> Experimental Vellum fork for Vibe Coding, semantic UI specs and Vellum-to-WPF workflows.  
> Upstream: [wieslawsoltes/Vellum](https://github.com/wieslawsoltes/Vellum)

**A little more possible.** A local-first design editor built with plain HTML, CSS, JavaScript, and a WebGPU-first renderer. Version **0.1.0**.

The interface follows the familiar design-editor arrangement: pages and layers on the left, a central canvas, a property inspector on the right, and a floating bottom toolbar. The starter file contains 171 editable layers: a desktop product dashboard, a mobile focus app, palette and typography boards, and reusable UI pieces. It is not a flattened screenshot.

## GitHub Pages and CI

**Editor:** https://linnnn89.github.io/Vellum-Agent-Bridge/  
**Portable download:** https://linnnn89.github.io/Vellum-Agent-Bridge/Vellum.html  
**Workflow:** [CI and GitHub Pages](https://github.com/linnnn89/Vellum-Agent-Bridge/actions/workflows/pages.yml)

Initial repository setup: **Settings → Pages → Build and deployment → Source → GitHub Actions**. This is required before the first deployment. No custom domain or long-lived deployment secret is needed. After enabling Pages, run the workflow manually or push to `main`.

Every pull request and push to `main` checks JavaScript/Python syntax, builds an allow-listed `_site/` artifact, and runs the browser integration suite against the built site at `/Vellum/?canvas`. This verifies project-relative asset loading rather than testing only the domain root. CI intentionally uses Canvas 2D on generic hosted runners; it does not claim to validate hardware WebGPU. Test reports and light/dark screenshots are uploaded as artifacts, and successful production runs deploy the tested site with GitHub's official Pages actions.

Pull requests never receive deployment permissions. The deployment job runs only for `main` in this repository, after the build passes, and uses the `github-pages` environment. Concurrent deployments are serialized. The published artifact includes the modular editor, generated portable edition, license, `.nojekyll`, and SHA-256 checksums; tests and repository metadata are not published.

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
python3 scripts/ci.py                  # build and browser checks
python3 scripts/ci.py --skip-browser   # syntax and build only
python3 -m http.server 8080 --directory _site --bind 127.0.0.1
```

The application itself still has no runtime package dependencies. Node.js is used only for CI syntax validation; Python builds the static artifact and drives optional browser tests.

## Vellum → Semantic UI Spec → WPF

This fork includes an experimental compiler at [`tools/vellum-wpf-bridge/`](tools/vellum-wpf-bridge/):

```text
.vellum  →  Semantic UI Spec  →  WPF/XAML
```

It keeps layout sizing (`fixed` / `fill`) separate from Vellum anchoring (`constraintH` / `constraintV`). Auto Layout with a main-axis fill becomes a Grid with star tracks; freeform frames fall back to Canvas.

```sh
cd tools/vellum-wpf-bridge
$env:PYTHONPATH="src"; python -m vellum_wpf_bridge convert samples/tabletop-chat.vellum -o output
python tests/run_tests.py
```

Design brief (with completion / deprecation status): [`初版设计.md`](初版设计.md). Tool usage: [`tools/vellum-wpf-bridge/README.md`](tools/vellum-wpf-bridge/README.md).

## Run

### Portable edition

Build with `python3 build.py`, then open `Vellum.html`. It contains the entire application, including its editable starter document, with no runtime downloads. For the most predictable WebGPU behavior, serve it from localhost or HTTPS rather than relying on browser-specific `file:` behavior.

### Modular source

From this directory:

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

Open `http://localhost:8080/`. There is no npm install, frontend framework, bundler, WebAssembly module, CDN, analytics service, or backend dependency.

The lower-left renderer badge reports the actual active backend. WebGPU needs a compatible browser/device and a secure context. Missing adapters, initialization failures, device loss, and raster-atlas exhaustion trigger the Canvas 2D fallback. Append `?canvas` to force that fallback for comparison.

## Editing that is implemented

| Area | Implementation |
| --- | --- |
| Workspace | Light/dark themes, pages, searchable layer tree, collapsible groups, hide/lock controls, command palette, shortcuts, grid, rulers, zoom and pan. |
| Geometry | Rectangles, ellipses, frames, lines, editable polygon/Bézier paths, rotation, on-canvas resize handles, multi-selection, marquee selection, nudging, alignment, distribution, grouping, layer order and hierarchy changes. |
| Typography | Editable multiline Unicode text, wrapping, font family/size/weight, italic, underline, line-through in the model, line height, letter spacing, alignment, case conversion, explicit LTR/RTL direction, and user-imported font files. |
| Appearance | Solid and linear-gradient fills, strokes, opacity, rounded corners, basic drop shadows and nested rounded-frame clipping. |
| Layout | Horizontal/vertical auto layout with gap, padding and cross-axis alignment; left/right/center/stretch/scale and top/bottom constraints on frame children. |
| Components | Main components, linked instances, propagation of existing-node properties and per-property overrides. Assets also include editable button/card/badge insertions. |
| Design tokens | Document-local color and typography tokens. Color-token editing remaps exact matching colors across all pages. JSON token export. |
| Files | Debounced local saving through IndexedDB with localStorage fallback, portable `.vellum` JSON, image placement, PNG export and editable SVG export. |
| Preview | Frame presentation, next/previous navigation and click-to-navigate prototype links. |
| History | 80 document-level undo/redo entries, drag transaction boundaries and reversible document replacement. Image/font strings are shared by reference between history entries, rather than copied into each geometry snapshot. |

### Useful keys

`V` move, `F` frame, `R` rectangle, `O` ellipse, `L` line, `P` pen, `T` text, `H` hand. Hold Space to pan; Ctrl/Cmd + scroll zooms around the pointer. Shift+1 fits the page, Shift+2 fits the selection, and Shift+0 sets 100%. Ctrl/Cmd+K opens the command palette.

Double-click text to edit it. Double-click a path to edit anchors and handles. While drawing a path, click for an anchor, drag for Bézier handles, press Enter to finish, or click its first anchor to close it. Alt-drag a handle to break tangent symmetry.

Drag a layer row to reorder it. Shift-drop a row onto a frame/group to reparent it while retaining its world transform. Double-click a page or layer name to rename it. Double-click a component in Assets to insert an instance.

## Rendering architecture

The WebGPU backend packs painter-ordered primitives into a growable storage buffer and emits **one instanced scene draw call**. A 128-byte instance contains its affine transform, dimensions, fill/stroke parameters, raster coordinates and clip-chain pointer. Rounded rectangles and ellipses use analytical signed-distance coverage; text, general paths and placed images use a cached four-layer texture atlas.

Browser text shaping is intentionally retained: complete text layers are rasterized with Canvas 2D and uploaded only when their content/style or quantized resolution changes. This is a text-layer atlas, **not** a custom glyph shaper or MSDF font engine. General Bézier paths are also raster-cached; they are not tessellated on the GPU.

CPU-side world transforms use JavaScript numbers. GPU translation and clip offsets are rebased relative to the camera before conversion to float32. The renderer culls against world-space bounds, preserves painter order, supports transformed ancestor clip chains, caps raster resolution and draws only when invalidated. Selection chrome uses a separate Canvas 2D overlay. The Canvas fallback also caches text rasters.

See `ARCHITECTURE.md` for the data flow and extension points.

## Verification

`tests/results.json` records **36 passing browser integration checks** for the delivered implementation. They cover pointer-based drawing/move/resize, undo/redo, grouping, Unicode text editing, typography settings, component propagation/overrides, auto layout, frame constraints, Bézier creation, embedded image import, file round-tripping, malformed document rejection, undoing document replacement with image assets, PNG/SVG output, preview, themes, command execution, responsive chrome and a 5,000-shape scene.

**Environment boundary:** these checks ran in Chromium with an inline, opaque-origin document because normal navigation was blocked in the test environment. The exercised backend was **Canvas 2D**. Native WebGPU execution and actual browser-storage persistence were **not runtime-verified** there. The report and screenshots say which backend was used. The recorded timing is CPU scene preparation/submission time, not GPU execution time or an FPS benchmark.

Run the same suite against a normal secure localhost context to exercise your actual adapter:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
# In another terminal, from the project directory:
python3 -m http.server 8765 --bind 127.0.0.1
# Then:
python3 tests/smoke.py --url http://localhost:8765/
```

Fresh reports and screenshots are written to `test-results/`. Set `CHROMIUM_EXECUTABLE` to use a particular browser binary. `--inline` runs the fallback-only, network-independent variant used for the supplied report. Test tooling is optional and not needed to run the editor.

## Deliberate scope boundaries

This is a substantial working first version, **not complete Figma product parity**. It does not implement multiplayer/CRDT collaboration, comments, a plugin marketplace, `.fig` compatibility, vector Boolean operations, GPU path tessellation, arbitrary blend modes, masks beyond frame clipping, component variants or structural component-tree propagation. Auto layout does not include wrapping, hug/fill sizing or the full flex/grid constraint model.

Each text layer has one style. Rich-text spans, editable OpenType feature tags, variable-font axis controls, explicit hyphenation, full typographic paragraph composition and text-on-path are not implemented. Font shaping and script coverage depend on the browser and available/imported fonts. Inter is the preferred family name, with system fallbacks; **no font binaries are bundled**. Only load and embed fonts you have permission to distribute. SVG exports reference font families rather than embedding fonts or outlining glyphs.

SVG files can be placed as image assets; their internal paths are not imported into the editable scene graph. Exported SVG preserves the editor's native shapes and text. Shadows are an approximation and may differ slightly between analytical GPU coverage, Canvas and SVG filters. Image export has a 64-megapixel / 16,384-pixel-per-side guard. UI chrome adapts to smaller screens, but dense property editing remains desktop-oriented.

Local save is not a cloud backup. A browser profile, origin or site-data change can make saved data unavailable. Export `.vellum` files for durable copies. Vellum is an independent working name, not a trademark-availability claim or an affiliation with Figma.

## Source layout

```text
index.html             Editor shell
styles.css             Semantic design tokens and light/dark chrome
src/document.js        Scene model, affine transforms, history, validation, starter file
src/renderer.js        WGSL pipeline, raster atlas, text layout, image store, fallback, PNG
src/app.js             Editing controller, input state machines, inspector, saving, commands
src/svg.js             Vector/text SVG export
src/icons.js           Inline SVG editor icons
build.py               Standard-library-only portable HTML builder
Vellum.html             Generated single-file edition (not tracked)
scripts/build_site.py  Allow-listed GitHub Pages artifact builder
scripts/ci.py          Syntax, build, and project-subpath browser checks
.github/workflows/pages.yml  CI and GitHub Pages publishing
tests/smoke.py          Browser integration suite
```

After modifying source, regenerate the portable edition with `python3 build.py`.

## Reference APIs

The implementation uses the WebGPU specification and the browser Canvas APIs. References: `https://www.w3.org/TR/webgpu/`, `https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API`, `https://developer.mozilla.org/en-US/docs/Web/API/GPUCanvasContext/configure`, and `https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API`.
