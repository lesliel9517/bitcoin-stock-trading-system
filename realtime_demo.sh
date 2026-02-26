#!/bin/bash

# Real-time Trading Visualization Demo

echo "🚀 启动实时交易可视化演示..."
echo ""
echo "提示: 浏览器将自动打开显示实时图表"
echo ""

# Create necessary directories
mkdir -p data/realtime

# Run the demo
source .venv/bin/activate && python examples/realtime_demo.py

echo ""
echo "✅ 演示完成!"
echo ""
