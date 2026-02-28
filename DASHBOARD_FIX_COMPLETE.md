# Dashboard修复完成 - 使用指南

## 已修复的问题

### 1. 价格统计区显示完整 ✓
- 最高、最低、今开、昨收
- 成交量、24H涨跌
- 历史最高、振幅

### 2. 图表区功能完整 ✓
- 蓝色价格线（●）
- 橙色均线（·）
- 白色当前价虚线（─）
- 左侧价格刻度（$格式）
- 右侧涨跌幅刻度（绿色/红色%）

### 3. Binance API地区限制处理 ✓
- 使用异步ccxt
- 代理配置支持
- 友好错误提示

## 重要：清理缓存后重新运行

```bash
# 1. 清理Python缓存（必须执行）
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# 2. 重新安装（如果需要）
pip install -e .

# 3. 启动交易
btc-trade trade start --strategy ma_cross --symbol BTC-USD --mode paper --dashboard
```

## 数据显示说明

Dashboard启动后的数据显示过程：

1. **初始状态（0-1秒）**：部分指标为0或默认值
2. **接收Trade事件（高频）**：更新当前价格
3. **接收Ticker事件（每秒1次）**：更新所有24h统计指标

**等待1-2秒后，所有指标会显示完整数据。**

## 修复的关键代码

### src/cli/commands/trade.py:287-310
```python
# 区分处理两种事件
if event.high is not None and event.low is not None and event.open is not None:
    # Ticker事件：更新完整统计
    dashboard.update_price(
        price,
        volume_24h=tick_volume,
        high_24h=float(event.high),
        low_24h=float(event.low),
        open_price=float(event.open),
        tick_volume=tick_volume
    )
else:
    # Trade事件：只更新价格
    dashboard.update_price(price, volume_24h=0, tick_volume=tick_volume)
```

### src/cli/dashboard/professional.py:643
```python
def update_price(self, price: float, volume_24h: float = 0,
                 high_24h: float = None, low_24h: float = None,
                 open_price: float = None, tick_volume: float = 0):
    # 接收并处理24h统计数据
```

### src/cli/dashboard/professional.py:287
```python
def render_chart(self) -> Panel:
    """渲染主图表区：价格线 + 均线 + 当前价虚线 + 双刻度"""
    # 包含所有图表元素
```

## 配置代理（可选，用于历史K线）

```bash
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port
```

## 验证修复

运行验证脚本：
```bash
python3 test_dashboard_fix.py
```

所有检查应该显示 ✓

## 故障排除

如果仍然看不到数据：

1. **确认已清理缓存**：删除所有 `__pycache__` 目录
2. **检查网络连接**：确保能访问 Binance WebSocket
3. **等待数据加载**：启动后等待2-3秒
4. **查看日志**：检查 `./data/logs/trading.log`

## 文件修改清单

- `src/cli/dashboard/professional.py` - 更新 update_price(), render_chart(), load_historical_data()
- `src/cli/commands/trade.py` - 修复事件处理逻辑（两处）
