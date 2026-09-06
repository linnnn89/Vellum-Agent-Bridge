# Vellum → Semantic UI Spec → WPF/XAML Bridge

A lightweight, deterministic compiler and bridge tool that converts [Vellum](https://github.com/wieslawsoltes/Vellum) design files (`.vellum`) into intermediate **Semantic UI Spec** (`ui-spec.json`) and clean, idiomatic **WPF/XAML** (`MainWindow.xaml`, `Resources.xaml`, `App.xaml`).

---

## 1. What It Does

```text
Vellum Design (.vellum)
         ↓
VellumDocumentAdapter (normalizes nodes, parent-child tree, tokens)
         ↓
SemanticMapper (heuristics: autolayout, buttons, inputs, cards, columns)
         ↓
Semantic UI Spec (framework-neutral JSON)
         ↓
WpfGenerator (generates idiomatic Grid / StackPanel / Border markup)
         ↓
Runnable WPF Desktop App (.NET 10)
```

---

## 2. Why Semantic UI Spec?

Direct point-to-point translation (`Vellum → XAML`) tightly couples graphic primitives with a single UI framework's quirks and creates brittle spaghetti generators.

By decoupling into **Semantic UI Spec**:
1. **Framework Neutral**: The intermediate format can target Avalonia, React, Flutter, HTML/Tailwind, or WinUI without changing the parser.
2. **AI & Vibe Coding Friendly**: LLMs / AI agents can easily inspect, reason about, and edit the human-readable JSON spec (e.g. "change right sidebar into tabs" or "adjust column ratio") before emitting code.
3. **Intent Preservation**: Distinguishes structural intentions (buttons, inputs, cards, multi-column layouts) from raw canvas coordinates.

---

## 3. Architecture

```text
.vellum JSON
    │
    ▼
VellumDocumentAdapter
    │
    ▼
NormalizedDocument
    │
    ▼
SemanticMapper (Heuristic Layout & Semantic Extraction)
    │
    ▼
Semantic UI Spec (ui-spec.json)
    │
    ├────────► [Optional / Future AI Spec Refiner]
    │
    ▼
WpfGenerator (Color Deduplication & XAML Synthesis)
    │
    ├── Resources.xaml (Reusable SolidColorBrush resources)
    ├── MainWindow.xaml (Structured Window UI)
    ├── App.xaml (WPF Application wrapper)
    └── conversion-report.json (Audit log: converted, fallbacks, warnings)
```

---

## 4. Supported Mappings

| Category | Feature | Status | Target XAML Representation |
| :--- | :--- | :--- | :--- |
| **Containers** | Auto-Layout, no main-axis fill | **Supported** | `StackPanel` + trailing child `Margin` for gap |
| | Auto-Layout with main-axis `stretch` | **Supported** | `Grid` star tracks; gap becomes spacer columns/rows |
| | Freeform (no Auto-Layout) | **Partial** | `Canvas` + `Canvas.Left/Top` and a diagnostic |
| | Sizing vs anchoring | **Supported** | `widthMode`/`heightMode` (`fixed`/`fill`) kept separate from `constraintH`/`constraintV` |
| | Card containers (rounded rectangle + content) | **Supported** | `Border` with `CornerRadius`, `Background`, `Padding` |
| **Controls** | Button Heuristic (Frame/Rect + Action text) | **Supported** | `<Button Content="Send" Command="{Binding SendCommand}"/>` |
| | Input Heuristic (Rect/Frame + Placeholder) | **Supported** | `<TextBox Text="..." VerticalContentAlignment="Center"/>` |
| | Text layers | **Supported** | `<TextBlock Text="..." FontSize="..." FontWeight="..." Foreground="..."/>` |
| | Line / Divider | **Supported** | `<Separator Height="1" Background="..."/>` |
| **Appearance** | Solid fills / background colors | **Supported** | `Background="{StaticResource Brush.Color_XXXX}"` |
| | Repeated colors deduplication | **Supported** | Extracted into `Resources.xaml` as `<SolidColorBrush>` |
| | Stroke & border thickness | **Supported** | `BorderBrush="..." BorderThickness="1.0"` |
| | Corner radius | **Supported** | `CornerRadius="8.0"` on `Border` |
| | Source Metadata | **Supported** | `<!-- Vellum: {nodeId} / {nodeName} -->` comments |
| **Fallback** | Arbitrary Bézier paths / vector curves | **Partial / Fallback** | Fallback shape + logged to `conversion-report.json` |
| | Ellipse / circular shapes | **Partial / Fallback** | Fallback shape + logged to `conversion-report.json` |
| | Gradients / Complex masks / Booleans | **Unsupported** | Gracefully logged to report without crashing |

---

## 5. Usage & CLI

### Prerequisites
- Python 3.10+ (Standard library only, zero third-party dependencies required)
- (Optional for running WPF demo) .NET SDK 8.0, 9.0, or 10.0 on Windows

### Command Examples

Run from `tools/vellum-wpf-bridge`:

```bash
# 1. Full conversion (outputs ui-spec.json, MainWindow.xaml, Resources.xaml, App.xaml, conversion-report.json)
$env:PYTHONPATH="src"; python -m vellum_wpf_bridge convert samples/tabletop-chat.vellum -o output

# 2. Spec-only mode (generates only ui-spec.json and conversion-report.json)
$env:PYTHONPATH="src"; python -m vellum_wpf_bridge convert samples/tabletop-chat.vellum -o output --spec-only

# 3. Custom output directory and custom C# namespace
$env:PYTHONPATH="src"; python -m vellum_wpf_bridge convert samples/tabletop-chat.vellum -o ./my-ui --namespace MyCustomApp
```

### Running Automated Tests

```bash
python tools/vellum-wpf-bridge/tests/run_tests.py
```

### Building the Generated WPF Demo

```bash
cd tools/vellum-wpf-bridge/samples/generated-wpf-demo
dotnet build
```

---

## 6. Output Artifacts

- `ui-spec.json`: Machine & human readable declarative semantic UI tree.
- `MainWindow.xaml`: Clean, well-formatted WPF XAML window without raw canvas coordinates.
- `Resources.xaml`: Deduplicated design tokens & solid color brushes.
- `App.xaml`: Application entrypoint referencing `Resources.xaml`.
- `conversion-report.json`: Metrics detailing total nodes, conversion success, and any unhandled vector fallbacks.
