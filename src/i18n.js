/**
 * Vellum Lightweight i18n Localization Module
 * Pure Vanilla JS, zero runtime dependencies, reactive DOM binding & instant live switching.
 */

const enUS = {
  common: {
    cancel: 'Cancel',
    save: 'Save',
    close: 'Close',
    export: 'Export',
    undo: 'Undo',
    redo: 'Redo',
    delete: 'Delete',
    duplicate: 'Duplicate',
    group: 'Group',
    ungroup: 'Ungroup',
    rename: 'Rename',
    copy: 'Copy',
    paste: 'Paste',
    none: 'None',
    edit: 'Edit'
  },
  topbar: {
    brandAria: 'Vellum menu',
    toggleLayers: 'Toggle layers panel',
    workspace: 'Workspace',
    renameDoc: 'Rename document',
    savedLocally: 'Saved locally',
    savingLocally: 'Saving locally',
    saveFailed: 'Save failed',
    localFile: 'LOCAL FILE',
    profileTip: 'Local-first · no account required',
    present: 'Present frames',
    exportBtn: 'Export'
  },
  leftPanel: {
    designFile: 'Design file',
    searchLayersTitle: 'Search layers',
    tabLayers: 'Layers',
    tabAssets: 'Assets',
    collapseAll: 'Collapse layers',
    searchPlaceholder: 'Find a layer…',
    pagesHeading: 'Pages',
    addPage: 'Add page',
    layersHeading: 'Layers',
    startingRenderer: 'Starting renderer',
    webgpuBackend: 'WebGPU accelerated',
    canvasBackend: 'Canvas 2D fallback',
    settingsBtn: 'Editor settings'
  },
  toolbar: {
    select: 'Move (V)',
    frame: 'Frame (F)',
    rect: 'Rectangle (R)',
    ellipse: 'Ellipse (O)',
    line: 'Line (L)',
    pen: 'Pen (P) · click points, Enter to finish',
    text: 'Text (T)',
    hand: 'Hand (H)',
    insertImage: 'Place image (⇧⌘K)',
    commands: 'Commands (⌘K)'
  },
  canvas: {
    defaultPage: 'Design exploration',
    localBadgeTip: 'All changes stay on this device',
    hint: 'Space to pan · ⌘ scroll to zoom · ? for shortcuts',
    zoomOut: 'Zoom out',
    zoomIn: 'Zoom in',
    zoomOptions: 'Zoom options',
    performance: '{count} layers · {ms} ms CPU',
    welcomeTitle: 'A little more possible.',
    welcomeText: 'Your next idea starts here. Everything is editable.',
    dismiss: 'Dismiss'
  },
  inspector: {
    tabDesign: 'Design',
    tabPrototype: 'Prototype',
    toggleTheme: 'Toggle light / dark theme',
    footerQuote: 'Made for your next big idea.',
    help: 'Keyboard shortcuts',
    pageSection: 'Page',
    startWithFrame: 'Start with a frame',
    presetDesktop: 'Desktop',
    presetPhone: 'Phone',
    presetTablet: 'Tablet',
    presetSocial: 'Social',
    localColorStyles: 'Local color styles',
    editTokensTitle: 'Edit design tokens',
    textStyles: 'Text styles',
    yourWorkYourDevice: 'Your work, your device',
    deviceNote: 'No account. No uploads. This document is saved locally in your browser.',
    savePortableCopy: 'Save a portable copy',
    selectedLayers: '{count} layers selected',
    sharedProperties: 'Edit shared properties',
    componentInstance: 'Component instance',
    mainComponent: 'Main component',
    layerActions: 'Layer actions',
    alignLeft: 'Align left',
    alignCenter: 'Align center',
    alignRight: 'Align right',
    alignTop: 'Align top',
    alignMiddle: 'Align middle',
    alignBottom: 'Align bottom',
    position: 'Position',
    layout: 'Layout',
    clipContent: 'Clip content',
    autoLayout: 'Auto layout',
    gapPadding: 'Gap / Padding',
    freeform: 'Freeform',
    horizontalStack: 'Horizontal stack',
    verticalStack: 'Vertical stack',
    alignStart: 'Align start',
    alignEnd: 'Align end',
    toggleAutoLayout: 'Toggle auto layout',
    appearance: 'Appearance',
    opacity: 'Opacity',
    toggleVisibility: 'Toggle visibility',
    toggleLock: 'Toggle lock',
    typography: 'Typography',
    loadFont: 'Load font…',
    editText: 'Edit text',
    fill: 'Fill',
    solid: 'Solid',
    linearGradient: 'Linear gradient',
    toggleFill: 'Toggle fill',
    stroke: 'Stroke',
    noStroke: 'No stroke',
    toggleStroke: 'Toggle stroke',
    effects: 'Effects',
    dropShadow: 'Drop shadow',
    removeShadow: 'Remove shadow',
    noEffects: 'No effects',
    toggleShadow: 'Toggle shadow',
    constraints: 'Constraints',
    exportSection: 'Export',
    exportSelection: 'Export {name}',
    developer: 'Developer',
    inspectCSS: 'Inspect CSS',
    prototypeTitle: 'Prototype',
    prototypeDesc: 'Connect a layer to a frame. In preview, clicking that layer navigates to the destination.',
    interaction: 'Interaction',
    navigateOnClick: 'On click → Navigate to',
    noDestination: 'No destination',
    transitionInstant: 'Transition: instant. Keyboard arrows also navigate between frames.',
    selectLayer: 'Select a layer',
    selectLayerDesc: 'Select a button, card, or other layer to add an interaction.',
    flowPreview: 'Flow preview',
    presentFrames: 'Present frames',
    previewNote: 'Preview is local. It does not publish or upload your design.'
  },
  settings: {
    dialogTitle: 'A workspace that feels like yours.',
    dialogSubtitle: 'Local settings & hardware status',
    language: 'Language',
    languageEn: 'English',
    languageZh: '简体中文',
    themeLight: 'Light appearance',
    grid: 'Canvas dot grid',
    snap: 'Smart alignment guides',
    rulers: 'Canvas rulers',
    rendering: 'Rendering',
    backend: 'Backend: {backend}',
    visibleLayers: 'Visible layers: {count}',
    instances: 'Instances: {count}',
    sceneDrawCalls: 'Scene draw calls: {count}',
    submissionTime: 'CPU submission: {ms} ms',
    devicePixelRatio: 'Device pixel ratio: {dpr}',
    storage: 'Storage: {mode}',
    webgpuStatus: 'WebGPU status: {status}',
    renderNote: 'Vellum draws on demand. The displayed time measures CPU scene assembly and command submission, not GPU execution or FPS. WebGPU requires a compatible browser and secure context.'
  },
  commands: {
    newFile: 'New document',
    openFile: 'Open .vellum document',
    saveFile: 'Save portable document',
    undo: 'Undo',
    redo: 'Redo',
    fit: 'Fit all to view',
    fitSelection: 'Fit selection',
    actualSize: 'Zoom to 100%',
    duplicate: 'Duplicate selection',
    group: 'Group selection',
    ungroup: 'Ungroup selection',
    frameSelection: 'Frame selection',
    component: 'Create component',
    front: 'Bring to front',
    back: 'Send to back',
    distributeH: 'Distribute horizontally',
    distributeV: 'Distribute vertically',
    placeImage: 'Place an image',
    exportPNG: 'Export PNG',
    exportSVG: 'Export SVG',
    present: 'Present frames',
    theme: 'Toggle light / dark theme',
    grid: 'Toggle canvas grid',
    rulers: 'Toggle rulers',
    snap: 'Toggle smart snapping',
    tokens: 'Edit design tokens',
    inspectCSS: 'Inspect CSS',
    addPage: 'Add a page',
    settings: 'Rendering settings',
    loadFont: 'Load a local font…',
    help: 'Keyboard shortcuts',
    stressTest: 'Create 5,000-shape stress test',
    resetStarter: 'Restore Forma starter document',
    searchPlaceholder: 'What would you like to do?',
    searchAria: 'Search commands',
    navigateHint: '↑ ↓ to navigate &nbsp; · &nbsp; Enter to run &nbsp; · &nbsp; Esc to close',
    noMatching: 'No matching commands.'
  },
  menu: {
    header: 'Vellum — make room for ideas',
    newDoc: 'New document',
    openDoc: 'Open document…',
    saveDoc: 'Save portable document',
    placeImage: 'Place image…',
    designTokens: 'Design tokens',
    addPage: 'Add page',
    toggleTheme: 'Toggle light / dark',
    hideGrid: 'Hide dot grid',
    showGrid: 'Show dot grid',
    hideRulers: 'Hide rulers',
    showRulers: 'Show rulers',
    settings: 'Editor settings',
    shortcuts: 'Keyboard shortcuts'
  },
  contextMenu: {
    copy: 'Copy',
    paste: 'Paste',
    duplicate: 'Duplicate',
    group: 'Group selection',
    ungroup: 'Ungroup',
    frameSelection: 'Frame selection',
    component: 'Create component',
    front: 'Bring to front',
    back: 'Send to back',
    distributeH: 'Distribute horizontally',
    distributeV: 'Distribute vertically',
    rename: 'Rename',
    lockUnlock: 'Lock / unlock',
    hideShow: 'Hide / show',
    exportPNG: 'Export PNG',
    exportSVG: 'Export SVG',
    delete: 'Delete'
  },
  zoomMenu: {
    fit: 'Zoom to fit',
    fitSelection: 'Zoom to selection',
    actualSize: 'Zoom to 100%'
  },
  helpDialog: {
    title: 'A few keys. Endless possibilities.',
    subtitle: 'Your Vellum field guide.',
    tools: 'Tools',
    canvas: 'Canvas',
    editing: 'Editing',
    pan: 'Pan',
    zoom: 'Zoom',
    fitAll: 'Fit all',
    actualSize: 'Actual size',
    hidePanels: 'Hide panels',
    drawSquareCircle: 'Draw square / circle',
    disableSnapping: 'Disable snapping',
    commands: 'Commands',
    editTextPath: 'Edit text / path',
    finishPath: 'Finish path',
    nudge: 'Nudge',
    nudge10: 'Nudge 10px',
    saveFile: 'Save file',
    note: 'On Windows and Linux, use Ctrl in place of ⌘. Pen: drag an anchor while drawing to create Bézier handles. Alt-drag a handle to break tangent symmetry.'
  },
  exportDialog: {
    title: 'Take your work with you.',
    subtitle: 'Portable by design. No account required.',
    downloadDoc: 'Download .vellum document',
    downloadNote: 'Includes every page, editable layer, component, design token, and placed image.',
    exportHeading: 'Export {target}',
    selection: 'selection',
    currentPage: 'current page',
    pngOption: 'PNG image · 2×',
    svgOption: 'SVG vector',
    alreadyHave: 'Already have a Vellum file?',
    openDoc: 'Open document',
    jsonNote: 'Vellum files are JSON. This editor does not read or write Figma’s proprietary .fig format.'
  },
  newFileDialog: {
    title: 'Start with a clean canvas.',
    desc: 'Your current document will remain available in Undo. Export a .vellum copy to keep it as a separate file.',
    backup: 'Export current file',
    confirm: 'New document'
  },
  tokensDialog: {
    title: 'Design tokens',
    subtitle: 'Your shared visual foundation, stored in this file.',
    note: 'Changing a color remaps exact matching fills and strokes throughout the document.',
    exportJson: 'Export JSON',
    apply: 'Apply tokens'
  },
  inspectCSSDialog: {
    title: 'Inspect CSS',
    note: 'Geometry and visual styles. Vector paths and text shaping remain renderer-specific.',
    copyBtn: 'Copy CSS'
  },
  toasts: {
    savedSuccess: 'Saved locally',
    saveFailed: 'Save failed. Local storage is full or unavailable.',
    exportReady: 'Export file downloaded.',
    cssCopied: 'CSS copied',
    clipboardBlocked: 'Clipboard blocked. Select the code to copy it.',
    smartSnappingOn: 'Smart snapping on',
    smartSnappingOff: 'Smart snapping off',
    noFramesPresent: 'Create a frame to present your design.',
    profileTip: 'Your local workspace. No account, presence simulation, or cloud upload.',
    canvasStatusTip: 'Saved in this browser only. Export a .vellum copy for backup.',
    savedFileRestoredWarn: 'Saved file could not be restored. Your starter document is open.',
    stressTestNotice: '5,000 editable GPU primitives. See Settings for measured render statistics.',
    langChanged: 'Language changed to English.'
  }
};

const zhCN = {
  common: {
    cancel: '取消',
    save: '保存',
    close: '关闭',
    export: '导出',
    undo: '撤销',
    redo: '重做',
    delete: '删除',
    duplicate: '创建副本',
    group: '编组',
    ungroup: '解组',
    rename: '重命名',
    copy: '复制',
    paste: '粘贴',
    none: '无',
    edit: '编辑'
  },
  topbar: {
    brandAria: 'Vellum 主菜单',
    toggleLayers: '切换图层面板',
    workspace: '工作区',
    renameDoc: '重命名文档',
    savedLocally: '已保存在本地',
    savingLocally: '正在本地保存',
    saveFailed: '保存失败',
    localFile: '本地文件',
    profileTip: '本地优先 · 无需账号',
    present: '演示画框',
    exportBtn: '导出'
  },
  leftPanel: {
    designFile: '设计文件',
    searchLayersTitle: '搜索图层',
    tabLayers: '图层',
    tabAssets: '资源',
    collapseAll: '折叠所有图层',
    searchPlaceholder: '查找图层…',
    pagesHeading: '页面',
    addPage: '添加页面',
    layersHeading: '图层',
    startingRenderer: '正在启动渲染器',
    webgpuBackend: 'WebGPU 硬件加速',
    canvasBackend: 'Canvas 2D 降级渲染',
    settingsBtn: '编辑器设置'
  },
  toolbar: {
    select: '选择移动 (V)',
    frame: '画框 (F)',
    rect: '矩形 (R)',
    ellipse: '椭圆 (O)',
    line: '线条 (L)',
    pen: '钢笔 (P) · 点击绘制锚点，Enter 完成',
    text: '文本 (T)',
    hand: '抓手移动 (H)',
    insertImage: '置入图片 (⇧⌘K)',
    commands: '命令面板 (⌘K)'
  },
  canvas: {
    defaultPage: '设计探索',
    localBadgeTip: '所有修改均安全保存在本设备',
    hint: '空格拖动画布 · ⌘/Ctrl 滚轮缩放 · ? 查看快捷键',
    zoomOut: '缩小',
    zoomIn: '放大',
    zoomOptions: '缩放选项',
    performance: '{count} 个图层 · {ms} 毫秒 CPU',
    welcomeTitle: '让创意，成为可能。',
    welcomeText: '灵感始于此处，一切皆可自由编辑。',
    dismiss: '知道了'
  },
  inspector: {
    tabDesign: '设计',
    tabPrototype: '原型',
    toggleTheme: '切换明亮 / 深色外观',
    footerQuote: '为你的下一个非凡创意而生。',
    help: '键盘快捷键',
    pageSection: '页面',
    startWithFrame: '从画框开始',
    presetDesktop: '桌面端',
    presetPhone: '手机端',
    presetTablet: '平板端',
    presetSocial: '社交媒体',
    localColorStyles: '局部颜色样式',
    editTokensTitle: '编辑设计标记 (Design Tokens)',
    textStyles: '文本样式',
    yourWorkYourDevice: '纯本地化，掌握在你的设备',
    deviceNote: '无需注册账号，不上传云端。所有设计完整保存在当前浏览器本地。',
    savePortableCopy: '保存便携副本 (.vellum)',
    selectedLayers: '已选中 {count} 个图层',
    sharedProperties: '编辑共享属性',
    componentInstance: '组件实例',
    mainComponent: '母版组件',
    layerActions: '图层操作',
    alignLeft: '左对齐',
    alignCenter: '水平居中',
    alignRight: '右对齐',
    alignTop: '顶对齐',
    alignMiddle: '垂直居中',
    alignBottom: '底对齐',
    position: '位置',
    layout: '布局',
    clipContent: '裁剪超出内容',
    autoLayout: '自动布局',
    gapPadding: '间距 / 内边距',
    freeform: '自由布局',
    horizontalStack: '横向排列 (Row)',
    verticalStack: '纵向排列 (Column)',
    alignStart: '起始对齐',
    alignEnd: '末尾对齐',
    toggleAutoLayout: '切换自动布局',
    appearance: '外观',
    opacity: '不透明度',
    toggleVisibility: '显示 / 隐藏',
    toggleLock: '锁定 / 解锁',
    typography: '排版文字',
    loadFont: '加载本地字体…',
    editText: '编辑文本',
    fill: '填充',
    solid: '纯色',
    linearGradient: '线性渐变',
    toggleFill: '开关填充',
    stroke: '描边',
    noStroke: '无描边',
    toggleStroke: '开关描边',
    effects: '效果',
    dropShadow: '投影效果',
    removeShadow: '移除阴影',
    noEffects: '无效果',
    toggleShadow: '开关阴影',
    constraints: '响应约束',
    exportSection: '导出',
    exportSelection: '导出 {name}',
    developer: '开发属性',
    inspectCSS: '检查 CSS 代码',
    prototypeTitle: '交互原型',
    prototypeDesc: '将图层连接到画框。在预览演示中，点击该图层即可跳转到对应目标。',
    interaction: '交互事件',
    navigateOnClick: '点击时 → 跳转至',
    noDestination: '无目标画框',
    transitionInstant: '过渡效果：瞬时。也可使用键盘方向键在画框间切换。',
    selectLayer: '选择图层',
    selectLayerDesc: '选中按钮、卡片或其他图层即可为其配置交互事件。',
    flowPreview: '流程预览',
    presentFrames: '演示画框',
    previewNote: '预览完全在本地运行，不会发布或上传你的设计。'
  },
  settings: {
    dialogTitle: '打造顺手专属的设计工作空间。',
    dialogSubtitle: '本地设置与硬件渲染状态',
    language: '界面语言',
    languageEn: 'English (英文)',
    languageZh: '简体中文',
    themeLight: '浅色外观 (Light)',
    grid: '画布点状网格',
    snap: '智能对齐参考线',
    rulers: '画布标尺',
    rendering: '渲染管线',
    backend: '渲染后端：{backend}',
    visibleLayers: '可见图层数：{count}',
    instances: 'GPU 实例数：{count}',
    sceneDrawCalls: '场景绘制调用：{count}',
    submissionTime: 'CPU 提交耗时：{ms} 毫秒',
    devicePixelRatio: '设备像素比 (DPR)：{dpr}',
    storage: '存储后端：{mode}',
    webgpuStatus: 'WebGPU 状态：{status}',
    renderNote: 'Vellum 按需触发重绘。此处时间衡量的是 CPU 场景装配与指令提交耗时，而非 GPU 渲染周期或帧率。WebGPU 需要兼容的浏览器及安全上下文。'
  },
  commands: {
    newFile: '新建文档',
    openFile: '打开 .vellum 文档',
    saveFile: '保存便携文档',
    undo: '撤销',
    redo: '重做',
    fit: '缩放以适应全貌',
    fitSelection: '缩放以适应所选对象',
    actualSize: '缩放到 100%',
    duplicate: '复制所选图层',
    group: '编组所选对象',
    ungroup: '解组所选对象',
    frameSelection: '将所选对象置入画框',
    component: '创建组件',
    front: '移至顶层',
    back: '移至底层',
    distributeH: '水平均匀分布',
    distributeV: '垂直均匀分布',
    placeImage: '置入图片',
    exportPNG: '导出 PNG 图像',
    exportSVG: '导出 SVG 矢量图',
    present: '全屏演示画框',
    theme: '切换明亮 / 深色主题',
    grid: '开关画布网格',
    rulers: '开关标尺',
    snap: '开关智能吸附对齐',
    tokens: '编辑设计标记 (Tokens)',
    inspectCSS: '检查 CSS 样式代码',
    addPage: '添加新页面',
    settings: '渲染设置与统计',
    loadFont: '加载本地字体…',
    help: '键盘快捷键指南',
    stressTest: '生成 5,000 图形压力测试',
    resetStarter: '恢复 Forma 初始设计范例',
    searchPlaceholder: '你想做什么操作？',
    searchAria: '搜索所有命令',
    navigateHint: '↑ ↓ 方向键导航 &nbsp; · &nbsp; Enter 运行 &nbsp; · &nbsp; Esc 关闭',
    noMatching: '未找到匹配的命令。'
  },
  menu: {
    header: 'Vellum — 为创意腾出空间',
    newDoc: '新建文档',
    openDoc: '打开文档…',
    saveDoc: '保存便携文档',
    placeImage: '置入图片…',
    designTokens: '设计标记 (Tokens)',
    addPage: '添加新页面',
    toggleTheme: '切换明亮 / 深色外观',
    hideGrid: '隐藏点状网格',
    showGrid: '显示点状网格',
    hideRulers: '隐藏标尺',
    showRulers: '显示标尺',
    settings: '编辑器设置',
    shortcuts: '键盘快捷键'
  },
  contextMenu: {
    copy: '复制',
    paste: '粘贴',
    duplicate: '创建副本',
    group: '编组所选',
    ungroup: '解组',
    frameSelection: '置入画框',
    component: '创建组件',
    front: '移至顶层',
    back: '移至底层',
    distributeH: '水平分布',
    distributeV: '垂直分布',
    rename: '重命名',
    lockUnlock: '锁定 / 解锁',
    hideShow: '隐藏 / 显示',
    exportPNG: '导出 PNG',
    exportSVG: '导出 SVG',
    delete: '删除'
  },
  zoomMenu: {
    fit: '缩放以适应全貌',
    fitSelection: '缩放以适应选中图层',
    actualSize: '缩放到 100%'
  },
  helpDialog: {
    title: '方寸按键，无限可能。',
    subtitle: 'Vellum 快捷操作随身指南',
    tools: '设计工具',
    canvas: '画布视窗',
    editing: '图形编辑',
    pan: '平移画布',
    zoom: '缩放视图',
    fitAll: '适应全貌',
    actualSize: '实际尺寸 (100%)',
    hidePanels: '隐藏/显示侧栏',
    drawSquareCircle: '绘制正方形/正圆',
    disableSnapping: '临时禁用对齐吸附',
    commands: '命令面板',
    editTextPath: '编辑文本 / 路径',
    finishPath: '完成路径编辑',
    nudge: '微移 (1px)',
    nudge10: '快速移动 (10px)',
    saveFile: '保存文件',
    note: '在 Windows 与 Linux 上使用 Ctrl 键代替 ⌘。钢笔工具：在绘制时拖动锚点可拉出贝塞尔手柄；按住 Alt 拖动手柄可打破切线对称。'
  },
  exportDialog: {
    title: '随时随地，携带你的设计成果。',
    subtitle: '原生便携设计 · 无需账户登录',
    downloadDoc: '下载 .vellum 文档',
    downloadNote: '包含所有画板页面、可编辑图层、组件母版、设计标记以及内置图片资源。',
    exportHeading: '导出{target}',
    selection: '当前选中对象',
    currentPage: '当前页面',
    pngOption: 'PNG 图像 · 2×',
    svgOption: 'SVG 矢量格式',
    alreadyHave: '已有 Vellum 文件？',
    openDoc: '打开文档',
    jsonNote: 'Vellum 文件基于开放的 JSON 规范存储。本编辑器不读取也不导出 Figma 专有的私有 .fig 格式。'
  },
  newFileDialog: {
    title: '从一张纯净的空白画布开始。',
    desc: '你当前的文档依然可以通过“撤销”恢复。建议先导出一份 .vellum 副本作为备份独立存储。',
    backup: '导出当前文件备份',
    confirm: '确认新建文档'
  },
  tokensDialog: {
    title: '设计标记 (Design Tokens)',
    subtitle: '共享的视觉设计基石，完整内置于该文件中。',
    note: '修改色值会自动重映射全篇文档中完全匹配的填充色与描边色。',
    exportJson: '导出 JSON',
    apply: '应用标记修改'
  },
  inspectCSSDialog: {
    title: '检查 CSS 样式代码',
    note: '包含几何坐标与可视化表现样式。矢量路径与文字排版渲染细节归属渲染引擎。',
    copyBtn: '复制 CSS 代码'
  },
  toasts: {
    savedSuccess: '已安全保存在本地',
    saveFailed: '保存失败。本地存储已满或当前环境不可用。',
    exportReady: '导出文件已就绪并开始下载。',
    cssCopied: 'CSS 代码已成功复制到剪贴板',
    clipboardBlocked: '剪贴板访问受阻，请直接在代码框内全选复制。',
    smartSnappingOn: '智能对齐吸附：已开启',
    smartSnappingOff: '智能对齐吸附：已关闭',
    noFramesPresent: '请先创建一个画框 (Frame) 以便进行演示。',
    profileTip: '本地私有工作区。无账户系统、无在线状态模拟、无云端上传。',
    canvasStatusTip: '仅保存在当前浏览器本地。建议导出 .vellum 文件进行离线备份。',
    savedFileRestoredWarn: '本地保存的历史文档无法恢复，已为你重新打开初始示例文件。',
    stressTestNotice: '已生成 5,000 个可编辑 GPU 基础图形。可在“设置”中查看实测渲染状态。',
    langChanged: '界面语言已切换为简体中文。'
  }
};

class I18nEngine {
  constructor() {
    this.locales = {
      'en-US': enUS,
      'zh-CN': zhCN
    };
    this.currentLocale = 'zh-CN';
    this.fallbackLocale = 'en-US';
    this.listeners = new Set();
    this.storageKey = 'vellum-options';
  }

  init(preferredLocale) {
    let chosen = preferredLocale;

    if (!chosen && typeof localStorage !== 'undefined') {
      try {
        const stored = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        if (stored && stored.language && this.locales[stored.language]) {
          chosen = stored.language;
        }
      } catch { }
    }

    if (!chosen) {
      const browserLang = (typeof navigator !== 'undefined' && navigator.language ? navigator.language : 'en-US').toLowerCase();
      chosen = browserLang.startsWith('zh') ? 'zh-CN' : 'en-US';
    }

    this.currentLocale = this.locales[chosen] ? chosen : this.fallbackLocale;
    if (typeof document !== 'undefined' && document.documentElement) {
      document.documentElement.lang = this.currentLocale.slice(0, 2);
    }
    this.translateDOM();
    return this.currentLocale;
  }

  getSupportedLocales() {
    return Object.keys(this.locales);
  }

  getLocale() {
    return this.currentLocale;
  }

  setLocale(locale) {
    if (!this.locales[locale] || locale === this.currentLocale) {
      return false;
    }

    this.currentLocale = locale;
    if (typeof document !== 'undefined' && document.documentElement) {
      document.documentElement.lang = locale.slice(0, 2);
    }

    this.translateDOM();

    for (const listener of this.listeners) {
      try {
        listener(locale, this);
      } catch (err) {
        console.error('[i18n] Listener error:', err);
      }
    }

    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('vellum:localechange', {
        detail: { locale, engine: this }
      }));
    }

    return true;
  }

  t(key, params = {}, fallback = '') {
    const value = this._resolve(this.locales[this.currentLocale], key) ??
                  this._resolve(this.locales[this.fallbackLocale], key) ??
                  fallback ??
                  key;

    if (typeof value !== 'string') {
      return value ?? key;
    }

    if (!params || Object.keys(params).length === 0) {
      return value;
    }

    return value.replace(/\{(\w+)\}/g, (match, paramKey) => {
      return params[paramKey] !== undefined ? String(params[paramKey]) : match;
    });
  }

  _resolve(dict, key) {
    if (!dict || !key) return null;
    const parts = key.split('.');
    let current = dict;
    for (const part of parts) {
      if (current && typeof current === 'object' && part in current) {
        current = current[part];
      } else {
        return null;
      }
    }
    return current;
  }

  translateDOM(root) {
    if (typeof document === 'undefined') return;
    root = root || document.body;
    if (!root) return;

    const textNodes = root.querySelectorAll('[data-i18n]');
    for (const el of textNodes) {
      const key = el.getAttribute('data-i18n');
      if (key) el.textContent = this.t(key);
    }

    const htmlNodes = root.querySelectorAll('[data-i18n-html]');
    for (const el of htmlNodes) {
      const key = el.getAttribute('data-i18n-html');
      if (key) el.innerHTML = this.t(key);
    }

    const titleNodes = root.querySelectorAll('[data-i18n-title]');
    for (const el of titleNodes) {
      const key = el.getAttribute('data-i18n-title');
      if (key) el.setAttribute('title', this.t(key));
    }

    const ariaNodes = root.querySelectorAll('[data-i18n-aria]');
    for (const el of ariaNodes) {
      const key = el.getAttribute('data-i18n-aria');
      if (key) el.setAttribute('aria-label', this.t(key));
    }

    const placeholderNodes = root.querySelectorAll('[data-i18n-placeholder]');
    for (const el of placeholderNodes) {
      const key = el.getAttribute('data-i18n-placeholder');
      if (key) el.setAttribute('placeholder', this.t(key));
    }
  }

  subscribe(listener) {
    if (typeof listener === 'function') {
      this.listeners.add(listener);
    }
    return () => this.listeners.delete(listener);
  }
}

export const i18n = new I18nEngine();
export const t = (key, params, fallback) => i18n.t(key, params, fallback);
export const locales = { 'en-US': enUS, 'zh-CN': zhCN };
