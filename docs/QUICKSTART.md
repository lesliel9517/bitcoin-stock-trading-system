# Quick Start Guide

## 快速开始

### 1. 安装依赖

```bash
cd bitcoin-stock-trading-system

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 或者安装为包
pip install -e .
```

### 2. 下载示例数据

```bash
# 下载模拟的市场数据
python scripts/download_data.py
```

### 3. 运行快速示例

```bash
# 运行快速开始示例
python scripts/quick_start.py
```

### 4. 使用CLI命令

```bash
# 查看帮助
btc-trade --help

# 运行回测
btc-trade backtest start \
  --strategy ma_cross \
  --symbol BTC-USD \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --capital 100000

# 查看版本
btc-trade version
```

## 项目结构

```
bitcoin-stock-trading-system/
├── config/              # 配置文件
│   ├── system.yaml     # 系统配置
│   ├── exchanges.yaml  # 交易所配置
│   ├── risk.yaml       # 风控配置
│   └── strategies/     # 策略配置
│       └── ma_cross.yaml
│
├── src/                # 源代码
│   ├── core/          # 核心引擎（事件系统）
│   ├── data/          # 数据模块
│   ├── strategies/    # 策略模块
│   ├── trading/       # 交易模块
│   ├── risk/          # 风控模块
│   ├── monitor/       # 监控模块
│   ├── backtest/      # 回测模块
│   ├── cli/           # 命令行接口
│   └── utils/         # 工具模块
│
├── scripts/           # 辅助脚本
│   ├── download_data.py   # 下载数据
│   └── quick_start.py     # 快速开始
│
├── data/              # 数据存储
│   ├── db/           # 数据库文件
│   ├── logs/         # 日志文件
│   └── backtest/     # 回测结果
│
└── tests/            # 测试
```

## 核心功能

### 1. 回测系统

```python
from src.backtest.engine import BacktestEngine
from src.strategies.examples.ma_cross import MACrossStrategy

# 创建策略
strategy = MACrossStrategy(strategy_id='test', config={
    'parameters': {'short_window': 5, 'long_window': 20}
})

# 创建回测引擎
engine = BacktestEngine(initial_capital=100000)
engine.set_strategy(strategy)

# 运行回测
results = await engine.run(data, symbol='BTC-USD')
```

### 2. 策略开发

```python
from src.strategies.base import Strategy

class MyStrategy(Strategy):
    def on_init(self):
        # 初始化策略
        pass

    async def on_market_data(self, event):
        # 处理行情数据
        # 生成交易信号
        return self.generate_signal(...)

    def calculate_indicators(self, data):
        # 计算技术指标
        return data
```

### 3. 数据管理

```python
from src.data.storage import DataStorage

storage = DataStorage()

# 保存数据
storage.save_ohlcv(df, symbol='BTC-USD', exchange='binance', timeframe='1d')

# 加载数据
data = storage.load_ohlcv(symbol='BTC-USD', exchange='binance', timeframe='1d')
```

## 配置说明

### 系统配置 (config/system.yaml)

```yaml
system:
  mode: simulation  # simulation | live
  log_level: INFO
  data_dir: ./data
```

### 策略配置 (config/strategies/ma_cross.yaml)

```yaml
strategy:
  name: ma_cross
  class: MACrossStrategy

parameters:
  short_window: 5
  long_window: 20

symbols:
  - BTC-USD
  - ETH-USD
```

### 风控配置 (config/risk.yaml)

```yaml
risk:
  max_position_size: 0.1      # 单个持仓最大占比10%
  max_drawdown: 0.2           # 最大回撤20%
  max_daily_loss: 0.05        # 每日最大亏损5%
```

## 下一步

### Phase 2: 实时交易（即将推出）
- 交易所API集成（币安、OKX、Alpaca）
- WebSocket实时行情
- 订单执行引擎
- 模拟交易模式

### Phase 3: 风险管理（即将推出）
- 动态止损止盈
- 仓位管理
- 风险评估

### Phase 4: 监控告警（即将推出）
- 实时监控面板
- 邮件/Telegram告警
- 性能追踪

## 常见问题

**Q: 如何添加新的策略？**

A: 继承 `Strategy` 基类并实现必要的方法，参考 `src/strategies/examples/ma_cross.py`

**Q: 如何获取真实市场数据？**

A: Phase 2 将集成真实的交易所API，目前使用模拟数据进行测试

**Q: 系统支持哪些市场？**

A: 设计支持加密货币、美股和A股，Phase 2 将实现完整的市场接入

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
