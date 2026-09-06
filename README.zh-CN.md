# Vellum (Agent Bridge Edition)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)]()
[![.NET](https://img.shields.io/badge/.NET-8.0%20%7C%209.0-purple.svg)]()
[![Renderer](https://img.shields.io/badge/Renderer-WebGPU%20%2F%20Canvas2D-orange.svg)]()
[![CI](https://github.com/linnnn89/Vellum-Agent-Bridge/actions/workflows/pages.yml/badge.svg)](https://github.com/linnnn89/Vellum-Agent-Bridge/actions)

[English](README.md) | [简体中文](README.zh-CN.md)

本地优先（Local-first）的 WebGPU 矢量设计编辑器，集成面向 WPF/XAML 的三阶段语义化编译桥梁，将矢量设计稿编译为响应式、确定性的桌面 UI 代码。

> **Fork 仓库**：[linnnn89/Vellum-Agent-Bridge](https://github.com/linnnn89/Vellum-Agent-Bridge)  
> **上游项目**：[wieslawsoltes/Vellum](https://github.com/wieslawsoltes/Vellum)（原作者：Wiesław Šoltés）

---

## 概述

设计工具擅长图形表达与自由排版，而现代桌面 UI 框架（如 WPF、Avalonia）依赖自适应流式布局、比例伸缩（Star Sizing）与数据绑定。传统的“像素转代码”往往生成脆弱的绝对坐标，直接让大语言模型（LLM）修改代码又极易破坏既有布局。

**Vellum-Agent-Bridge** 采用标准的三阶段编译器管线解决上述问题：

```text
.vellum 原始设计稿 (矢量图形)
       │
       ▼  [vellum-wpf convert / validate]
Semantic UI Spec (自包含独立 IR)
       │
       ├─── (可选) Agent Refinement Patch [vellum-wpf refine-apply]
       │       ▲
       │       └── 安全 AI 语义增强（仅限语义白名单，布局完全冻结）
       ▼
WPF / XAML 规范代码 (确定性生成、Grid 比例伸缩、直接 .NET 构建)
```

1. **设计层**：在原生 WebGPU 编辑器 Vellum 中进行界面排版与视觉设计；
2. **中间表示层（IR）**：将图形几何结构规范化为声明式 `ui-spec.json`，遵循严格的 [`ui-spec.schema.json`](tools/vellum-wpf-bridge/schemas/ui-spec.schema.json)；
3. **安全 Agent 修正**：AI Agent 仅能通过原子化 JSON Patch 修改语义元数据（文本、命令名、提示、辅助功能标签），布局结构与样式被严格锁定禁止修改；
4. **代码生成层**：输出整洁、符合人类工程习惯的 XAML 代码，使用 `dotnet build` 直接编译运行。

---

## 核心特性

### 1. 本地优先 WebGPU 矢量编辑器
- **零运行时外部依赖**：纯标准 HTML、CSS 与现代 JavaScript（ES Modules）开发，无 npm 打包工具或前端框架开销；
- **双渲染后端**：高性能 WebGPU 批处理管线（单场景单 Draw Call 渲染），并在不支持 WebGPU 的设备上平滑回退至 Canvas 2D；
- **单文件便携版**：运行 `python3 build.py` 即可构建出约 260 KB 的独立单文件 `Vellum.html`，无需联网即可离线运行；
- **中英文实时双语切换**：通过软件“设置”面板或顶部快捷切换按钮，可在英文与简体中文之间即时切换；
- **完整的矢量排版能力**：画框（Frame）、自动布局（Auto Layout with gap/padding）、文字排版、Bézier 曲线、设计 Token、组件符号引用以及 80 步撤销/重做历史。

### 2. 语义化 UI 规范（Self-Contained IR）
- **框架中立**：抽象并封装组件树、主轴伸缩策略（`fixed` 与 `fill`）、对齐约束与色彩资源；
- **自包含（Self-contained）**：颜色 Token 与共享资源直接收录于 `UiSpec.resources`，完全摆脱对原始 `.vellum` 的隐式依赖，支持直接基于 IR 重新生成代码；
- **严格校验**：强制检查文档拓扑、有向无环图、数值边界与图层 ID 唯一性。

### 3. 安全 Agent 修正机制（Safe Refiner）
- **布局与样式不可变性**：防止模型幻觉破坏排版。禁止 Patch 修改 `id`、`type`、`layout.*`、`style.*`、`children` 等结构与外观属性；
- **语义白名单**：仅允许 Agent 调整 `name`、`props.text`、`props.command`、`props.tooltip`、`props.accessibleName`、`props.helpText` 及 `props.semanticRole`；
- **原子事务与审计日志**：基于 `baseSpecSha256` 进行版本一致性核对，全量校验通过方才落盘，并生成完整追踪报告 `refinement-report.json`。

### 4. 确定性 WPF/XAML 生成器
- **响应式布局转换**：
  - 主轴含 `fill` 的自动布局自动编译为带 `*` 轨道的 WPF `Grid`，间距由专用占位轨道（Spacer Track）精确表达；
  - 固定尺寸的主轴布局编译为 `StackPanel`，间距映射为后置外边距；
  - 自由画布容器回退至 `Canvas` 并保留物理设计尺寸；
- **规范的布局语义**：容器内边距（Padding）统一包装为 `<Border Padding="..." ...>`，杜绝错误转化为外边距；
- **无污染的控件输出**：输入框占位符（Placeholder）不作为 `TextBox.Text` 填入，仅为必要控件生成确定性且唯一的 `x:Name`。

---

## 快速上手

### 运行设计编辑器

#### 方式 A：模块化开发运行（推荐）
在仓库根目录下启动任意本地静态服务器：

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

在支持 WebGPU 的现代浏览器（Chrome、Edge、Safari 17+ 等）中访问 `http://localhost:8080/`。

#### 方式 B：单文件便携版
```sh
python3 build.py
```
构建后直接双击或在浏览器中打开生成的 `Vellum.html` 即可。

---

### 安装 Bridge CLI 工具

编译工具位于 `tools/vellum-wpf-bridge`，需要 **Python 3.10+** 环境：

```sh
cd tools/vellum-wpf-bridge
pip install -e .
```

安装完成后，可以在命令行直接使用 `vellum-wpf` 命令。

---

### CLI 核心命令指南

#### 1. 校验 `.vellum` 文件结构
验证图层 ID 唯一性、层级拓扑与几何数值合法性：

```sh
vellum-wpf validate samples/tabletop-chat.vellum
```

#### 2. 转换 `.vellum` 为 UI Spec 与 WPF/XAML
运行全流程编译管线：

```sh
vellum-wpf convert samples/tabletop-chat.vellum -o output
```

生成产物：
- `output/ui-spec.json`：标准化中间表示（IR）
- `output/MainWindow.xaml`：主窗口布局文件
- `output/Resources.xaml`：提取的共享色彩资源字典
- `output/App.xaml`：应用程序定义
- `output/conversion-report.json`：转换统计与诊断清单

#### 3. 从 `ui-spec.json` 独立生成 XAML
直接基于 IR 生成代码，无需重新读取 `.vellum`：

```sh
vellum-wpf generate output/ui-spec.json -o output-wpf
```

#### 4. 校验 Agent 修正补丁（Patch）
核验 Patch 是否符合 schema 以及语义修改白名单：

```sh
vellum-wpf refine-validate output/ui-spec.json path/to/patch.json
```

#### 5. 原子化应用 Agent 修正补丁
应用补丁并输出更新后的 IR 与审计日志：

```sh
vellum-wpf refine-apply output/ui-spec.json path/to/patch.json -o refined-output
```

---

### 编译与运行生成的 WPF Demo

仓库内置了标准 .NET 示例项目（位于 [`tools/vellum-wpf-bridge/samples/generated-wpf-demo/`](tools/vellum-wpf-bridge/samples/generated-wpf-demo/)）：

```sh
cd tools/vellum-wpf-bridge/samples/generated-wpf-demo
dotnet build GeneratedWpfDemo.csproj
dotnet run --project GeneratedWpfDemo.csproj
```

生成的工程在现代 .NET SDK 环境下可达到 **0 错误、0 警告** 编译通过。

---

## 质量保障与验证体系

### 布局契约伸缩测试（`260 | * | 260` Canary）
为确保生成的 Grid 严格具备响应式自适应能力，项目内置自动化三栏 Canary 验证。当容器宽度从 1280px 调整至 1600px 时，两侧边栏宽度保持不变，伸缩增量全部由中央星号轨道吸收：

$$\begin{aligned}
\text{宽度 } 1280\text{px} &\longrightarrow 260 \mid 760 \mid 260 \\
\text{宽度 } 1600\text{px} &\longrightarrow 260 \mid 1080 \mid 260 \\
\Delta &\longrightarrow 0 \mid +320 \mid 0
\end{aligned}$$

运行编译器全套自动化单测：
```sh
cd tools/vellum-wpf-bridge
python tests/run_tests.py
```

### 浏览器端冒烟集成测试
编辑器包含覆盖鼠标绘制、撤销重做、图层树调整、字体排版与组件传播的集成测试套件：

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
python3 scripts/ci.py --skip-browser   # 语法与构建基础检查
```

---

## 项目目录结构

```text
.
├── index.html                 # 编辑器宿主 HTML
├── styles.css                 # 编辑器全局样式与主题变量
├── src/                       # 编辑器前端 ES Modules 源码
│   ├── app.js                 # 核心控制器、交互状态机、属性检查器
│   ├── document.js            # 场景图数据模型、仿射变换、校验与历史
│   ├── renderer.js            # WGSL WebGPU 渲染管线与 Canvas 2D 回退
│   ├── i18n.js                # 中英文双语词典与响应式切换引擎
│   ├── icons.js               # 内置矢量图标库
│   └── svg.js                 # 矢量 SVG 导出引擎
├── tools/
│   └── vellum-wpf-bridge/     # Vellum 到 WPF 编译桥梁核心工具
│       ├── pyproject.toml     # 标准 Python 打包配置
│       ├── schemas/           # UI Spec 与 Agent Patch 的 JSON Schema
│       ├── src/               # 桥梁源码包
│       ├── samples/           # 标准样例 .vellum 与生成的 WPF 示范工程
│       └── tests/             # 编译器单测与 Canary 验证套件
├── docs/                      # 架构规范与内部约束文档
├── scripts/                   # CI 脚本与静态站点构建工具
└── build.py                   # 便携单文件 HTML 打包脚本
```

---

## 规范与进阶文档

- [架构设计与渲染管线说明](ARCHITECTURE.md)
- [内部架构硬约束与设计规范](docs/SPEC_CONSTRAINTS.md)
- [Semantic UI Spec JSON Schema](tools/vellum-wpf-bridge/schemas/ui-spec.schema.json)
- [Agent Patch JSON Schema](tools/vellum-wpf-bridge/schemas/ui-spec-patch.schema.json)

---

## 致谢与开源许可

- **上游原项目**：感谢 Wiesław Šoltés 开发的 [Vellum](https://github.com/wieslawsoltes/Vellum)；
- **许可证**：本项目采用 [MIT License](LICENSE) 授权开源。
