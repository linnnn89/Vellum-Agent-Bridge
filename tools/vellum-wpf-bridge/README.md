# Vellum → Semantic UI Spec → WPF/XAML Bridge

A lightweight, deterministic compiler and bridge pipeline that converts [Vellum](https://github.com/wieslawsoltes/Vellum) design files (`.vellum`) into intermediate **Semantic UI Spec** (`ui-spec.json`), supports verified **Safe Agent Refinement** (`ui-spec-patch.schema.json`), and synthesizes clean, idiomatic **WPF/XAML** (`MainWindow.xaml`, `Resources.xaml`, `App.xaml`).

---

## 1. 架构体系与数据流 (Architecture & Data Flow)

Vellum-Agent-Bridge 采用严格的三阶段编译与中介表示（IR）架构：

```text
.vellum Document (Vector Design JSON)
        │
        ▼  [1. Source Validation & Normalization]
   validator.py (Strict AST & Cycle Check)
   vellum_adapter.py (Hierarchical Scene Reconstruction)
        │
        ▼  [2. Semantic Mapping & Layout Synthesis]
   layout_contract.py (Sizing, Flow, Anchoring, Star/Spacer Tracks)
   semantic_mapper.py (Button, Input, Card, Container Promotion)
   resources.py (Token Extraction into UiSpec.resources)
        │
        ▼
   Semantic UI Spec (ui-spec.json, 100% Self-Contained IR)
        │
        ├─── [Optional: Safe Agent Refinement]
        │        ▲
        │        └── refiner.py (ui-spec-patch.schema.json, SHA-256 verification)
        │            • Allowed: name, props.text, props.command, props.tooltip, props.accessibleName
        │            • Disallowed: id, type, source, layout.*, style.*, children, resources
        │
        ▼  [3. Deterministic Code Synthesis]
   wpf_generator.py (Reads only UiSpec; Border Padding; Placeholder in Tooltip; Minimal x:Name)
        │
        ├── MainWindow.xaml (Responsive Grid & StackPanel layout)
        ├── Resources.xaml (Shared SolidColorBrush dictionary)
        ├── App.xaml (Application entrypoint)
        └── conversion-report.json (Audit log: counts, absorptions, diagnostics)
```

### 核心设计决策：为何需要自包含 IR？
1. **彻底解耦生成器与图形源数据**：`ui-spec.json` 生成后即为完整独立的抽象语法树，所有色彩 Token 直接打包在 `UiSpec.resources` 中。`WpfGenerator` **仅读取 `UiSpec`**，杜绝隐式调用 `.vellum`。
2. **AI 与 Agent 安全交互边界**：禁止大语言模型直接重写全部 UI 代码或完整 Spec。通过微型差量补丁（Patch）机制，在保证排版设计（Layout）绝对冻结的前提下，允许 Agent 补充命令绑定、语义文案与无障碍标签。
3. **消除绝对坐标脆弱性**：将设计稿的 Auto Layout 映射为 WPF 具备自适应能力的 `Grid`（带 `*` 伸缩列与 Spacer 间距轨道），在窗口缩放时自然延展。

---

## 2. 核心模块与实现逻辑 (Modules & Implementation Logic)

| 模块文件 | 职责范围 | 核心实现逻辑与不变量 |
| :--- | :--- | :--- |
| [`validator.py`](src/vellum_wpf_bridge/validator.py) | 源文件严格校验器 | • 验证 `format == 'vellum'`, `version == 1`；<br>• 检查节点 ID 格式与全局唯一性；<br>• 严格校验 `x, y, w, h, rotation, opacity` 为有限数值且尺寸非负（拒绝静默补默认值）；<br>• 校验 `parentId` 引用存在性与两遍扫描无环（Cycle Detection）拓扑检查。 |
| [`vellum_adapter.py`](src/vellum_wpf_bridge/vellum_adapter.py) | 数据模型适配层 | • 将平面列表按 `parentId` 重组为保序树形场景（保留绘制 Z 轴顺序）；<br>• 将原始节点属性严格绑定为强类型 `VellumNode` 与 `VellumDocument`。 |
| [`layout_contract.py`](src/vellum_wpf_bridge/layout_contract.py) | 布局契约状态机 | • Sizing（`fixed`/`fill`）、Anchoring（`constraintH`/`constraintV`）、Flow 正交解耦；<br>• 拒绝基于图层名猜测布局；仅 `stretch` 映射为 `fill`；<br>• 动态计算 Grid 列/行 `*` 轨道并插入 Spacer Track 表达 `gap`。 |
| [`semantic_mapper.py`](src/vellum_wpf_bridge/semantic_mapper.py) | 语义提升映射器 | • 启发式识别按钮（Frame/Rect + 单 Text 子节点，或包含明确 Action 名）；<br>• 启发式识别输入框（包含 placeholder/单行输入形态）；<br>• 容器提升（Card / Header / Footer）；<br>• 将文档中的设计色彩 Token 规范化并打包进 `UiSpec.resources`。 |
| [`resources.py`](src/vellum_wpf_bridge/resources.py) | 资源与色彩管理器 | • 收集并去重整个组件树的颜色；<br>• 支持直接从 `UiSpec.resources` 独立加载（Self-Contained）；<br>• 将 Token 名字转换为符合 WPF 规范的 `Brush.Brand.Primary` 键名。 |
| [`refiner.py`](src/vellum_wpf_bridge/refiner.py) | 安全 Agent 修正器 | • 校验 Patch 规范 `ui-spec-patch.schema.json` 与 `baseSpecSha256`；<br>• 实施严格的白名单与黑名单过滤，拒绝修改布局与外观；<br>• 原子性提交并生成 `refinement-report.json` 审计清单。 |
| [`wpf_generator.py`](src/vellum_wpf_bridge/wpf_generator.py) | WPF/XAML 合成引擎 | • 仅读取 `UiSpec`；<br>• 主轴含 `fill` 编译为 `Grid`，固定流编译为 `StackPanel`，自由画布回退为 `Canvas` 并保留物理设计尺寸；<br>• 内边距统一生成 `<Border Padding="..." ...>` 包装器；<br>• 输入框 Placeholder 放入 `Tag` / `ToolTip`，保持 `Text` 为空；<br>• 仅为 `Button`、`Input` 及显式绑定项生成确定性且唯一的 `x:Name`。 |
| [`cli.py`](src/vellum_wpf_bridge/cli.py) | 命令行接口入口 | • 提供 `validate`, `convert`, `generate`, `refine-validate`, `refine-apply` 五大子命令的完整调度与状态码返回。 |

---

## 3. 依赖关系规范 (Dependency Specification)

项目严格遵循极简与轻量化依赖原则，避免过度引入第三方轮子：

| 环境分类 | 依赖项 | 依赖说明与版本要求 |
| :--- | :--- | :--- |
| **运行时依赖 (Runtime)** | **无 (None / Zero External Dependencies)** | 编译桥梁核心完全基于 **Python 3.10+ 标准库**（`json`, `hashlib`, `math`, `re`, `argparse`, `dataclasses`, `pathlib`）。未引入 `pydantic`, `jsonschema`, `click` 等任何第三方包，启动速度极快。 |
| **安装与打包依赖** | `setuptools >= 61.0` | 仅在执行 `pip install -e .` 安装命令行入口时由 pip 使用。 |
| **测试期依赖 (Testing)** | `unittest` (Python 标准库)<br>`node.js >= 18` (可选) | • 单元测试与 Canary 验证基于 Python 原生 `unittest`；<br>• Node.js 仅用于执行可选的 `test_validate_vellum.py`（调用原版 `DocumentModel.parse()` 交叉比对，环境无 Node 时自动跳过）。 |
| **目标工程生成依赖** | `.NET SDK 8.0 / 9.0 / 10.0` (仅 Windows) | 仅在实际编译运行生成的 WPF 演示工程时需要（`dotnet build`）。编译器生成过程本身无需 .NET 环境。 |

---

## 4. 命令行指南 (CLI Usage)

在当前目录执行安装：

```bash
pip install -e .
```

安装后系统将全局注册 `vellum-wpf` 命令。

### 1. 校验源设计文件
```bash
vellum-wpf validate samples/tabletop-chat.vellum
```
> 输出：`PASS: tabletop-chat.vellum is a valid Vellum document.`

### 2. 全流程编译 (Vellum → UI Spec → WPF)
```bash
vellum-wpf convert samples/tabletop-chat.vellum -o output
```
> 生成产物：
> - `output/ui-spec.json`: 中间表示（IR）
> - `output/MainWindow.xaml`: 主窗口界面
> - `output/Resources.xaml`: 提取的共享色彩画刷
> - `output/App.xaml`: 应用程序清单
> - `output/conversion-report.json`: 转换度量与诊断日志

### 3. 从 `ui-spec.json` 独立重新生成 XAML
```bash
vellum-wpf generate output/ui-spec.json -o output-wpf
```
> 无需访问原始 `.vellum` 文件，直接基于 IR 合成同等质量的 XAML。

生成前校验 IR 的必填字段、字段类型、有限数值、非负尺寸、四项 Padding、整数 Grid 索引和树结构；错误包含字段路径，校验失败不创建输出目录或改写已有 XAML。宽高接受非负数字或 `Auto`；Grid 轨道另接受 `*`，不接受任意字符串或加权星号。可选字段仍使用既有默认值。直接调用生成器也会校验模型。

文本属性按字面量输出：以 `{` 开头的标题、文字、占位符和字体名会加 XAML 的 `{}` 转义前缀；合法 Command 绑定和生成器创建的资源引用保持有效。来源注释中的连续连字符会转义。

**颜色约定**：源 `.vellum` 的八位颜色为 `#RRGGBBAA`，进入 IR 前转换一次；`ui-spec.json` 的样式和资源八位颜色统一为 `#AARRGGBB`，资源管理器不得再次移动 alpha。例如源 `#12345680` 对应 IR/WPF `#80123456`。手写 IR 应遵守此约定，无法仅凭八位字符串自动判断作者使用了哪种顺序。三位、六位颜色继续支持。

### 4. 校验 Agent 修正补丁 (Safe Refiner)
```bash
vellum-wpf refine-validate output/ui-spec.json path/to/patch.json
```

### 5. 原子化应用 Agent 修正补丁
```bash
vellum-wpf refine-apply output/ui-spec.json path/to/patch.json -o output-refined
```
> 生成更新后的 `refined-ui-spec.json` 与审计报告 `refinement-report.json`。

审计报告 v2 的 `oldValue`、`newValue`、`reason` 仅保留 `{"redacted": true}`，不保存原文或正文哈希。**refined spec 和 XAML 仍是包含实际文案的产品文件，不是脱敏审计文件**，不应因报告脱敏而一并公开上传。

`props.tooltip`、`props.accessibleName`、`props.helpText` 分别生成 `ToolTip`、`AutomationProperties.Name`、`AutomationProperties.HelpText`，并遵循字面量转义。显式 tooltip 优先于输入框的 placeholder 提示；`semanticRole` 仍为语义元数据，不自动改变 WPF 控件类型。

`convert ... --patch path/to/patch.json` 在映射后通过 SafeAgentRefiner 应用补丁，并输出脱敏报告；补丁哈希必须对应同一源文件/页面使用 `convert --spec-only` 得到的 IR。未传补丁时只转换与校验，不调用 Agent 服务。

图片资源使用 `assets: {"pic1": "data:image/png;base64,..."}`，节点使用 `props.assetId: "pic1"`。源 `.vellum` 的 assets 会保留到 IR，生成器导出 `Assets/<内容哈希>.<扩展名>` 并写入 Image.Source。支持 PNG/JPEG/GIF/BMP/ICO/TIFF，单图不超过 20 MiB、总计不超过 100 MiB；缺失图片、SVG/WebP、路径和外部 URL 明确报错，不自动读取或下载。将生成结果放入 WPF 工程时，需要将 Assets 作为内容文件复制到输出目录，例如 `<Content Include="Assets\**\*" CopyToOutputDirectory="PreserveNewest" />`。`generate_all()` 返回值中 XAML 为字符串、图片为 bytes；CLI 会分别写出。

JSON IR 的 Command 必须是 ASCII 标识符，样式/资源颜色必须是带 `#` 的三、六或八位十六进制；无效值在读取和补丁应用阶段拒绝。直接构造模型的生成器仍保留安全丢弃无效 Command/颜色的防御。

---

## 5. 质量保证与测试架构 (Quality Assurance)

运行全部自动化测试：

```bash
python tests/run_tests.py
```

### 核心测试集覆盖：
1. **260 | * | 260 响应式 Canary 验证** ([`test_tdd_layout_canary.py`](tests/test_tdd_layout_canary.py))：
   - 验证三栏自适应容器在 1280px 调整至 1600px 过程中，两侧边栏固定在 260px，增量全部归属中央 `*` 列（Delta: `0 | +320 | 0`）。
2. **源数据严格校验测试** ([`test_source_validator.py`](tests/test_source_validator.py))：
   - 覆盖非法版本、空页面、重复节点 ID、非数字几何属性、负尺寸、幽灵 Parent 与循环引用拦截。
3. **Safe Agent Refiner 测试** ([`test_refiner.py`](tests/test_refiner.py))：
   - 覆盖语义白名单属性修改、SHA-256 哈希冲突拦截、修改 `layout`/`style` 违规拦截与原子全回滚保证。
4. **自包含与生成器修复测试** ([`test_self_contained_generate.py`](tests/test_self_contained_generate.py))：
   - 验证 `ui-spec.json` 独立生成等价性、Canvas 子节点设计尺寸保留与警告、Border Padding 包装器、TextBox 占位符隔离与按需生成 `x:Name`。
5. **真实 WPF 编译**：
   - 在 `samples/generated-wpf-demo/` 目录下执行 `dotnet build GeneratedWpfDemo.csproj`，实测 **0 错误、0 警告**。
