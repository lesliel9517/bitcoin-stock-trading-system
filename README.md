# Bitcoin & Stock Trading System

一个专业的实时量化交易系统，支持加密货币交易，配备实时可视化仪表盘。

## 核心功能

- ✅ **实时交易仪表盘**: 专业级可视化界面，实时显示价格走势、持仓、盈亏
- ✅ **策略回测**: 历史数据回测，性能分析
- ✅ **纸上交易**: 使用真实市场数据进行虚拟交易测试
- ✅ **模拟交易**: 使用模拟数据快速测试策略
- ✅ **风险管理**: 止损止盈、仓位管理、风险控制

## 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/lesliel9517/bitcoin-stock-trading-system.git
cd bitcoin-stock-trading-system

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
pip install -e .
```

### 2. 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件（可选，纸上交易需要Binance API）
# BINANCE_API_KEY=your_api_key
# BINANCE_API_SECRET=your_api_secret
```

### 3. 运行

```bash
# 纸上交易（推荐）- 真实Binance数据，虚拟资金
btc-trade trade start --mode paper --dashboard

# 模拟交易 - 虚拟数据，快速测试
btc-trade trade start --mode simulation --dashboard

# 策略回测
btc-trade backtest start --strategy ma_cross --symbol BTC-USD --start 2024-01-01 --end 2024-12-31
```

## 实时仪表盘

专业级实时交易仪表盘，提供：

- **价格走势图**: 实时折线图，显示价格变化和涨跌幅
- **账户信息**: 总资产、现金余额、盈亏统计
- **持仓信息**: 当前持仓、成本价、浮动盈亏
- **交易记录**: 买入卖出历史，盈亏明细
- **市场状态**: 趋势判断、波动率监控
- **实时日志**: 所有交易事件实时显示

### 仪表盘特性

- Y轴显示价格和涨跌幅（基于当日0点价格）
- 买入/卖出标记在价格图上
- 账户信息实时更新（买入扣现金，卖出加现金）
- 完全静默模式（无终端日志干扰）

## CLI 命令

### 交易命令

```bash
# 启动交易（带仪表盘）
btc-trade trade start --mode paper --dashboard

# 启动交易（纯文本日志）
btc-trade trade start --mode paper --no-dashboard

# 自定义参数
btc-trade trade start --mode paper --capital 50000 --ma-short 5 --ma-long 20 --dashboard

# 模拟交易（指定时长）
btc-trade trade start --mode simulation --duration 60 --dashboard
```

### 回测命令

```bash
# 运行回测
btc-trade backtest start --strategy ma_cross --symbol BTC-USD --start 2024-01-01 --end 2024-12-31

# 保存回测结果
btc-trade backtest start --strategy ma_cross --symbol BTC-USD --start 2024-01-01 --end 2024-12-31 --output results.csv
```

## 内置策略

### 1. MA Cross Strategy (均线交叉)
- 短期均线（默认10）和长期均线（默认30）交叉信号
- 适合趋势市场

### 2. Adaptive Strategy (自适应策略)
- 自动检测市场状态（上涨/下跌/震荡）
- 动态调整参数和止损止盈
- 根据波动率调整仓位

## 项目结构

```
bitcoin-stock-trading-system/
├── src/
│   ├── cli/              # CLI命令行接口
│   │   ├── commands/     # 命令实现
│   │   └── dashboard/    # 实时仪表盘
│   ├── core/             # 核心引擎（事件总线、交易引擎）
│   ├── strategies/       # 交易策略
│   ├── trading/          # 交易模块（订单、持仓、交易所）
│   ├── data/             # 数据模块（市场数据、数据源）
│   ├── risk/             # 风险管理
│   ├── backtest/         # 回测引擎
│   └── utils/            # 工具函数
├── config/               # 配置文件
├── tests/                # 测试
└── data/                 # 数据存储
    ├── db/              # 数据库
    └── logs/            # 日志文件
```

## 技术架构

```
CLI Layer (命令行接口)
    ↓
Application Layer (策略管理、回测协调)
    ↓
Core Engine Layer (事件总线、交易引擎、订单管理、风险管理)
    ↓
Service Layer (市场数据、交易所网关、持仓管理)
    ↓
Infrastructure Layer (数据库、日志、配置)
```

## 支持的交易所

- **Binance**: 纸上交易（真实数据）
- **模拟交易所**: 快速测试

## 开发

### 代码格式化

```bash
# 格式化代码
black src/ tests/

# 检查代码风格
flake8 src/ tests/

# 类型检查
mypy src/
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_core/

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

## 注意事项

⚠️ **重要提示**:

1. **测试优先**: 始终先在模拟/纸上交易环境测试策略
2. **风险控制**: 严格遵守风控规则，设置止损
3. **API安全**: 妥善保管API密钥，不要提交到代码仓库
4. **数据质量**: 确保市场数据源稳定可靠
5. **日志监控**: 定期检查 `./data/logs/` 目录下的日志文件

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 相关文档

- [CLAUDE.md](CLAUDE.md) - 开发者指南和架构说明
