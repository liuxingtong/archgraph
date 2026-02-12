# 🏛️ ArchGraph · 建筑灵感知识图谱

**用可交互知识图谱管理你的建筑灵感，用 AI 拓展你的设计视野。**

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-yellow)
![D3.js](https://img.shields.io/badge/D3.js-v7-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

> 🎯 **项目定位**：一个集 AI 能力与数据可视化于一体的全栈应用，展示全栈开发、AI 集成、数据可视化等综合能力。

> 🌐 **在线 Demo**：[点击体验](https://web-production-c31fd.up.railway.app/) | 📚 [用户手册](USER_GUIDE.md)

---

## ✨ 核心功能

### 📌 案例管理

- **手动添加**：录入名称、建筑师、年份、地点、标签、设计描述等完整信息
- **URL 智能导入**：粘贴 ArchDaily / 谷德 / gooood 等链接，AI 自动爬取网页内容并提取结构化建筑信息（名称、建筑师、年份、地点、标签、描述），同时自动抓取代表性图片并下载到本地
- **图片上传**：支持 JPG / PNG / WebP / GIF 格式的本地图片上传，并可直接关联到指定案例
- **批量数据管理**：支持导入导出 JSON（完整数据）、CSV（案例表格）、GraphML（图谱格式，可用于 Gephi 等工具）
<img src="assets/1.png" width="1000" alt="url抓取案例">

### 🕸️ 交互式知识图谱

- **D3.js 力导向图**：案例、标签、概念、星云节点自动生成关联关系网络
- **多类型边关系**：案例—标签（`case_tag`）、标签层级（`tag_hierarchy`）、案例—子标签（`case_subtag`）、星云—案例/概念（`nebula_case` / `nebula_concept`）、星云互联（`nebula_link`，根据共享内容数量计算权重）
- **星云视图切换**：激活某个星云时，只展开该星云内的案例和概念节点，其他星云自动收起
- **性能优化**：图谱数据内置 5 秒 TTL 内存缓存，数据变更时自动失效

### 🧬 方案融合（Hybridize）

这是核心差异化功能——模拟建筑师从不同参考案例中提取设计片段并重组的思维过程：

- 选中 2–4 个案例，选择要融合的设计维度：手法 / 场地处理 / 概念 / 技术 / 形式 / 结构（也支持自定义维度）
- 支持**逐案例指定维度**：每个案例可以只贡献特定维度，而非全部维度
- AI 从每个案例中提取对应维度的"设计 DNA"，重组为全新方案构想
- 生成内容包括：维度精华提取、概念名称与叙述、组合逻辑、落地场景建议、张力与潜力分析
- **效果图生成**（可选）：自动生成英文图像提示词，调用 DALL-E 或豆包 API 生成建筑效果图

### 🔍 AI 灵感搜索

- **自然语言查询**：用自然语言描述设计需求（如"滨水社区，低成本改造，社区参与"）
- **智能匹配**：AI 从已有知识图谱中匹配关联案例，并解释关联逻辑
- **新案例推荐**：推荐图谱中没有的新案例，可一键添加到图谱
- **联网搜索增强**：使用火山方舟（Volcengine）API 时，自动启用联网搜索模式，推荐真实可查的建筑案例并附带来源 URL
- **设计策略与概念拓展**：生成具体可操作的设计策略建议，推荐可继续深挖的概念方向

### 🏷️ 标签系统

- **层级结构**：支持父标签—子标签层级关系，标签可挂载在其他标签或案例节点下
- **多父节点**：一个标签可以同时拥有多个父节点（标签或案例），形成桥接关系
- **自动同步**：创建或编辑案例时，自动将案例中的标签名同步注册到标签库；也提供手动全量同步接口
- **安全删除**：删除标签时检查是否有子标签或被案例引用，防止数据不一致

### 💡 元概念管理

- **URL 概念提取**：从任意网页 URL 提取设计概念（不限于建筑网站），AI 自动归纳概念名称、关键词和描述
- **轻量级实体**：概念只需名称、关键词、描述，比案例更灵活，适合记录抽象的设计理念
- **图谱集成**：概念节点同样显示在知识图谱中，可被星云收纳和管理

### 🌌 星云分组（Nebula）

- **分组管理**：创建星云来组织相关的案例和概念
- **多对多关系**：每个案例/概念可以同时属于多个星云
- **可视化联动**：激活星云时只展开其内容，未激活的星云在图谱中显示为收起状态
- **关联分析**：星云之间根据共享案例/概念数量自动生成连接边，权重反映关联强度

### 📊 版本控制与数据管理

- **操作历史**：自动记录每次创建、编辑、删除、导入操作的前置快照（最多保留 100 条记录，撤销栈最大 50 层）
- **撤销/重做**：基于快照栈实现完整的 undo/redo 功能
- **手动快照**：可随时创建命名快照，支持列出、恢复、删除
- **数据导入**：JSON 导入支持"追加"或"替换"两种模式，追加模式自动跳过已有 ID 的记录

---

## 🛠️ 技术栈

| 层 | 技术 | 说明 |
|---|------|------|
| **后端** | FastAPI + Python 3.10+ | RESTful API，支持异步端点（URL 导入 / 图片下载 / 图像生成） |
| **前端** | Vanilla JS + D3.js v7 | 无框架依赖，D3 力导向图可视化 |
| **AI 集成** | OpenAI 兼容 API | 支持 GPT / DeepSeek / 豆包 / Qwen 等；火山方舟自动启用联网搜索 |
| **图像生成** | DALL-E / 豆包 Seedream | 方案融合时可选生成建筑效果图 |
| **数据爬取** | httpx + BeautifulSoup | 异步 HTTP，智能图片提取（OG / Twitter Card / 文章主图 / 大图 fallback），反爬处理 |
| **数据存储** | JSON 文件 / SQLite（可选） | 默认 JSON 零配置启动，可切换 SQLite |
| **性能优化** | 内存缓存 | 图谱数据 5 秒 TTL 缓存，写操作自动失效 |

---

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

**必需配置：**

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_API_KEY` | LLM API 密钥 | `sk-xxx` |
| `LLM_BASE_URL` | API 基础 URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-4o-mini` |

**可选配置：**

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `USE_DATABASE` | `false` | 设为 `true` 启用 SQLite 数据库 |
| `ENABLE_IMAGE_GENERATION` | `true` | 是否在方案融合时生成效果图 |
| `IMAGE_GENERATION_PROVIDER` | `openai` | 图像生成提供商：`openai`（DALL-E）或 `doubao` |
| `DOUBAO_IMAGE_API_KEY` | — | 豆包图像 API 密钥（仅 `doubao` 模式需要） |
| `DOUBAO_IMAGE_API_URL` | 火山方舟默认地址 | 豆包图像 API 地址 |

支持 OpenAI / DeepSeek / 硅基流动 / 火山方舟 / 任何 OpenAI 兼容 API。推荐用 DeepSeek，性价比高。使用火山方舟 API 时，AI 搜索自动切换为联网搜索模式。

### 4. 启动服务

```bash
# Linux / Mac
export $(cat .env | xargs) && uvicorn app:app --reload --port 8000

# Windows PowerShell
Get-Content .env | ForEach-Object {
  if ($_ -match '^([^#].+?)=(.+)$') {
    [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
  }
}
uvicorn app:app --reload --port 8000
```

### 5. 访问应用

打开浏览器访问 http://localhost:8000

首次启动会自动加载预置的种子案例，并创建"示范案例"星云。

---

## 📁 项目结构

```
archgraph/
├── app.py                  # FastAPI 后端（~1800行，全部后端逻辑）
├── static/
│   ├── index.html          # 前端（D3 知识图谱 + 交互界面）
│   └── uploads/            # 上传 & 爬取的图片文件
├── seed_data.json          # 预置经典建筑案例（种子数据）
├── data.json               # 案例运行时数据（自动生成）
├── tags.json               # 标签数据（自动生成）
├── concepts.json           # 元概念数据（自动生成）
├── nebulas.json            # 星云数据（自动生成）
├── history.json            # 操作历史 & 撤销/重做栈
├── snapshots/              # 手动快照目录
├── archgraph.db            # SQLite 数据库（仅 USE_DATABASE=true 时生成）
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量配置模板
├── README.md
└── USER_GUIDE.md           # 用户操作手册
```

---

## 🔧 API 参考

### 案例管理

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/cases` | 获取所有案例 |
| `POST` | `/api/cases` | 创建案例 |
| `PUT` | `/api/cases/{case_id}` | 更新案例 |
| `DELETE` | `/api/cases/{case_id}` | 删除案例 |
| `POST` | `/api/import-url` | 从 URL 智能导入案例 |
| `POST` | `/api/cases/from-suggestion` | 从 AI 推荐结果一键添加案例 |

### 概念管理

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/concepts` | 获取所有概念 |
| `POST` | `/api/concepts` | 创建概念 |
| `PUT` | `/api/concepts/{concept_id}` | 更新概念 |
| `DELETE` | `/api/concepts/{concept_id}` | 删除概念 |
| `POST` | `/api/concepts/from-url` | 从 URL 提取概念 |

### 标签管理

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/tags` | 获取所有标签 |
| `POST` | `/api/tags` | 创建标签（可指定父节点） |
| `PUT` | `/api/tags/{tag_id}` | 更新标签 |
| `DELETE` | `/api/tags/{tag_id}` | 删除标签（需无子标签且未被引用） |
| `POST` | `/api/tags/sync-from-cases` | 从所有案例同步标签到标签库 |

### 星云管理

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/nebulas` | 获取所有星云 |
| `POST` | `/api/nebulas` | 创建星云 |
| `PUT` | `/api/nebulas/{nebula_id}` | 更新星云 |
| `DELETE` | `/api/nebulas/{nebula_id}` | 删除星云 |

### AI 功能

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/search` | AI 灵感搜索（支持标签筛选叠加） |
| `POST` | `/api/hybridize` | 方案融合（含可选效果图生成） |

### 图谱与图片

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/graph` | 获取图谱数据（可选 `?active_nebula_id=xxx` 过滤） |
| `POST` | `/api/upload-image` | 上传图片 |
| `POST` | `/api/upload-image-for-case/{case_id}` | 上传图片并关联到案例 |

### 数据管理

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/export/json` | 导出完整数据（JSON） |
| `GET` | `/api/export/csv` | 导出案例（CSV，UTF-8 BOM） |
| `GET` | `/api/export/graphml` | 导出图谱（GraphML，可用于 Gephi） |
| `POST` | `/api/import/json` | 导入 JSON 数据（支持 append / replace 模式） |

### 版本历史与快照

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/history/undo` | 撤销上一步操作 |
| `POST` | `/api/history/redo` | 重做 |
| `GET` | `/api/snapshots` | 列出所有快照 |
| `POST` | `/api/snapshots` | 创建快照（可选命名） |
| `POST` | `/api/snapshots/{id}/restore` | 恢复快照 |
| `DELETE` | `/api/snapshots/{id}` | 删除快照 |

---

## 🎯 项目亮点

- **全栈开发**：FastAPI 后端 + Vanilla JS / D3.js 前端，约 1800 行后端代码实现完整功能
- **AI 深度集成**：LLM 用于 URL 内容提取、概念归纳、灵感搜索、方案融合四大核心场景，支持多模型多厂商切换
- **数据可视化**：基于 D3.js 力导向图的交互式知识图谱，支持多节点类型（案例、标签、概念、星云）和多种边类型
- **工程实践**：内存缓存、操作历史与撤销重做、快照恢复、数据导入导出（三种格式）、JSON / SQLite 双存储层
- **智能爬取**：多策略图片提取（OG 标签 → Twitter Card → 文章主图 → 尺寸推断 → 关键词匹配），自动下载到本地
- **可扩展设计**：环境变量驱动配置，数据层抽象支持 JSON 和 SQLite 切换，图像生成支持多提供商

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📜 License

MIT