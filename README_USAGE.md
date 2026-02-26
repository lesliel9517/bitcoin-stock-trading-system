# 使用指南 - Bitcoin & Stock Trading System

## 📖 目录

1. [快速开始](#快速开始)
2. [环境配置](#环境配置)
3. [回测示例](#回测示例)
4. [模拟交易](#模拟交易)
5. [实盘交易](#实盘交易)
6. [策略开发](#策略开发)
7. [常见问题](#常见问题)

## 🚀 快速开始

### 第一步：安装依赖

```bash
# 激活虚拟环境（如果已创建）
source .venv/bin/activate

# 或创建新的虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装项目依赖
pip install -e .
```

### 第二步：配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件（可选，回测不需要API密钥）
vim .env
```

**注意**：如果只是运行回测，不需要配置真实的API密钥。

### 第三步：运行第一个回测

```bash
# 使用内置的均线交叉策略进行回测
btc-trade backtest start \
  --strategy ma_cross \
  --symbol BTC-USD \
  --start 2024-01-01 \
  --end 2024-12-31
```

## ⚙️ 环境配置

### 必需配置

对于**回测**，无需任何API密钥配置。

对于**模拟交易**和**实盘交易**，需要配置相应的交易所API密钥：

#### Binance（币安）

```bash
# .env 文件
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_TESTNET=true  # 使用测试网
```

获取API密钥：
1. 登录 [Binance](https://www.binance.com)
2. 进入 API Management
3. 创建新的API密钥
4. **重要**：首次使用建议启用测试网（BINANCE_TESTNET=true）

#### Alpaca（美股）

```bash
# .env 文件
ALPACA_API_KEY=your_api_key_here
ALPACA_API_SECRET=your_api_secret_here
ALPACA_PAPER=true  # 使用模拟账户
```

获取API密钥：
1. 注册 [Alpaca](https://alpaca.markets)
2. 进入 Paper Trading 获取模拟账户密钥

### 可选配置

#### 告警通知（Telegram）

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

#### 数据库（默认使用SQLite）

```bash
DATABASE_URL=sqlite:///./data/db/trading.db
```

## 📊 回测示例

### 示例1：基础回测

使用均线交叉策略回测BTC：

```bash
btc-trade backtest start \
  --strategy ma_cross \
  --symbol BTC-USD \
  --start 2024-01-01 \
  --end 2024-12-31
```

### 示例2：自定义参数回测

```bash
btc-trade backtest start \
  --strategy ma_cross \
  --symbol BTC-USD \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --params '{"short_window": 10, "long_window": 30}'
```

### 示例3：查看回测结果

```bash
# 列出所有回测
btc-trade backtest list

# 查看特定回测的详细报告
btc-trade backtest report --id <backtest_id>
```

### 回测结果解读

回测报告包含以下关键指标：

- **总收益率**：策略的总体收益百分比
- **年化收益率**：按年计算的收益率
- **夏普比率**：风险调整后的收益（>1为良好）
- **最大回撤**：最大的资金回撤百分比
- **胜率**：盈利交易占总交易的比例
- **盈亏比**：平均盈利/平均亏损

## 🎮 模拟交易

模拟交易使用虚拟资金，但连接真实市场数据。

### 启动模拟交易

```bash
btc-trade trade start \
  --strategy ma_cross \
  --symbol BTC-USD \
  --mode simulation \
  --capital 100000
```

### 监控交易状态

```bash
# 查看交易状态
btc-trade trade status

# 查看当前持仓
btc-trade trade positions

# 查看订单历史
btc-trade trade orders

# 查看实时监控面板
btc-trade monitor dashboard
```

### 停止交易

```bash
btc-trade trade stop
```

## 💰 实盘交易

**⚠️ 警告**：实盘交易涉及真实资金，请务必：
1. 先在模拟环境充分测试
2. 从小资金开始
3. 设置严格的风控规则
4. 理解策略的风险

### 启动实盘交易

```bash
# 确保 .env 中设置 SYSTEM_MODE=live
btc-trade trade start \
  --strategy ma_cross \
  --symbol BTC-USD \
  --mode live \
  --capital 1000 \
  --exchange binance
```

### 风险管理配置

在配置文件中设置风控参数：

```yaml
# config/risk.yaml
risk_management:
  max_position_size: 0.1  # 单个持仓最大占比10%
  max_drawdown: 0.2       # 最大回撤20%
  daily_loss_limit: 0.05  # 每日最大亏损5%
  stop_loss: 0.02         # 止损2%
  take_profit: 0.05       # 止盈5%
```

## 🔧 策略开发

### 创建自定义策略

1. 在 `src/strategies/examples/` 创建新文件：

```python
# src/strategies/examples/my_strategy.py
from typing import Dict, Optional
import pandas as pd
from ..base import Strategy
from ...core.event import MarketEvent, SignalEvent
from ...core.types import SignalType

class MyStrategy(Strategy):
    """我的自定义策略"""

    def __init__(self, strategy_id: str, config: Dict):
        super().__init__(strategy_id, config)
        # 初始化策略参数
        self.param1 = self.parameters.get('param1', 10)

    def on_init(self):
        """策略初始化"""
        pass

    async def on_market_data(self, event: MarketEvent) -> Optional[SignalEvent]:
        """处理实时行情数据"""
        # 获取历史数据
        data = self.get_data(event.symbol)
        if data is None or len(data) < 20:
            return None

        # 计算指标
        data_with_indicators = self.calculate_indicators(data)

        # 生成信号
        if self._should_buy(data_with_indicators):
            return self.generate_signal(
                symbol=event.symbol,
                signal_type=SignalType.BUY,
                strength=1.0
            )
        elif self._should_sell(data_with_indicators):
            return self.generate_signal(
                symbol=event.symbol,
                signal_type=SignalType.SELL,
                strength=1.0
            )

        return None

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        # 添加你的指标计算
        data['sma'] = data['close'].rolling(window=self.param1).mean()
        return data

    def _should_buy(self, data: pd.DataFrame) -> bool:
        """买入条件"""
        latest = data.iloc[-1]
        return latest['close'] > latest['sma']

    def _should_sell(self, data: pd.DataFrame) -> bool:
        """卖出条件"""
        latest = data.iloc[-1]
        return latest['close'] < latest['sma']

    def backtest_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """回测模式：批量生成信号"""
        data = self.calculate_indicators(data)
        data['signal'] = 0
        data.loc[data['close'] > data['sma'], 'signal'] = 1
        data.loc[data['close'] < data['sma'], 'signal'] = -1
        return data
```

2. 注册策略：

```python
# src/strategies/__init__.py
from .examples.my_strategy import MyStrategy

STRATEGIES = {
    'ma_cross': MACrossStrategy,
    'my_strategy': MyStrategy,  # 添加你的策略
}
```

3. 测试策略：

```bash
btc-trade backtest start \
  --strategy my_strategy \
  --symbol BTC-USD \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --params '{"param1": 20}'
```

## ❓ 常见问题

### Q1: 如何获取历史数据？

```bash
# 下载历史数据
btc-trade data download \
  --symbol BTC-USD \
  --start 2024-01-01 \
  --end 2024-12-31

# 查看已下载的数据
btc-trade data list
```

### Q2: 回测时提示"数据不足"

确保：
1. 数据时间范围足够（至少包含策略所需的最小周期）
2. 策略的 `min_data_points` 参数合理
3. 数据已正确下载

### Q3: 如何调试策略？

```bash
# 启用DEBUG日志级别
btc-trade --log-level DEBUG backtest start \
  --strategy ma_cross \
  --symbol BTC-USD \
  --start 2024-01-01
```

### Q4: 模拟交易如何连接真实行情？

模拟交易会自动连接交易所的WebSocket获取实时行情，但订单只在本地模拟执行，不会发送到交易所。

### Q5: 如何优化策略参数？

```bash
# 使用参数优化功能
btc-trade strategy optimize \
  --name ma_cross \
  --symbol BTC-USD \
  --start 2024-01-01 \
  --end 2024-12-31
```

### Q6: 交易所API限制怎么办？

系统内置了速率限制保护，但如果频繁触发限制：
1. 增加数据获取间隔
2. 使用缓存的历史数据
3. 考虑升级交易所API等级

### Q7: 如何设置止损止盈？

在策略配置中添加：

```yaml
# config/strategies/ma_cross.yaml
strategy:
  name: ma_cross
  parameters:
    short_window: 5
    long_window: 20
  risk:
    stop_loss: 0.02      # 2%止损
    take_profit: 0.05    # 5%止盈
```

### Q8: 支持哪些交易对？

- **加密货币**：BTC-USD, ETH-USD, BTC-USDT 等（通过Binance/OKX）
- **美股**：AAPL, TSLA, GOOGL 等（通过Alpaca）
- **A股**：需要配置相应的数据源

### Q9: 如何查看系统日志？

```bash
# 日志文件位置
tail -f ./data/logs/trading.log

# 或使用监控命令
btc-trade monitor metrics
```

### Q10: 遇到错误怎么办？

1. 检查日志文件：`./data/logs/trading.log`
2. 确认环境变量配置正确
3. 验证API密钥有效性
4. 查看GitHub Issues：https://github.com/yourusername/bitcoin-stock-trading-system/issues

## 📚 进阶使用

### 多策略组合

```python
# 创建多策略配置
strategies:
  - name: ma_cross
    symbols: [BTC-USD]
    weight: 0.5
  - name: grid_trading
    symbols: [ETH-USD]
    weight: 0.5
```

### 自定义告警

```python
# 在策略中添加自定义告警
from ...monitor.alerts import send_alert

send_alert(
    title="交易信号",
    message=f"检测到买入信号：{symbol}",
    level="INFO"
)
```

### 性能优化

1. 使用Redis缓存市场数据
2. 启用数据库连接池
3. 调整EventBus队列大小
4. 使用异步数据获取

## 🔗 相关资源

- [项目文档](./docs/)
- [API参考](./docs/api.md)
- [策略示例](./src/strategies/examples/)
- [CLAUDE.md](./CLAUDE.md) - 开发者指南

## 📞 获取帮助

- GitHub Issues: [提交问题](https://github.com/yourusername/bitcoin-stock-trading-system/issues)
- 文档: [查看文档](./docs/)
- 示例: [查看示例](./examples/)

---

**免责声明**：本系统仅供学习和研究使用。量化交易存在风险，请谨慎使用真实资金。作者不对任何交易损失负责。
