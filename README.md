# Vellum (Agent Bridge Edition)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)]()
[![.NET](https://img.shields.io/badge/.NET-8.0%20%7C%209.0-purple.svg)]()
[![Renderer](https://img.shields.io/badge/Renderer-WebGPU%20%2F%20Canvas2D-orange.svg)]()
[![CI](https://github.com/linnnn89/Vellum-Agent-Bridge/actions/workflows/pages.yml/badge.svg)](https://github.com/linnnn89/Vellum-Agent-Bridge/actions)

[English](README.md) | [简体中文](README.zh-CN.md)

A local-first WebGPU vector design editor paired with a semantic compilation pipeline that converts design documents into responsive, deterministic WPF/XAML.

> **Fork Repository**: [linnnn89/Vellum-Agent-Bridge](https://github.com/linnnn89/Vellum-Agent-Bridge)  
> **Upstream Project**: [wieslawsoltes/Vellum](https://github.com/wieslawsoltes/Vellum) by Wiesław Šoltés.

---

## Overview

Design tools excel at visual expression, while UI frameworks require explicit layout flow, star sizing, and data binding. Direct "pixel-to-code" generators often produce brittle absolute coordinates, while raw LLMs frequently corrupt layout structures when asked to tweak code.

**Vellum-Agent-Bridge** bridges this gap using a three-stage compiler architecture:

```text
.vellum Document (Vector Design)
       │
       ▼  [vellum-wpf convert / validate]
Semantic UI Spec (Self-Contained IR)
       │
       ├─── (Optional) Agent Refinement Patch [vellum-wpf refine-apply]
       │       ▲
       │       └── Safe AI Modification (Semantic Whitelist Only)
       ▼
WPF / XAML Code (Deterministic, Star-Track Grid, Direct .NET Build)
```

1. **Design Layer**: Create or edit interfaces in Vellum, a zero-dependency WebGPU editor.
2. **Intermediate Representation (IR)**: Normalize geometry into a declarative `ui-spec.json` following [`schemas/ui-spec.schema.json`](tools/vellum-wpf-bridge/schemas/ui-spec.schema.json).
3. **Safe AI Refinement**: AI agents modify only semantic metadata (text, commands, tooltips, accessibility) via atomic JSON patches, while layout structure and styles remain strictly immutable.
4. **Code Generation**: Emit clean, human-readable WPF/XAML that builds immediately with `dotnet build`.

---

## Key Features

### 1. Local-First WebGPU Design Editor
- **Zero Runtime Dependencies**: Written in vanilla HTML, CSS, and modern JavaScript (ES modules). No bundlers, npm packages, or web frameworks required.
- **Dual-Backend Rendering**: Instanced WebGPU pipeline emitting a single draw call per scene, with automatic fallback to Canvas 2D.
- **Single-File Portable Edition**: Run `python3 build.py` to produce a completely self-contained `Vellum.html` (approx. 260 KB) that runs offline.
- **Bilingual Interface**: Seamless real-time switching between English and 简体中文 through both the Settings modal and top-bar toggle button.
- **Full Vector Editing**: Frames, auto-layout with gap/padding, typography, Bézier curves, design tokens, linked components, and 80 levels of undo/redo.

### 2. Semantic UI Spec (Self-Contained IR)
- **Framework-Agnostic**: Encapsulates component hierarchy, sizing modes (`fixed` vs. `fill`), alignment constraints, and color resources.
- **Self-Contained**: Color tokens and shared assets reside directly inside `UiSpec.resources`, enabling standalone generation without original `.vellum` sources.
- **Strict Schema & Source Validation**: Verifies document integrity, acyclic parent-child trees, finite numeric bounds, and unique layer IDs.

### 3. Safe Agent Refinement Pipeline
- **Immutable Layout & Style**: Prevents LLMs from breaking layouts. Structural fields (`id`, `type`, `layout.*`, `style.*`, `children`) cannot be modified by patches.
- **Semantic Whitelist**: Agents can safely refine `name`, `props.text`, `props.command`, `props.tooltip`, `props.accessibleName`, `props.helpText`, and `props.semanticRole`.
- **Atomic Application**: Validates `baseSpecSha256` and node existence before applying changes, generating a complete audit trail in `refinement-report.json`.

### 4. Deterministic WPF/XAML Generation
- **Responsive Layout Mapping**:
  - Auto-layout with main-axis fill compiles to WPF `Grid` with star tracks (`*`), with gaps modeled via dedicated spacer rows/columns.
  - Auto-layout with fixed sizing compiles to `StackPanel` with trailing item margins.
  - Freeform containers gracefully fall back to `Canvas` with physical design dimensions preserved.
- **Correct Layout Semantics**: Container padding wraps inner panels in `<Border Padding="..." ...>` rather than misapplying `Margin`.
- **Clean Bindings**: Placeholders remain out of `TextBox.Text` (stored in metadata/tooltip), and deterministic `x:Name` tags are emitted only for actionable or bound controls.

---

## Quick Start

### Running the Editor

#### Option A: Modular Source (Recommended for development)
Serve the repository root with any static file server:

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

Open `http://localhost:8080/` in a browser supporting WebGPU (Chrome, Edge, Firefox Nightly, or Safari 17+).

#### Option B: Standalone Portable File
```sh
python3 build.py
```
Open the generated `Vellum.html` directly in your browser.

---

### Installing the Bridge CLI

The bridge tool resides under `tools/vellum-wpf-bridge` and requires **Python 3.10+**:

```sh
cd tools/vellum-wpf-bridge
pip install -e .
```

Once installed, the `vellum-wpf` command is globally accessible in your environment.

---

### CLI Command Reference

#### 1. Validate a `.vellum` file
Check document structure, format version, unique layer IDs, and numeric bounds:

```sh
vellum-wpf validate samples/tabletop-chat.vellum
```

#### 2. Convert `.vellum` to Semantic UI Spec and WPF/XAML
Run the end-to-end compiler pipeline:

```sh
vellum-wpf convert samples/tabletop-chat.vellum -o output
```

Outputs:
- `output/ui-spec.json`: Standardized Semantic UI Spec IR.
- `output/MainWindow.xaml`: Main window XAML.
- `output/Resources.xaml`: Shared color brush dictionary.
- `output/App.xaml`: Application definition.
- `output/conversion-report.json`: Compilation statistics and diagnostics.

#### 3. Standalone Generation from `ui-spec.json`
Compile directly from IR without touching the source `.vellum`:

```sh
vellum-wpf generate output/ui-spec.json -o output-wpf
```

#### 4. Validate an Agent Patch
Check whether an agent modification complies with the schema and semantic whitelist:

```sh
vellum-wpf refine-validate output/ui-spec.json path/to/patch.json
```

#### 5. Apply an Agent Patch
Atomically apply approved modifications and produce an updated spec and audit report:

```sh
vellum-wpf refine-apply output/ui-spec.json path/to/patch.json -o refined-output
```

---

### Building the Generated WPF Demo

A complete .NET sample project is included at [`tools/vellum-wpf-bridge/samples/generated-wpf-demo/`](tools/vellum-wpf-bridge/samples/generated-wpf-demo/):

```sh
cd tools/vellum-wpf-bridge/samples/generated-wpf-demo
dotnet build GeneratedWpfDemo.csproj
dotnet run --project GeneratedWpfDemo.csproj
```

The sample compiles with **0 errors and 0 warnings** under modern .NET SDKs.

---

## Verification & Quality Assurance

### Layout Contract Canary (`260 | * | 260`)
To guarantee responsive behavior, the bridge enforces an automated resize canary test. A three-column layout must allocate expansion delta exclusively to the center star track:

$$\begin{aligned}
\text{Width } 1280\text{px} &\longrightarrow 260 \mid 760 \mid 260 \\
\text{Width } 1600\text{px} &\longrightarrow 260 \mid 1080 \mid 260 \\
\Delta &\longrightarrow 0 \mid +320 \mid 0
\end{aligned}$$

Run bridge automated tests:
```sh
cd tools/vellum-wpf-bridge
python tests/run_tests.py
```

### Browser Test Suite
The editor includes browser integration tests exercising drawing, auto-layout, typography, undo/redo, component propagation, and export:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
python3 scripts/ci.py --skip-browser   # Syntax and build validation
```

---

## Project Structure

```text
.
├── index.html                 # Editor HTML shell
├── styles.css                 # Editor design tokens & dark/light theme
├── src/                       # Editor frontend ES modules
│   ├── app.js                 # Controller, state machines, inspector & shortcuts
│   ├── document.js            # Scene graph model, affine matrices, parse & history
│   ├── renderer.js            # WGSL WebGPU pipeline, atlas allocator & Canvas fallback
│   ├── i18n.js                # Bilingual dictionary & reactive translation engine
│   ├── icons.js               # Editor UI vector icons
│   └── svg.js                 # Vector SVG export engine
├── tools/
│   └── vellum-wpf-bridge/     # Compiler from Vellum to Semantic UI Spec & WPF
│       ├── pyproject.toml     # Packaging configuration
│       ├── schemas/           # JSON Schemas for UI Spec & Agent Patch
│       ├── src/               # Bridge Python package
│       ├── samples/           # Canonical .vellum samples & generated WPF demo
│       └── tests/             # Compiler unit tests & layout canary suite
├── docs/                      # Architectural specifications & internal constraints
├── scripts/                   # CI scripts and site generation
└── build.py                   # Portable single-file HTML packager
```

---

## Specifications & Documentation

- [Architecture & Rendering Pipeline](ARCHITECTURE.md)
- [Internal Architectural Constraints & Rules](docs/SPEC_CONSTRAINTS.md)
- [Semantic UI Spec JSON Schema](tools/vellum-wpf-bridge/schemas/ui-spec.schema.json)
- [Agent Patch JSON Schema](tools/vellum-wpf-bridge/schemas/ui-spec-patch.schema.json)

---

## Credits & License

- **Original Author**: Wiesław Šoltés ([wieslawsoltes/Vellum](https://github.com/wieslawsoltes/Vellum)).
- **License**: Released under the [MIT License](LICENSE).
