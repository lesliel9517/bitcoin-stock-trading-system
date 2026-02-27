# Bitcoin & Stock Trading System

专业的实时量化交易系统，支持加密货币交易，配备实时可视化仪表盘。

## 核心功能

- **实时交易仪表盘**: 专业级可视化界面，实时显示价格走势、持仓、盈亏
- **策略回测**: 历史数据回测，性能分析
- **纸上交易**: 真实市场数据，虚拟资金测试
- **模拟交易**: 虚拟数据快速测试
- **风险管理**: 止损止盈、仓位管理

## 快速开始

```bash
# 安装
git clone https://github.com/lesliel9517/bitcoin-stock-trading-system.git
cd bitcoin-stock-trading-system
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

# 配置（可选）
cp .env.example .env

# 运行
btc-trade trade start --mode paper --dashboard        # 纸上交易（推荐）
btc-trade trade start --mode simulation --dashboard   # 模拟交易
```

## CLI 命令

```bash
# 交易
btc-trade trade start --mode paper --dashboard
btc-trade trade start --mode paper --capital 50000 --ma-short 5 --ma-long 20

# 回测
btc-trade backtest start --strategy ma_cross --symbol BTC-USD --start 2024-01-01 --end 2024-12-31
```

## 内置策略

- **MA Cross**: 均线交叉策略，适合趋势市场
- **Adaptive**: 自适应策略，动态调整参数和止损止盈

## 注意事项

⚠️ **重要**:
- 测试优先：始终先在模拟/纸上交易环境测试
- 风险控制：严格遵守风控规则，设置止损
- API安全：妥善保管API密钥

## 许可证

MIT License

## 相关文档

- [CLAUDE.md](CLAUDE.md) - 开发者指南和架构说明
