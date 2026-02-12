# ArchGraph 部署指南

本指南将帮助你：
1. 将项目上传到 GitHub
2. 部署在线 Demo（推荐多个平台）

---

## 📤 第一步：上传到 GitHub

### 1.1 准备工作

#### 检查敏感信息

确保 `.gitignore` 已正确配置，不会上传敏感信息：

```bash
# 检查 .gitignore 是否包含以下内容
cat .gitignore
```

应该包含：
- `.env`（包含API密钥）
- `data.json`（运行时数据）
- `*.db`（数据库文件）
- `static/uploads/*`（上传的文件）

#### 创建 .env.example

如果还没有 `.env.example` 文件，请创建它（已包含在项目中）。

### 1.2 初始化 Git 仓库

```bash
# 进入项目目录
cd archgraph

# 初始化 Git（如果还没有）
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: ArchGraph - 建筑灵感知识图谱系统"
```

### 1.3 创建 GitHub 仓库

1. 登录 [GitHub](https://github.com)
2. 点击右上角 "+" → "New repository"
3. 填写仓库信息：
   - **Repository name**: `archgraph`（或你喜欢的名字）
   - **Description**: `建筑灵感知识图谱系统 - 用AI和知识图谱管理建筑案例`
   - **Visibility**: Public（公开，方便展示）
   - **不要**勾选 "Initialize with README"（我们已经有了）
4. 点击 "Create repository"

### 1.4 推送代码

```bash
# 添加远程仓库（替换 YOUR_USERNAME 为你的GitHub用户名）
git remote add origin https://github.com/YOUR_USERNAME/archgraph.git

# 推送代码
git branch -M main
git push -u origin main
```

### 1.5 添加仓库描述和标签

在 GitHub 仓库页面：
1. 点击 "Settings" → "General"
2. 添加 Topics（标签）：
   - `python`
   - `fastapi`
   - `d3js`
   - `knowledge-graph`
   - `ai`
   - `architecture`
   - `data-visualization`

---

## 🚀 第二步：部署在线 Demo

### 方案一：Railway（推荐，最简单）

Railway 提供免费额度，部署简单。

#### 步骤：

1. **注册 Railway**
   - 访问 [railway.app](https://railway.app)
   - 使用 GitHub 账号登录

2. **创建新项目**
   - 点击 "New Project"
   - 选择 "Deploy from GitHub repo"
   - 选择你的 `archgraph` 仓库

3. **配置环境变量**
   - 在项目设置中找到 "Variables"
   - 添加以下环境变量：
     ```
     LLM_API_KEY=your-api-key
     LLM_BASE_URL=https://api.deepseek.com
     LLM_MODEL=deepseek-chat
     ENABLE_IMAGE_GENERATION=false
     ```
   - **注意**：不要使用生产环境的API密钥，建议创建专门的测试密钥

4. **部署**
   - Railway 会自动检测 `requirements.txt` 并部署
   - 等待部署完成（约2-3分钟）

5. **获取访问链接**
   - 部署完成后，Railway 会提供一个 `*.railway.app` 域名
   - 点击 "Settings" → "Generate Domain" 可以自定义域名

#### 创建 `railway.json`（可选）

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn app:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

### 方案二：Render（推荐，免费）

Render 提供免费层，适合静态和动态网站。

#### 步骤：

1. **注册 Render**
   - 访问 [render.com](https://render.com)
   - 使用 GitHub 账号登录

2. **创建 Web Service**
   - 点击 "New" → "Web Service"
   - 连接你的 GitHub 仓库

3. **配置服务**
   - **Name**: `archgraph`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`

4. **配置环境变量**
   - 在 "Environment" 标签页添加环境变量（同Railway）

5. **部署**
   - 点击 "Create Web Service"
   - 等待部署完成

---

### 方案三：Fly.io（推荐，全球CDN）

Fly.io 提供全球CDN，访问速度快。

#### 步骤：

1. **安装 Fly CLI**
   ```bash
   # Windows (PowerShell)
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   
   # Mac/Linux
   curl -L https://fly.io/install.sh | sh
   ```

2. **登录 Fly.io**
   ```bash
   fly auth login
   ```

3. **创建应用**
   ```bash
   fly launch
   ```
   按提示操作，选择区域（推荐选择离你最近的）

4. **配置环境变量**
   ```bash
   fly secrets set LLM_API_KEY=your-api-key
   fly secrets set LLM_BASE_URL=https://api.deepseek.com
   fly secrets set LLM_MODEL=deepseek-chat
   ```

5. **部署**
   ```bash
   fly deploy
   ```

#### 创建 `fly.toml`（自动生成，但可以自定义）

```toml
app = "archgraph"
primary_region = "hkg"  # 香港，可选其他区域

[build]

[env]
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
```

---

### 方案四：Vercel（仅前端，需要后端分离）

Vercel 主要适合前端，如果要用需要将前后端分离。

**不推荐**：当前项目是前后端一体的，Vercel 部署需要额外配置。

---

## 🔧 部署配置优化

### 创建 `Procfile`（用于某些平台）

```procfile
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

### 创建 `runtime.txt`（指定Python版本）

```
python-3.10.12
```

### 更新 `requirements.txt`（确保包含所有依赖）

```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
httpx>=0.25.0
beautifulsoup4>=4.12.0
openai>=1.6.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

---

## ⚠️ 部署注意事项

### 1. API 密钥安全

- ✅ **不要**在代码中硬编码 API 密钥
- ✅ **使用**环境变量存储敏感信息
- ✅ **创建**专门的测试 API 密钥用于 Demo
- ✅ **设置**API 密钥的使用限额

### 2. 静态文件处理

- 上传的文件存储在 `static/uploads/`，部署时可能需要配置持久化存储
- 考虑使用云存储（如 AWS S3、Cloudinary）存储上传的图片

### 3. 数据库选择

- 默认使用 JSON 文件存储，适合 Demo
- 生产环境建议使用 SQLite 或 PostgreSQL
- 设置 `USE_DATABASE=true` 启用数据库

### 4. 性能优化

- 部署平台通常有资源限制
- 考虑添加请求限流
- 优化图片加载（压缩、CDN）

### 5. CORS 配置（如果需要）

如果前端和后端分离部署，需要在 `app.py` 中添加 CORS：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📝 部署后检查清单

- [ ] 环境变量已正确配置
- [ ] API 密钥可以正常调用
- [ ] 网站可以正常访问
- [ ] 图谱可以正常加载
- [ ] AI 搜索功能正常
- [ ] 文件上传功能正常（如果使用）
- [ ] HTTPS 已启用
- [ ] 自定义域名已配置（可选）

---

## 🔗 推荐部署平台对比

| 平台 | 免费额度 | 部署难度 | 推荐度 | 备注 |
|------|---------|---------|--------|------|
| **Railway** | 500小时/月 | ⭐ 简单 | ⭐⭐⭐⭐⭐ | 最简单，自动检测配置 |
| **Render** | 750小时/月 | ⭐⭐ 中等 | ⭐⭐⭐⭐ | 稳定，适合长期运行 |
| **Fly.io** | 3个VM免费 | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐ | 全球CDN，速度快 |
| **Heroku** | 无免费层 | ⭐⭐ 中等 | ⭐⭐ | 已取消免费层 |

**推荐顺序**：Railway > Render > Fly.io

---

## 🎯 快速开始（Railway 示例）

```bash
# 1. 确保代码已推送到 GitHub
git push origin main

# 2. 访问 railway.app，用 GitHub 登录
# 3. 点击 "New Project" → "Deploy from GitHub repo"
# 4. 选择 archgraph 仓库
# 5. 在 Variables 中添加环境变量
# 6. 等待部署完成
# 7. 获取访问链接，分享给面试官！
```

---

## 📸 部署成功后

1. **更新 README**：在 README 中添加在线 Demo 链接
2. **更新简历**：在项目描述中添加 Demo 链接
3. **录制演示视频**：展示在线 Demo 的使用流程

---

**祝部署顺利！** 🚀
