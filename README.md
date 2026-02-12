# 🏛️ ArchGraph · 建筑灵感知识图谱

**用可交互知识图谱管理你的建筑灵感，用 AI 拓展你的设计视野。**

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-yellow)
![D3.js](https://img.shields.io/badge/D3.js-v7-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

> 🎯 **项目定位**：一个集AI能力与数据可视化于一体的全栈应用，展示全栈开发、AI集成、数据可视化等综合能力

> 🌐 **在线 Demo**：[点击体验](https://your-demo-url.railway.app) | 📖 [部署指南](DEPLOYMENT.md) | 📚 [用户手册](USER_GUIDE.md)

## ✨ 核心功能

### 📌 案例管理
- **手动添加**：录入名称、建筑师、年份、地点、标签、设计描述等
- **URL智能导入**：粘贴 ArchDaily / 谷德 / gooood 等链接，AI 自动爬取并提取结构化信息
- **图片上传**：支持本地图片上传或图片URL
- **批量操作**：支持数据导入导出（JSON/CSV/GraphML格式）

### 🕸️ 交互式知识图谱
- **D3.js力导向图**：案例、标签、概念、星云自动生成关联关系网络
- **交互操作**：点击节点查看详情、拖拽节点、缩放画布、悬浮预览
- **智能筛选**：点击标签高亮关联节点，支持多标签组合筛选
- **主题切换**：支持暗色/亮色主题，适配不同使用场景

### 🧬 方案融合（核心差异化功能）
- 选中 2-4 个案例，选择要融合的设计维度（手法 / 场地处理 / 概念 / 技术 / 形式 / 结构）
- AI 从每个案例中提取该维度的"设计 DNA"，重组为一个全新的方案构想
- 生成内容包括：组合逻辑、落地场景建议、张力与潜力分析
- 这是建筑师做设计时大脑里真实发生的过程（从不同参考中抽取片段重组），但目前没有工具把这个过程外化

### 🔍 AI 灵感搜索
- **自然语言查询**：用自然语言描述设计需求（如"滨水社区，低成本改造，社区参与"）
- **智能匹配**：AI 从已有图谱中匹配关联案例并解释关联逻辑
- **联网推荐**：推荐图谱中没有的新案例（支持联网搜索），一键添加
- **策略生成**：生成具体可操作的设计策略建议
- **概念拓展**：推荐可继续深挖的概念方向

### 🏷️ 标签系统
- **标签云可视化**：显示每个标签的案例数量，点击筛选
- **层级结构**：支持创建父标签和子标签，建立标签层级关系
- **灵活关联**：案例可作为父节点，实现案例与标签的双向关联
- **搜索集成**：搜索时可叠加标签条件，精准定位

### 💡 元概念管理
- **概念提取**：从任意网页URL提取设计概念（不限于建筑网站）
- **轻量级实体**：概念只需名称、关键词、描述，比案例更灵活
- **图谱集成**：概念节点同样显示在知识图谱中，与案例建立关联

### 🌌 星云分组
- **分组管理**：创建星云（Nebula）来组织案例和概念
- **多对多关系**：每个案例/概念可以同时属于多个星云
- **可视化状态**：激活星云时只显示其内容，其他星云收起显示
- **关联分析**：星云之间根据共享案例/概念数量显示连接强度

### 📊 数据管理
- **数据导出**：支持导出为 JSON（完整数据）、CSV（案例表格）、GraphML（图谱格式）
- **数据导入**：支持从 JSON 文件导入，可选择追加或替换模式
- **版本历史**：自动记录操作历史，支持撤销/重做
- **快照功能**：创建数据快照，随时恢复到历史状态
- **数据库支持**：可选使用 SQLite 数据库（默认使用 JSON 文件）

## 🚀 快速开始

### 1. 安装依赖

```bash
cd archgraph
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

支持 OpenAI / DeepSeek / 硅基流动 / 任何 OpenAI 兼容 API。推荐用 DeepSeek，性价比高。

**图像生成配置**（可选）：
- 使用 OpenAI DALL-E：设置 `IMAGE_GENERATION_PROVIDER=openai`（默认）
- 使用豆包图像生成：设置 `IMAGE_GENERATION_PROVIDER=doubao`，并配置 `DOUBAO_IMAGE_API_KEY` 和 `DOUBAO_IMAGE_API_URL`
- 禁用图像生成：设置 `ENABLE_IMAGE_GENERATION=false`

### 3. 启动

```bash
# Linux / Mac
export $(cat .env | xargs) && uvicorn app:app --reload --port 8000

# Windows PowerShell
Get-Content .env | ForEach-Object { if ($_ -match '^([^#].+?)=(.+)$') { [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2]) } }
uvicorn app:app --reload --port 8000
```

打开浏览器访问 http://localhost:8000

## 📁 项目结构

```
archgraph/
├── app.py                  # FastAPI 后端（案例CRUD / URL导入 / AI搜索 / 图谱API）
├── static/
│   ├── index.html          # 前端（D3知识图谱 + 交互界面）
│   └── uploads/            # 上传的图片文件
├── seed_data.json          # 预置12个经典建筑案例（种子数据）
├── data.json               # 运行时数据（自动生成）
├── tags.json               # 标签数据
├── concepts.json           # 元概念数据
├── nebulas.json            # 星云数据
├── history.json            # 版本历史
├── snapshots/              # 快照目录
├── archgraph.db            # SQLite数据库（可选）
├── requirements.txt        # Python依赖
├── .env.example            # API 配置模板
├── README.md               # 项目说明
└── USER_GUIDE.md           # 用户操作手册
```

## 🛠️ 技术栈

| 层 | 技术 | 说明 |
|---|------|------|
| **后端** | FastAPI + Python 3.10+ | RESTful API，异步HTTP请求 |
| **前端** | Vanilla JS + D3.js | 无框架依赖，D3.js 力导向图可视化 |
| **AI集成** | OpenAI 兼容 API | 支持 GPT / DeepSeek / 豆包 / Qwen 等 |
| **数据爬取** | httpx + BeautifulSoup | 智能内容提取，反爬虫处理 |
| **数据存储** | JSON / SQLite | 默认JSON，可选SQLite数据库 |
| **性能优化** | 内存缓存 | 图谱数据5秒TTL缓存机制 |
| **UI/UX** | CSS Variables | 支持主题切换，响应式设计 |

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd archgraph
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

**必需配置**：
- `LLM_API_KEY`: LLM API密钥
- `LLM_BASE_URL`: API基础URL（如 `https://api.openai.com/v1`）
- `LLM_MODEL`: 模型名称（如 `gpt-4o-mini`）

**可选配置**：
- `USE_DATABASE=true`: 启用SQLite数据库（默认false使用JSON）
- `ENABLE_IMAGE_GENERATION=true`: 启用图像生成
- `IMAGE_GENERATION_PROVIDER`: 图像生成提供商（openai/doubao）

### 4. 启动服务

```bash
# Linux / Mac
export $(cat .env | xargs) && uvicorn app:app --reload --port 8000

# Windows PowerShell
Get-Content .env | ForEach-Object { if ($_ -match '^([^#].+?)=(.+)$') { [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2]) } }
uvicorn app:app --reload --port 8000
```

### 5. 访问应用

打开浏览器访问 http://localhost:8000

首次启动会自动加载12个预置案例，并创建"示范案例"星云。

## 📖 使用文档

详细的使用说明请参考 [用户操作手册](USER_GUIDE.md)

## 🎯 项目亮点

- ✅ **全栈开发**：FastAPI后端 + D3.js前端，完整的产品级应用
- ✅ **AI深度集成**：LLM用于内容提取、灵感搜索、方案融合等核心功能
- ✅ **数据可视化**：交互式知识图谱，直观展示复杂关联关系
- ✅ **工程实践**：错误处理、缓存优化、数据导入导出、版本历史等
- ✅ **用户体验**：主题切换、搜索过滤、拖拽交互等细节优化
- ✅ **可扩展性**：支持SQLite数据库，代码结构清晰，便于扩展

## 🔧 开发说明

### API端点

- `GET /api/cases` - 获取所有案例
- `POST /api/cases` - 创建案例
- `GET /api/graph` - 获取图谱数据
- `POST /api/search` - AI灵感搜索
- `POST /api/import-url` - 从URL导入案例
- `GET /api/export/json` - 导出JSON数据
- `POST /api/snapshots` - 创建快照
- 更多API请参考 `app.py`

### 数据模型

- **案例（Case）**：项目名称、建筑师、年份、地点、标签、描述、图片、来源
- **概念（Concept）**：概念名称、关键词、描述、图片、来源
- **标签（Tag）**：标签名称、父标签、子标签、关联案例
- **星云（Nebula）**：星云名称、包含的案例和概念ID列表

## 📸 功能演示

> 启动后即可看到预置的12个经典建筑案例组成的知识图谱

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📜 License

MIT
