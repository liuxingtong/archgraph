#!/bin/bash
# ArchGraph 一键启动脚本

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 请先安装 Python 3.10+"
    exit 1
fi

# 安装依赖
echo "📦 安装依赖..."
pip install -r requirements.txt -q

# 检查 .env
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，请先配置 API Key："
    echo "   cp .env.example .env"
    echo "   然后编辑 .env 填入你的 API Key"
    exit 1
fi

# 加载环境变量
export $(grep -v '^#' .env | xargs)

# 启动
echo ""
echo "🏛️  ArchGraph 启动中..."
echo "   打开浏览器访问: http://localhost:8000"
echo ""
uvicorn app:app --reload --port 8000
