# 更新日志

## v3.1 - 主线收敛与交互打磨 (2026-05-22)

### ✨ 新增与优化

- ✅ 当前前端主入口收敛为 `frontend/explorer.html`
- ✅ 左右面板支持拖拽调整宽度，中间 3D 视口自适应
- ✅ 相机控制切换为 TrackballControls，支持更自由的旋转
- ✅ 鼠标拖拽旋转不会误触发 Face/Edge 选择
- ✅ 增加 Playwright 交互巡检

### 🧹 债务清理

- 移除旧纯前端入口：`frontend/index.html`、`frontend/index_v2.html`、`frontend/index_v3.html`
- 移除旧后端/实验入口：`backend/api_server.py`、`backend/step_parser.py`、`backend/geometry_extractor.py`
- README 改为只描述当前主线运行方式
- Python 依赖补充 `gmsh`
- 忽略 Python 缓存、Playwright 结果和生成网格数据

### 📦 当前文件结构

```
brep_semantic_explorer/
├── app.py
├── backend/
│   ├── mesh_generator.py
│   ├── requirements.txt
│   └── step_parser_v2.py
├── frontend/
│   └── explorer.html
├── tests/
│   └── ui-interaction.spec.js
├── README.md
├── CHANGELOG.md
├── package.json
└── playwright.config.js
```

---

## v3.0 - 3D 可视化版本 (2026-05-21)

### ✨ 新增功能

**3D 可视化**
- ✅ Three.js 集成，真正的 3D 渲染
- ✅ 顶点显示为红色球体
- ✅ 边显示为蓝色线段
- ✅ 支持鼠标交互：
  - 拖动旋转视角
  - 滚轮缩放
  - 右键平移
  - 点击元素选中

**几何数据提取**
- ✅ 从 STEP 文件提取顶点 3D 坐标
- ✅ 提取边的起点、终点、长度、曲线类型
- ✅ 计算模型包围盒
- ✅ 支持科学记数法坐标（如 -1.83697019872103E-16）

**搜索与过滤**
- ✅ 按实体 ID 搜索
- ✅ 按类型过滤（全部/面/边/顶点）
- ✅ 实时搜索结果

**视图控制**
- ✅ 显示/隐藏顶点
- ✅ 显示/隐藏边
- ✅ 显示/隐藏坐标轴
- ✅ 重置视角
- ✅ 适应视图

**反向追溯（核心功能）**
- ✅ 3D 视图点击 → 显示 STEP 原始文本
- ✅ 列表点击 → 3D 视图高亮
- ✅ 引用实体跳转
- ✅ 完整依赖关系链

**用户体验**
- ✅ 暗色主题界面
- ✅ 加载动画
- ✅ 状态指示器
- ✅ 调试日志（F12 控制台）

### �� Bug 修复

- 修复 CARTESIAN_POINT 解析正则表达式（支持 `('name',(x,y,z))` 格式）
- 修复 Three.js 版本兼容性问题（降级到 r128）
- 修复小模型包围盒为 0 的问题
- 修复顶点球体过小看不见的问题

### 📦 当时文件结构

```
brep_semantic_explorer/
├── backend/
│   ├── step_parser_v2.py       # v2 增强解析器（反向引用、拓扑分析）
│   ├── mesh_generator.py       # gmsh 网格生成
│   └── requirements.txt
├── frontend/
│   └── explorer.html           # 当前 3D 探索界面
├── data/
│   └── *_mesh.json             # 生成的几何数据
├── README.md
└── CHANGELOG.md
```

### 🎯 测试数据

- 测试文件：`D:\company\code\Step_Test_Data\*.step`
- 成功解析：100106_7f144e5b_0000_0001.step（148 实体，4 顶点，6 边）

---

## v2.0 - 增强版界面 (2026-05-20)

### ✨ 新增功能

- 暗色主题界面
- 搜索功能（按 ID 或类型）
- 类型过滤（面/边/顶点）
- 支持边和顶点实体
- 统计信息面板

---

## v1.0 - 原型版本 (2026-05-20)

### ✨ 核心功能

- STEP 文件解析（纯 Python）
- 实体信息提取
- 引用关系分析
- 基础 Web 界面
- 反向追溯功能（从实体 → STEP 文本）

### 📊 统计

- 解析速度：6887 个实体 < 1 秒
- 支持实体类型：50+ 种
- 无需 OpenCASCADE 依赖
