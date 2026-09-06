# Vellum-Agent-Bridge: 架构约束与内部规范 (Specification & Constraints)

> **文档性质**：项目内部工程基准与安全约束。定义编译器、IR 契约、Agent 修改边界与验证红线。
> **适用对象**：内部核心开发者、编译器维护者及自主协作 Agent。

---

## 1. 核心架构与分层不变性 (Architecture Invariants)

Vellum-Agent-Bridge 采用单向、严格分层的编译架构：

```text
.vellum JSON (设计源数据)
     │
     ▼  [VellumDocumentAdapter / Source Validator]
Normalized Vellum Scene
     │
     ▼  [SemanticMapper & LayoutContract]
Semantic UI Spec (Self-Contained IR)
     │
     ├─── (可选) Agent Refinement Patch [Safe Refiner]
     ▼
WPF / XAML Generator
     │
     ▼
Deterministic C# / XAML
```

### 1.1 独立性与自包含（Self-Contained IR）
- `ui-spec.json` 生成后即为完整独立的抽象语法树（IR），包含所有页面结构、布局元数据以及抽取/推断的颜色与资源（`UiSpec.resources`）。
- XAML 代码生成器（`WpfGenerator`）**仅依赖 `UiSpec`**，严禁逆向读取原始 `.vellum` 文件或隐藏调用 `VellumDocument`。
- 支持独立命令行重入：`vellum-wpf generate ui-spec.json` 必须能直接生成同等质量的 XAML 与资源字典。

### 1.2 数据校验严密性（Source Validation）
- 禁止在底层静默容错非法文档。
- 校验器必须强制检验：
  - 格式与版本：`format == "vellum"`, `version == 1`；
  - 页面合法性：必须包含非空页面，页面 ID 语法合法；
  - 节点 ID 唯一性：文档内所有图层 ID 必须严格唯一；
  - 几何数值合法性：`x, y, w, h, rotation, opacity` 必须为有限有效数值；尺寸禁止负值；
  - 层级拓扑完整性：`parentId` 必须指向同页面存在的节点，且无任何循环引用与非法超深层级。

---

## 2. 布局契约规则 (Layout Contract)

Sizing、Anchoring、Flow 三个维度正交解耦，严禁通过图层名称（如 "Row", "Col"）猜测布局。

### 2.1 规则矩阵
| 场景 | 目标容器 | 转换规则与约束 |
| :--- | :--- | :--- |
| **AutoLayout + 主轴含 fill** | `Grid` | 展开为带 `*` 轨道的 Grid；子元素间距（`gap`）通过显式 spacer track 展开，子节点不得再输出该主轴的固定 `Width`/`Height`。 |
| **AutoLayout + 主轴无 fill** | `StackPanel` | 转换为水平或垂直 `StackPanel`；子元素间距（`gap`）通过非末尾项的 trailing `Margin` 展开。 |
| **Freeform 自由排版** | `Canvas` | 子元素保留绝对设计坐标与物理尺寸（`Canvas.Left`, `Canvas.Top`, `Width`, `Height`），并输出 `responsive constraint lost on Canvas` 警告。 |
| **内边距（Padding）** | `Border` 包装器 | 严禁将容器的 `padding` 错误映射为 `Margin`。若存在内边距，统一生成 `<Border Padding="..." ...>` 作为外层布局包装。 |
| **输入控件（Input）** | `TextBox` | 严禁将占位提示符（placeholder）写入 `TextBox.Text`。`Text` 默认保持为空，placeholder 转入 `Tag` 或 `ToolTip`。 |
| **控件标识（x:Name）** | 按需生成 | 严禁为所有文本块和面板普遍生成无意义的 `x:Name`。仅对 `Button`、`Input` 生成 `generatedName`；WPF `x:Name` 只使用该字段（缺失时由稳定 `id` 推导）。Agent 可改 `name`，不可改 `generatedName`。 |

### 2.2 响应式 Canary 验证标准
布局编译器必须持续通过 3 栏内容自适应测试（`260 | * | 260`）：
- 宽度 1280px 时：`260 | 760 | 260`
- 宽度 1600px 时：`260 | 1080 | 260`
- 变化增量（Delta）：`0 | +320 | 0`
- 绝对禁止两端固定列受中心伸缩影响发生尺寸漂移。

---

## 3. 安全 Agent 修正机制 (Safe Refiner Contract)

为了让大语言模型或自动化 Agent 能够对 UI Spec 进行无损语义增强，同时坚决杜绝 LLM 破坏视觉设计和布局流，制定本约束。

### 3.1 零信任与单向 Patch 机制
- 严禁让 Agent 直接重新生成全量 `ui-spec.json`。
- Agent 必须且仅能提交符合 `ui-spec-patch.schema.json` 规范的操作指令（Patch）。

### 3.2 属性修改白名单与黑名单
- **允许修改项（语义白名单）**：
  - `name`（节点语义名称，不影响 `x:Name`）
  - `props.text`（文本内容；仅 button / input / text）
  - `props.command`（按钮绑定的命令名称；仅 button）
  - `props.placeholder`（占位符；仅 input）
  - `props.tooltip`（提示信息）
  - `props.accessibleName`（无障碍名称）
  - `props.helpText`（辅助说明）
  - `props.semanticRole`（语义角色提示）
- **禁止修改项（设计黑名单，直接拒绝）**：
  - `id`、`type`、`source`、`generatedName`
  - `layout.*`（包括 `type`, `direction`, `gap`, `padding`, `width`, `height`, `widthMode`, `heightMode`, `columns`, `rows` 等全部布局属性）
  - `style.*`（包括 `background`, `foreground`, `borderColor`, `borderThickness`, `cornerRadius`, `fontSize` 等视觉样式）
  - `children`（结构拓扑）
  - `resources`（资源定义）
- **其它补丁规则**：同一 `nodeId+path` 不得 set 两次；编译器不得把语义猜测写成 `props.command`。

### 3.3 原子执行与审计报告
1. **基底哈希检验**：校验 `baseSpecSha256` 是否与当前 `ui-spec.json` 的 SHA-256 完全吻合，防止并发冲突或脏读；
2. **全量前置校验**：遍历所有 operation，检查 `nodeId` 是否存在、`path` 是否在白名单、`value` 类型是否合法；
3. **全通过写入**：只要有一条 operation 不合规，整批 patch 立即回滚并报错退出；
4. **生成审计文件**：成功应用后生成 `refinement-report.json`，记录被修改节点、路径与操作数；报告 v2 将原始值、新值和原因替换为 redacted 标记，不输出正文或可字典猜测的正文哈希。实际 refined spec 仍保留 UI 文案，应按用户内容管理，不作为公开审计产物。

---

## 4. 工程范围边界 (Scope Boundaries & Non-Goals)

为保持项目的纯粹性、健壮性与易维护性，明确以下范围边界：

- **无外部云端与 LLM API 强绑定**：编译管线核心完全基于标准库与纯本地算法，不依赖 OpenAI/Gemini/Anthropic API 或云端服务；
- **不自动生成业务 ViewModel 代码**：仅在 XAML 控件上暴露声明式 Command/Binding 插槽，不越俎代庖生成复杂业务逻辑代码；
- **不追求完整 SVG 拓扑运算**：Path/Bézier 等图形元素以通用 Geometry/Fallback 形式表达，不追求在 C# 层重建复杂布尔运算引擎；
- **保持单一职责**：专注于 `Vellum → UI Spec → WPF` 的工程闭环，不分散精力构建 React、Avalonia 或 Flutter 多端运行时。

---

## 5. 依赖边界与依赖关系清单 (Dependencies & Boundaries)

为保证系统的极致轻量、高可移植性与工程稳定性，各子系统严格遵守以下依赖边界：

### 5.1 编译器桥梁依赖 (`tools/vellum-wpf-bridge`)
- **运行时环境**：Python 3.10+
- **第三方包依赖**：**零依赖 (0 Third-Party Dependencies)**。
  - 核心实现仅使用 Python 标准库：`json`, `hashlib`, `re`, `math`, `argparse`, `dataclasses`, `pathlib`, `typing`。
  - 严禁擅自引入 `pydantic`, `jsonschema`, `click`, `rich` 等第三方重型依赖，确保冷启动毫秒级且无轮子版本冲突。
- **打包依赖**：`setuptools >= 61.0`（仅供 `pip install -e .` 构建标准命令行软链接）。
- **测试期依赖**：
  - `unittest`：Python 原生内置；
  - `node.js >= 18`（可选）：仅供 `test_validate_vellum.py` 跨环境验证原生 `DocumentModel.parse()`，若未检测到 Node 则自动跳过该测试，不影响整体单测通过。
- **目标输出环境依赖**：
  - 生成的 WPF 项目支持 `.NET SDK 8.0 / 9.0 / 10.0`（Windows 环境），生成的 XAML 和 C# 代码为纯原生 WPF，**不依赖任何外部 NuGet 包**。

### 5.2 前端编辑器与国际化系统 (`src/`)
- **浏览器运行时**：现代标准浏览器（Chrome 113+, Edge 113+, Safari 17+, Firefox Nightly）。
- **前端外部依赖**：**零依赖 (Zero Runtime Dependencies)**。
  - 无 npm、无 Webpack/Vite/Rollup、无 React/Vue、无第三方 CSS 库；
  - 双语国际化引擎 `src/i18n.js` 为纯原生 ES Module 编写，基于 DOM 声明式属性 `data-i18n*` 驱动，零外部框架包袱。
- **CI 与构建脚本依赖**：
  - `python >= 3.10`：标准库打包 `Vellum.html`（`build.py`）与静态发布包（`scripts/build_site.py`）；
  - `node.js`：仅用于 CI 的 `node --check` 语法静态检查；
  - `playwright`：仅用于可选的端到端浏览器冒烟测试（`tests/smoke.py`）。

---

## 6. 核心模块实现逻辑与调用链路 (Implementation Logic & Call Graph)

```text
[CLI vellum-wpf]
  │
  ├── validate:  validator.validate_vellum_file()
  │
  ├── convert:   adapter.load_from_file()
  │                │
  │                ▼
  │              mapper.map_document()  <──  resources.ResourceManager
  │                │
  │                ▼
  │              generator.generate_all()  <──  UiSpec (Self-Contained)
  │
  ├── generate:  UiSpec.from_dict()
  │                │
  │                ▼
  │              generator.generate_all()  (完全不碰 .vellum)
  │
  ├── refine-validate: refiner.validate_patch()  (SHA-256 核验 + 语义白名单检查)
  │
  └── refine-apply:    refiner.apply_patch()     (原子写入 + 生成 refinement-report.json)
```

1. **`validator.py`**：两遍扫描逻辑。遍一检查所有页面及其直接子节点的属性类型、有限数值、无负尺寸与 ID 唯一性字典；遍二扫描有向图，追溯 `parentId` 祖先链，拦截自环、非存在引用以及深度大于 100 的循环层级。
2. **`layout_contract.py`**：将节点归纳为 fixed / fill / absolute，通过矩阵遍历计算各子元素在主轴与交叉轴的占比；为带 gap 的 Grid 生成虚交错列并对齐物理索引。
3. **`resources.py`**：IR 中保留语义 Token 名（如 `Brand / Iris`）；WPF 后端再转换为 `Brush.Brand.Iris`。以色彩精确十六进制值（`#RRGGBB` / `#AARRGGBB`）为索引去重，将跨图层高频颜色提升为 `Resources.xaml` 里的静态资源画刷。
4. **`refiner.py`**：将目标 `ui-spec.json` 按键名升序格式化并哈希计算规范 SHA-256，匹配补丁中声明的 `baseSpecSha256`；随后基于递归节点字典进行针对性局部替换，所有修改前的值保存于内存回滚缓冲区，仅当全部 Operation 校验无误后方才执行写入操作并导出审计追踪。
