# Dashboard字段说明 - 最终版本

## 价格统计区字段（11行）

### 顶部大号价格
- **当前价格** + 涨跌金额 + 涨跌百分比

### 第一列（左侧）
1. **24H最高** - 过去24小时最高价（来自Binance ticker）
2. **今开** - 今日开盘价（来自Binance ticker）
3. **成交量** - 24小时总成交量（来自Binance ticker）
4. **会话最高** - 本次交易会话期间的最高价（程序启动后记录）
5. **52周最高** - 52周最高价（来自交易所，如果提供）

### 第二列（右侧）
1. **24H最低** - 过去24小时最低价（来自Binance ticker）
2. **昨收** - 昨日收盘价（近似为24h开盘价）
3. **24H涨跌** - 相对于开盘价的涨跌百分比
4. **会话最低** - 本次交易会话期间的最低价（程序启动后记录）
5. **52周最低** - 52周最低价（来自交易所，如果提供）

## 字段说明

### 会话最高/最低 vs 历史最高/最低
- **会话最高/最低**：从程序启动开始记录的最高/最低价格
- **52周最高/最低**：过去52周（约1年）的最高/最低价格
- 会话数据在程序重启后重置
- 52周数据需要从交易所API获取（如果支持）

### 数据来源
- **24H数据**：来自Binance WebSocket ticker事件（每秒更新）
- **会话数据**：本地实时计算（每次价格更新时比较）
- **52周数据**：需要从交易所API获取（目前默认为0）

## 注意事项

### Binance API限制
Binance的WebSocket ticker事件**不提供**52周最高/最低数据。要获取这些数据需要：

1. **方案1：REST API查询**（推荐）
   - 在程序启动时调用 Binance REST API
   - 获取过去52周的K线数据
   - 计算最高/最低价格
   - 定期更新（如每小时）

2. **方案2：本地计算**
   - 持久化历史价格数据到数据库
   - 滚动计算52周窗口的最高/最低
   - 需要长期运行才能积累数据

3. **方案3：使用第三方数据源**
   - CoinGecko API
   - CryptoCompare API
   - 提供历史统计数据

### 当前实现
- 52周最高/最低字段已添加到dashboard
- `update_price()` 方法支持接收这些参数
- **默认值为0**（需要实现数据获取逻辑）

## 实现52周数据的建议

如果需要显示真实的52周数据，建议在 `trade.py` 中添加：

```python
# 在程序启动时获取52周数据
async def fetch_52_week_data(symbol):
    import ccxt.async_support as ccxt
    exchange = ccxt.binance()

    # 获取过去365天的日K线
    ohlcv = await exchange.fetch_ohlcv(symbol, '1d', limit=365)

    # 计算52周最高/最低
    week_52_high = max(candle[2] for candle in ohlcv)  # High
    week_52_low = min(candle[3] for candle in ohlcv)   # Low

    await exchange.close()
    return week_52_high, week_52_low

# 在dashboard初始化后调用
week_52_high, week_52_low = await fetch_52_week_data(symbol)
dashboard.week_52_high = week_52_high
dashboard.week_52_low = week_52_low
```

## 快捷键

- `Ctrl+C` - 退出程序
- `1-6` - 切换时间周期
- `S` - 切换策略
- `R` - 刷新显示

## 运行命令

```bash
btc-trade trade start --strategy ma_cross --symbol BTC-USD --mode paper --dashboard
```

等待1-2秒后，所有字段会显示实时数据（除了52周数据需要单独实现）。
