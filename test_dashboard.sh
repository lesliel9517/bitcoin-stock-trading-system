#!/bin/bash
# Test dashboard with real Binance data

echo "测试实时交易仪表盘..."
echo "默认配置："
echo "  - 模式: paper (真实 Binance 数据)"
echo "  - 初始资金: $100,000"
echo "  - 交易标的: BTCUSDT"
echo "  - 策略: 自适应策略 (MA 10/30)"
echo ""
echo "按 Ctrl+C 停止"
echo ""

# Run with default settings (paper mode with real data)
python3 examples/professional_realtime.py
