# Vellum → Semantic UI Spec → WPF/XAML Bridge 开发日志

本日志记录 Vellum 桥接工具与实验性工作流（Vellum 设计稿 → .vellum JSON → 语义化 UI Spec → WPF/XAML Generator → 运行验证）的完整演进、技术决策与测试记录。

---

## 2026-09-06: MVP 初版设计与落地

### 1. 任务背景与核心目标
- **目标**：验证从 Vellum 原生矢量设计稿到高质量 WPF/XAML 界面的 Vibe Coding 全链路。
- **架构原则**：
  - Vellum 负责设计表达；
  - 中间层 **Semantic UI Spec** 解耦设计格式与具体平台技术栈；
  - WPF Generator 负责生成地道、干净、无多余 Canvas 绝对定位的 XAML 标记代码；
  - 为未来的 AI Agent 提供 Spec 修改与布局推断的挂载点。
- **关键约束**：
  - 不修改 Vellum 编辑器原始核心代码；
  - 依赖极简（仅依赖 Python 3 标准库，零第三方外部库依赖）；
  - 遇到未知/复杂图形特性（如贝塞尔 path）采用优雅降级与日志报告策略，绝不 crash 终止。

---

### 2. 关键架构与技术决策 (Decisions & Rationale)

1. **为什么选择中间层 Semantic UI Spec (`ui-spec.json`)？**
   - 若直接绑定 `Vellum → XAML`，会将矢量绘图命令与具体 XAML 标签深耦合，无法向 React / Avalonia / Flutter 拓展。
   - 语义化 Spec 体现的是“组件与意图”（如 `button`、`input`、`card`、`columns: [260, "*", 260]`），对人类和 AI Agent 均具备极高的可读性与可编辑性。
2. **拒绝全页 Canvas 绝对定位的布局策略**：
   - 传统 Figma-to-code 工具往往机械复制坐标，输出大量 `<Canvas><Button Canvas.Left="120".../></Canvas>`，在窗口缩放或 DPI 变化时不可用。
   - 本工具优先通过 Auto-Layout 与空间分析，将视觉容器转换为 WPF 的 `Grid`（支持 `*` 弹性比例与固定列宽）和 `StackPanel`（带子项 Margin 间距补偿）。
3. **按钮与输入框启发式吸收 (Heuristic Absorption)**：
   - 当 Frame/Rect 满足按钮特征时，其内部唯一的文本节点被吸收为按钮的 `Content="Send"` 与 `Command="{Binding SendCommand}"`，而不是生成冗余嵌套的 TextBlock，保证生成的 XAML 符合 WPF 习惯用法。
4. **颜色资源集中抽取与去重**：
   - 遍历解析出的 UI 树及 Vellum 设计 Tokens，重复出现 2 次以上的颜色自动归集至 `Resources.xaml` 的 `<SolidColorBrush>`，在主窗体中使用 `{StaticResource ...}` 引用，避免硬编码重复。
5. **预留 Agent 扩展钩子 (`UiSpecRefiner`)**：
   - 在生成 XAML 之前预留 `UiSpecRefiner` 接口，后续可无缝接入 LLM 进行语义润色与布局智能重组。

---

### 3. 本次新建与关键文件清单 (Files Modified / Created)

| 文件路径 | 职责说明 |
| :--- | :--- |
| `tools/vellum-wpf-bridge/schemas/ui-spec.schema.json` | 语义 UI Spec 的 JSON Schema 规范定义 |
| `tools/vellum-wpf-bridge/src/vellum_wpf_bridge/models.py` | 规范化文档模型、UI Spec 数据类及 `UiSpecRefiner` 抽象接口 |
| `tools/vellum-wpf-bridge/src/vellum_wpf_bridge/vellum_adapter.py` | `.vellum` JSON 解析适配器，还原父子树拓扑结构 |
| `tools/vellum-wpf-bridge/src/vellum_wpf_bridge/semantic_mapper.py` | 启发式布局与控件语义映射核心（AutoLayout, Button, Input, Card） |
| `tools/vellum-wpf-bridge/src/vellum_wpf_bridge/resources.py` | 颜色去重与 SolidColorBrush 资源提取管理 |
| `tools/vellum-wpf-bridge/src/vellum_wpf_bridge/wpf_generator.py` | WPF XAML 代码合成器（生成 MainWindow.xaml, Resources.xaml, App.xaml） |
| `tools/vellum-wpf-bridge/src/vellum_wpf_bridge/report.py` | 转换指标与降级审计报告生成器 |
| `tools/vellum-wpf-bridge/src/vellum_wpf_bridge/utils.py` | PascalCase 命名清洗、十六进制颜色规范化与 XML 转义工具 |
| `tools/vellum-wpf-bridge/src/vellum_wpf_bridge/cli.py` | CLI 命令行执行入口（支持 convert, --spec-only 等参数） |
| `tools/vellum-wpf-bridge/samples/tabletop-chat.vellum` | 桌面跑团/聊天 UI 真实设计样例（Header + 左/中/右三栏 + 底部输入栏） |
| `tools/vellum-wpf-bridge/samples/generated-wpf-demo/` | 可直接使用 .NET 编译运行的完整 WPF 验证工程 |
| `tools/vellum-wpf-bridge/tests/` | 自动化单元测试套件（覆盖 Adapter、Mapper、Generator 与 Golden 快照比对） |
| `tools/vellum-wpf-bridge/README.md` | 工具使用指南与架构说明文档 |
| `log.md` | 全局开发变更与决策记录 |

---

### 4. 验证与测试记录 (Verification)

1. **单元测试与回归快照**：
   - 执行命令：`python tools/vellum-wpf-bridge/tests/run_tests.py`
   - 结果：**6 passed, 0 failed**（用时 0.007s）。
   - 涵盖：
     - `test_adapter.py`：校验树形层级恢复与非法格式阻断；
     - `test_semantic_mapper.py`：校验三栏列宽（`260`, `*`, `260`）、按钮命令提取与矢量降级机制；
     - `test_wpf_generator.py`：校验生成 XML 语法正确性与非 Canvas 布局约束；
     - `test_golden.py`：与预期 `MainWindow.xaml` 基准快照进行字符级行比对。
2. **CLI 转换全量执行**：
   - 执行命令：`$env:PYTHONPATH="src"; python -m vellum_wpf_bridge convert samples/tabletop-chat.vellum -o output`
   - 产出：`ui-spec.json`、`MainWindow.xaml`、`Resources.xaml`、`App.xaml`、`conversion-report.json`。
   - 转换审计：总节点 32，成功转换 32，降级 0，警告 0。
3. **WPF 真实工程编译 (`dotnet build`)**：
   - 环境：Windows 11，.NET SDK 10.0.302，WPF 目标框架 `net10.0-windows`。
   - 执行命令：`dotnet build` 于 `samples/generated-wpf-demo/`。
   - 结果：`GeneratedWpfDemo.dll` 生成成功，**0 个警告，0 个错误**。

---

### 5. 当前限制与后续规划 (Limitations & Next Steps)
- **当前限制**：
  1. 贝塞尔 Path 暂降级为几何占位，未输出完整 SVG/PathGeometry `Data="M..."`；
  2. 尚未处理按钮内部存在复杂复合徽章（如“图标 + 标签 + 快捷键”）的场景；
  3. 仅支持单页导出，暂未批量导出多 Page。
- **下一步推进重点**：
  1. 支持矢量 PathGeometry 映射输出；
  2. 接入 AI Spec Refiner 自动化调整布局与样式；
  3. 扩展 Avalonia XAML 生成器支持跨平台 Linux/macOS。


## 2026-09-06 23:06（北京时间）— GROK 遗留生成安全问题修复

- 目标：修复字面量 markup extension 注入、未校验 IR 的属性/注释注入和八位颜色重复转换；保留会话开始时已有的未提交修复，不提交或推送。
- 变更：utils/wpf_generator 为 Title、Content、Text、ToolTip、Tag、FontFamily 加入字面量转义；注释中的连续连字符安全编码。新增 spec_validator.py，在 UiSpec.from_dict 和两个公开模型生成入口检查必填字段、类型、有限数值、尺寸、Padding、Grid 索引和树结构。fmt_length 拒绝任意字符串。CLI 校验成功后才创建输出目录。同步 schema 和 README。
- 颜色证据：vellum_adapter 和 semantic_mapper 已将源 RGBA 转成 ARGB，旧 ResourceManager 会再次转换。现在仅源转换函数处理 RGBA，IR 资源、去重和内联颜色使用保留 ARGB 的函数；源 #12345680 → IR/WPF #80123456，序列化往返不变。
- 失败与修正：首轮 54 项中 53 通过，快照因过度转义普通注释/文本格式失败；缩小到危险连字符序列及花括号字面量，未修改 golden 基准。
- 验证：py -3.10 tools/vellum-wpf-bridge/tests/run_tests.py，65/65 通过，0 跳过（Python 3.10.0、.NET SDK 10.0.302）。新增 11 项安全测试含多组恶意输入、Agent patch 到生成器、已有输出不被非法 spec 覆盖、颜色去重和往返。真实 WPF XamlReader 验证七类属性字面值与实际 ARGB，原有 WPF Grid 测量和 golden 通过。git diff --check 通过（仅 Git 的换行规范提示）。
- 反证自审：XML 能解析不代表 WPF 不执行绑定，因此增加实际 XamlReader 和 BindingOperations 检查；颜色首次输出正确不代表往返/去重正确，因此分别覆盖。
- 边界：手写 IR 八位色必须按 ARGB，无法自动识别误填 RGBA；可选字段仍允许默认值，未知扩展字段仍保留既有处理，未实现完整通用 JSON Schema 引擎。现有危险 Command/非法颜色丢弃策略保持。未发布、提交或推送，无新增依赖。


## 2026-09-06 23:24（北京时间）— GROK 后续反馈修复

- 范围：报告正文泄露、提示/无障碍属性空操作、IR token 校验、convert 补丁入口、图片链路、ARGB 主题亮度及编辑器翻译 HTML 输出。保留已有未提交变更，未执行 Git 提交、推送、部署或远端 Actions。
- 报告：refinement-report v2 的 oldValue/newValue/reason 全部替换为 redacted 标记，不保留正文或可猜测正文哈希；refined spec 和 XAML 必须保留实际文案，文档明确不属于可公开审计产物。同步 docs/SPEC_CONSTRAINTS.md。
- 语义：在节点最外层生成 ToolTip、AutomationProperties.Name/HelpText（含 Border），显式 tooltip 覆盖 placeholder 提示；继续做 XAML 字面量转义。semanticRole 明确为元数据，不自动改变控件类型。
- IR：from_dict 和 SafeAgentRefiner 基底/结果拒绝非标识符 command 与非 hex 颜色；转换时跳过无法产生合法 ASCII 标识符的推断 command。直接构造模型保留生成器安全丢弃防御。主题按 ARGB 最后六位计算 RGB 亮度，不把 alpha 当 R。
- convert：移除 stub 调用，新增 --patch，经 canonical SHA-256 校验后使用 SafeAgentRefiner；无补丁时仍验证映射 IR，不引入 Agent 服务。
- 图片：沿用源 assets 内嵌资源，保留至 IR；assets.py 验证 base64、位图签名及单图 20 MiB/总计 100 MiB 限额，导出内容哈希命名的本地 Assets 文件。Image.Source 使用生成路径。generate_all 现含 bytes 图片，CLI 分类型落盘。缺失资源、外部 URL/路径、SVG/WebP 明确拒绝，不静默丢失；未添加转码依赖。WPF 工程需复制 Assets 到输出目录，README 有配置示例。
- 编辑器：legacy data-i18n-html 使用 textContent；HTML 模板中的翻译及 modal/section/快捷键标签在输出边界转义，去除三处参数预转义以避免双重转义，t() 本身仍返回原始文本。
- 验证：Bridge 74/74 通过、无跳过，包含 WPF 实际图片解码、AutomationProperties 值、字面量/ARGB、源图片 convert→独立 generate 和恶意补丁。原有 Refiner 测试 fixture 的字符串轨道改成契约要求的数字轨道，保持所有原断言；首次严格基底校验因此暴露该旧 fixture，修正后通过。Linux 仅跳过 Windows WPF 运行时检查，纯 Python 安全测试照常执行。
- 编辑器 CI：scripts/ci.py 首次因 Playwright 配套浏览器缺失而失败；使用现有 CHROMIUM_EXECUTABLE 入口和本机 Chrome 独立测试上下文重跑，JS 语法/构建与 37 项浏览器检查全部通过（Canvas 2D）。没有下载浏览器；这不等于远端 GitHub Actions 已运行。
- 反证自审：报告脱敏不等于 spec 脱敏，已明确区分；有 Source 不等于图片可读，新增真实 WPF 解码；XML 中有 AutomationProperties 不等于运行时生效，新增实际属性读取断言。现有样例/golden 未改写。待办仅为用户决定的 Git/远端交付；SVG/WebP 转码不在此次实现内。


## 2026-09-06 23:46（北京时间）— 统一手写模型与 JSON 的严格 token 契约

- 授权：用户确认统一严格拒绝、使用边界重新验证、保留发射层上下文编码的方案。当前检出 5353af5 已含标题/promptText/convert 空目录修复，本轮未改编辑器或上述既有修复。
- 改动：移除 strict_tokens 开关；JSON 与模型调用相同校验规则，颜色 predicate 共用。UiSpec.to_dict 在省略字段前校验原始模型，阻断构造后修改及负数样式被序列化过滤的绕过。生成器入口仍在资源状态修改前校验；发射层遇到非法 Command/颜色改为明确 ValueError，不再成功但丢属性。资源 XAML 输出验证 key 和颜色后使用规范化颜色。
- 边界：refine-validate 校验候选结果，与 apply 对齐且不修改原文档；convert 在验证、生成准备和 spec 序列化成功后写出，refine-apply 延后 mkdir。错误不回显非法值，资源值报错也不拼入用户资源键。保留合法可选字段/默认值和 XAML 字面量规则，无新增依赖或公开宽松模式。
- 验证：py -3.10 tools/vellum-wpf-bridge/tests/run_tests.py，82/82 通过、0 跳过（12.051 秒）。新增 8 项测试：JSON/模型/导出/两种生成入口一致拒绝、多组 token、修改后复验、导出不隐藏负数、资源状态不变、发射层独立拦截、合法文本/命令/ARGB 往返、补丁验证与应用一致、失败目录与已有输出保护。此前两个“丢弃非法值”测试升级为必须抛异常，未放宽测试。
- 反证自审：只在构造时校验挡不住 props 后改；只校验 to_dict 结果挡不住它省略非法 style 值。针对两者直接检查当前原始模型并加回归断言。WPF 真实解析、图片解码、无障碍、布局和 golden 全部通过。本轮未修改前端，未重跑浏览器测试。
- 交付边界：过去静默丢属性的手写模型调用现在会报错，这是用户确认的兼容性变化；不承诺任意宿主 Python 代码受沙箱限制，也不声称磁盘写入失败有多文件原子回滚。未提交、推送或运行远端 Actions。
