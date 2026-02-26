# Bitcoin & Stock Trading System

一个功能完整的实时量化交易系统，支持加密货币、美股和A股市场。

## 特性

- ✅ **实时交易执行**: 支持币安、OKX、Alpaca等交易所
- ✅ **策略回测优化**: 历史数据回测、参数优化、性能分析
- ✅ **实时监控告警**: 价格监控、信号提醒、多渠道告警
- ✅ **风险管理系统**: 止损止盈、仓位管理、风险评估
- ✅ **命令行交互**: 简洁的CLI界面

## 系统架构

```
CLI Layer (命令行接口)
    ↓
Application Layer (策略管理、回测引擎、交易协调)
    ↓
Core Engine Layer (事件总线、策略引擎、订单管理、风险管理)
    ↓
Service Layer (市场数据、交易所网关、持仓管理、告警服务)
    ↓
Infrastructure Layer (数据库、缓存、日志、配置)
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 或者安装为包
pip install -e .
```

### 2. 配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的API密钥
vim .env
```

### 3. 运行回测

```bash
# 运行均线交叉策略回测
btc-trade backtest start --strategy ma_cross --symbol BTC-USD --start 2024-01-01 --end 2024-12-31

# 查看回测结果
btc-trade backtest report --id <backtest_id>
```

### 4. 启动模拟交易

```bash
# 启动模拟交易
btc-trade trade start --strategy ma_cross --symbol BTC-USD --mode simulation

# 查看持仓
btc-trade trade positions

# 查看订单
btc-trade trade orders
```

## CLI 命令

### 回测命令

```bash
btc-trade backtest start --strategy ma_cross --symbol BTC-USD --start 2024-01-01
btc-trade backtest list
btc-trade backtest report --id <backtest_id>
```

### 交易命令

```bash
btc-trade trade start --strategy ma_cross --mode simulation
btc-trade trade stop
btc-trade trade status
btc-trade trade positions
btc-trade trade orders
```

### 策略命令

```bash
btc-trade strategy list
btc-trade strategy info --name ma_cross
btc-trade strategy optimize --name ma_cross --symbol BTC-USD
```

### 监控命令

```bash
btc-trade monitor start
btc-trade monitor dashboard
btc-trade monitor metrics
```

### 数据命令

```bash
btc-trade data download --symbol BTC-USD --start 2024-01-01
btc-trade data list
```

## 支持的市场

- **加密货币**: BTC, ETH, 等（通过币安、OKX）
- **美股**: AAPL, TSLA, 等（通过Alpaca）
- **A股**: 上证、深证指数和个股（通过AKShare）

## 内置策略

- **均线交叉策略** (MA Cross): 基于短期和长期移动平均线的交叉信号
- **网格交易策略** (Grid Trading): 在价格区间内自动买卖
- **套利策略** (Arbitrage): 跨交易所价差套利
- **均值回归策略** (Mean Reversion): 基于价格偏离均值的交易

## 风险管理

系统内置多层风险控制：

- **仓位限制**: 单个持仓最大占比控制
- **止损止盈**: 自动止损和止盈机制
- **回撤控制**: 最大回撤限制
- **每日限额**: 每日最大亏损和订单数限制

## 项目结构

```
bitcoin-stock-trading-system/
├── config/              # 配置文件
├── src/
│   ├── core/           # 核心引擎
│   ├── data/           # 数据模块
│   ├── strategies/     # 策略模块
│   ├── trading/        # 交易模块
│   ├── risk/           # 风控模块
│   ├── monitor/        # 监控模块
│   ├── backtest/       # 回测模块
│   └── cli/            # 命令行接口
├── tests/              # 测试
├── docs/               # 文档
└── data/               # 数据存储
```

## 开发

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_core/

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 代码格式化

```bash
# 格式化代码
black src/ tests/

# 检查代码风格
flake8 src/ tests/

# 类型检查
mypy src/
```

## 注意事项

⚠️ **重要提示**:

1. **测试优先**: 始终先在模拟环境测试策略
2. **小额验证**: 实盘交易从小资金开始
3. **风险控制**: 严格遵守风控规则
4. **API限制**: 注意交易所API频率限制
5. **数据安全**: 妥善保管API密钥

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

- GitHub: [your-github-username]
- Email: your.email@example.com
