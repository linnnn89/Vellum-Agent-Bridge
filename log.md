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
