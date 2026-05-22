# Brep Semantic Explorer

CAD BRep/STEP 探索原型。当前主线是一个一体化 Web 服务：后端解析 STEP、用 gmsh 生成网格，前端用 Three.js 展示拓扑树、3D 模型和 STEP 原文追溯信息。

## 当前能力

- STEP 文件上传和本地加载。
- gmsh 网格化，显示面、边和三角网格。
- 左侧拓扑树：Solid -> Shell -> Face -> EdgeLoop -> Edge。
- 3D 视口选择面/边，并联动右侧 STEP 实体详情。
- 右侧属性面板显示实体 ID、类型、行号、原始 STEP 文本和引用关系。
- 左右面板可拖拽调整宽度，中间 3D 视口自适应。
- Trackball 相机控制：左键自由旋转、滚轮缩放、右键平移。
- Playwright 自动化巡检覆盖面板拖拽、视口自适应和拖拽旋转不误选。

## 项目结构

```text
brep_semantic_explorer/
├── app.py                         # 一体化 HTTP 服务和 API
├── backend/
│   ├── mesh_generator.py           # gmsh STEP 网格化
│   ├── requirements.txt            # Python 依赖
│   └── step_parser_v2.py           # STEP 实体解析和引用关系
├── frontend/
│   └── explorer.html               # 当前唯一前端入口
├── tests/
│   └── ui-interaction.spec.js      # Playwright 交互巡检
├── uploads/                        # 本地测试 STEP 文件
├── _bmad-output/                   # 规划和工作流产物
├── package.json
└── playwright.config.js
```

## 启动

安装 Python 依赖：

```bash
pip install -r backend/requirements.txt
```

启动服务：

```bash
python app.py
```

访问：

```text
http://localhost:8080
```

也可以带一个 STEP 文件直接启动并预加载：

```bash
python app.py uploads\100106_7f144e5b_0000_0001.step
```

## 自动化检查

安装 Node 依赖：

```bash
npm install
```

运行交互巡检：

```bash
npm test
```

可视化运行：

```bash
npm run test:ui
```

调试模式：

```bash
npm run test:ui:debug
```

## 当前技术债

- STEP 实体与 gmsh 拓扑的映射目前主要按实体顺序绑定，对复杂模型不够可靠。
- `app.py` 使用进程内全局状态，暂不适合多用户并发。
- 大文件网格化是同步流程，上传时会阻塞请求。
- 还没有持久化缓存、导出报告、测量、剖切、隐藏/隔离等分析工具。

## 已清理的旧版本债务

- 移除了旧纯前端入口 `frontend/index.html`、`frontend/index_v2.html`、`frontend/index_v3.html`。
- 移除了旧 FastAPI/实验后端入口 `backend/api_server.py`、`backend/step_parser.py`、`backend/geometry_extractor.py`。
- README 已改为只描述当前主线入口和运行方式。
