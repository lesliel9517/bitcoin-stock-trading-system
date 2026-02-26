#!/bin/bash

# 快速启动脚本 - Bitcoin & Stock Trading System

set -e

echo "=========================================="
echo "Bitcoin & Stock Trading System"
echo "快速启动脚本"
echo "=========================================="
echo ""

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3"
    echo "请先安装 Python 3.10 或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python 版本: $PYTHON_VERSION"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo ""
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
    echo "✅ 虚拟环境创建成功"
fi

# 激活虚拟环境
echo ""
echo "🔧 激活虚拟环境..."
source .venv/bin/activate

# 安装依赖
echo ""
echo "📥 安装依赖包..."
pip install --upgrade pip > /dev/null 2>&1
pip install -e . > /dev/null 2>&1
echo "✅ 依赖安装完成"

# 检查环境变量
if [ ! -f ".env" ]; then
    echo ""
    echo "⚙️  创建环境配置文件..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件"
    echo "💡 提示: 如需实盘交易，请编辑 .env 文件配置API密钥"
fi

# 创建必要的目录
mkdir -p data/db data/logs

echo ""
echo "=========================================="
echo "✅ 环境配置完成！"
echo "=========================================="
echo ""
echo "🚀 快速开始:"
echo ""
echo "1️⃣  运行回测示例:"
echo "   python3 examples/quick_backtest.py"
echo ""
echo "2️⃣  使用CLI命令:"
echo "   btc-trade backtest start --strategy ma_cross --symbol BTC-USD --start 2024-01-01"
echo ""
echo "3️⃣  查看使用指南:"
echo "   cat README_USAGE.md"
echo ""
echo "=========================================="
