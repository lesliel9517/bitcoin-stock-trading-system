# 交易系统优化说明

## 优化内容总结

本次优化为比特币交易系统添加了三个重要功能：

### 1. 动态自适应交易策略 ✅

**位置**: `src/strategies/examples/adaptive_strategy.py`

**核心特性**:
- **市场状态检测**: 自动识别市场趋势（上涨/下跌/震荡）
- **波动率分析**: 检测市场波动率（高/正常/低）
- **动态参数调整**:
  - 趋势市场：调整MA周期以捕捉动量
  - 震荡市场：使用基准参数
  - 高波动：扩大止损（3%）、减小仓位（70%）
  - 低波动：收紧止损（1.5%）、增大仓位（95%）
- **自适应风控**: 根据市场条件动态调整止损止盈

**使用方法**:
```python
from src.strategies.examples.adaptive_strategy import AdaptiveStrategy

strategy = AdaptiveStrategy('adaptive_btc', {
    'parameters': {
        'ma_short': 10,
        'ma_long': 30,
        'volatility_window': 20,
        'trend_window': 50
    }
})
```

### 2. 交易记录序列化存储 ✅

**位置**: `src/data/storage.py`

**新增功能**:
- **trades 表**: 存储所有交易记录（买入/卖出、价格、数量、手续费）
- **equity_curve 表**: 存储资金曲线数据
- **backtest_sessions 表**: 存储回测会话元数据

**API 方法**:
```python
storage = DataStorage()

# 保存交易记录
storage.save_trades(trades, session_id, strategy_name)

# 保存资金曲线
storage.save_equity_curve(equity_data, session_id)

# 保存回测会话
storage.save_backtest_session(session_data)

# 查询历史记录
trades_df = storage.load_trades(session_id)
equity_df = storage.load_equity_curve(session_id)
sessions_df = storage.get_backtest_sessions(limit=10)

# 导出为CSV
storage.export_trades_csv(session_id, 'trades.csv')
storage.export_equity_csv(session_id, 'equity.csv')
```

### 3. 交互式可视化图表 ✅

**位置**: `src/backtest/visualizer.py`

**图表内容**:
1. **K线图 + 交易信号**
   - 蜡烛图显示价格走势
   - 移动平均线叠加
   - 买入信号（绿色三角形向上）
   - 卖出信号（红色三角形向下）

2. **资金曲线图**
   - 显示账户总资产变化
   - 填充区域显示增长

3. **回撤图**
   - 显示最大回撤
   - 橙色填充区域

**特点**:
- 使用 Plotly 实现交互式图表
- 支持缩放、平移、悬停显示详情
- 美观的配色方案
- 自动生成 HTML 报告

**使用方法**:
```python
from src.backtest.visualizer import BacktestVisualizer

visualizer = BacktestVisualizer()
visualizer.create_report(
    data=data_with_signals,
    trades=trades,
    equity_curve=equity_df,
    metrics=metrics,
    output_path='./report.html'
)
```

## 快速开始

### 运行自适应策略演示

```bash
# 方式1: 使用脚本
./adaptive_demo.sh

# 方式2: 直接运行
source .venv/bin/activate
python examples/adaptive_backtest_demo.py
```

### 查看结果

1. **控制台输出**: 显示回测统计数据
2. **交互式报告**: 在 `data/reports/` 目录下生成 HTML 文件
3. **CSV导出**: 在 `data/exports/` 目录下生成交易和资金曲线 CSV
4. **数据库**: SQLite 数据库位于 `data/db/trading.db`

### 在浏览器中查看可视化报告

```bash
# 找到生成的报告文件
ls data/reports/

# 在浏览器中打开
open data/reports/backtest_*.html  # macOS
# 或直接双击 HTML 文件
```

## 集成到现有系统

### 在回测中使用

```python
from src.backtest.engine import BacktestEngine
from src.strategies.examples.adaptive_strategy import AdaptiveStrategy
from src.data.storage import DataStorage

# 初始化
storage = DataStorage()
engine = BacktestEngine(
    initial_capital=Decimal(100000),
    storage=storage  # 自动保存结果
)

# 设置策略
strategy = AdaptiveStrategy('my_strategy', config)
engine.set_strategy(strategy)

# 运行回测
results = await engine.run(data, symbol='BTC-USD')

# 结果自动保存到数据库并生成可视化报告
print(f"Report: {results['report_path']}")
print(f"Session: {results['session_id']}")
```

### 查询历史回测

```python
from src.data.storage import DataStorage

storage = DataStorage()

# 查看最近的回测会话
sessions = storage.get_backtest_sessions(limit=10)
print(sessions)

# 加载特定会话的数据
session_id = 'xxx-xxx-xxx'
trades = storage.load_trades(session_id)
equity = storage.load_equity_curve(session_id)
```

## 技术细节

### 数据库表结构

**trades 表**:
- session_id: 会话ID
- timestamp: 交易时间
- symbol: 交易对
- side: 买入/卖出
- quantity: 数量
- price: 价格
- commission: 手续费
- portfolio_value: 账户总值

**equity_curve 表**:
- session_id: 会话ID
- timestamp: 时间点
- equity: 总资产
- cash: 现金
- position_value: 持仓市值
- price: 当前价格

**backtest_sessions 表**:
- id: 会话ID
- strategy: 策略名称
- symbol: 交易对
- start_date/end_date: 回测时间范围
- initial_capital/final_capital: 初始/最终资金
- total_return: 总收益率
- total_trades: 交易次数
- win_rate: 胜率
- sharpe_ratio: 夏普比率
- max_drawdown: 最大回撤

### 自适应策略算法

1. **波动率检测**:
   - 计算最近20天的收益率标准差
   - 与历史标准差对比
   - 高波动: > 1.5倍历史波动
   - 低波动: < 0.7倍历史波动

2. **趋势检测**:
   - 对50天SMA进行线性回归
   - 斜率 > 0.5%: 上涨趋势
   - 斜率 < -0.5%: 下跌趋势
   - 其他: 震荡市场

3. **参数调整规则**:
   - 上涨趋势: MA周期缩短（更快响应）
   - 下跌趋势: MA周期延长（避免假信号）
   - 高波动: 止损扩大、仓位减小
   - 低波动: 止损收紧、仓位增大

## 性能优化建议

1. **数据库索引**: 已为常用查询字段创建索引
2. **批量操作**: 使用批量插入提高性能
3. **可视化**: Plotly 图表支持大数据量（10000+ 点）
4. **内存管理**: 策略只保留必要的历史数据

## 未来扩展方向

1. **更多策略**: 可以基于 AdaptiveStrategy 创建更多变体
2. **实时监控**: 将可视化集成到实时交易监控
3. **多策略对比**: 在同一图表中对比多个策略
4. **机器学习**: 使用历史数据训练参数优化模型
5. **风险指标**: 添加更多风险评估指标（VaR、CVaR等）

## 依赖项

所有必需的依赖已在 `requirements.txt` 中：
- plotly>=5.17.0 (可视化)
- pandas>=2.0.0 (数据处理)
- numpy>=1.24.0 (数值计算)
- sqlalchemy>=2.0.0 (数据库ORM，可选)

## 故障排除

### 问题: 可视化报告无法打开
**解决**: 确保使用现代浏览器（Chrome、Firefox、Safari）

### 问题: 数据库锁定
**解决**: 确保没有其他进程正在访问数据库文件

### 问题: 策略参数不生效
**解决**: 检查配置字典中的 `parameters` 键是否正确

## 联系与支持

如有问题或建议，请查看项目文档或提交 Issue。
