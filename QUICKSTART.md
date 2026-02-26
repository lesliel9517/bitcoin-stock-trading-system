# 🚀 快速开始指南

## 项目已完善内容

我已经为这个Bitcoin & Stock Trading System完善了以下内容：

### ✅ 已完成的改进

1. **详细的中文使用指南** (`README_USAGE.md`)
   - 完整的安装和配置说明
   - 回测、模拟交易、实盘交易示例
   - 策略开发教程
   - 常见问题解答

2. **真实数据提供者**
   - `BinanceDataProvider`: 获取加密货币历史和实时数据
   - `YahooFinanceProvider`: 获取美股历史数据
   - 支持WebSocket实时行情订阅

3. **示例脚本和配置**
   - `examples/quick_backtest.py`: 一键运行回测示例
   - `scripts/setup.sh`: 自动化环境配置脚本
   - `config/strategies/ma_cross_example.yaml`: 策略配置示例

4. **开发者文档**
   - `CLAUDE.md`: 完整的系统架构和开发指南

---

## 📖 如何使用

### 方法一：快速启动（推荐）

```bash
# 1. 运行自动配置脚本
bash scripts/setup.sh

# 2. 运行回测示例
python3 examples/quick_backtest.py
```

### 方法二：手动配置

```bash
# 1. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 2. 安装依赖
pip install -e .

# 3. 配置环境变量（可选，回测不需要）
cp .env.example .env

# 4. 运行回测
python3 examples/quick_backtest.py
```

### 方法三：使用CLI命令

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行回测
btc-trade backtest start \
  --strategy ma_cross \
  --symbol BTC-USD \
  --start 2024-01-01 \
  --end 2024-12-31

# 查看帮助
btc-trade --help
```

---

## 📚 详细文档

- **使用指南**: 查看 `README_USAGE.md` 了解详细使用方法
- **开发指南**: 查看 `CLAUDE.md` 了解系统架构和开发规范
- **原始README**: 查看 `README.md` 了解项目概述

---

## 🎯 快速测试

运行以下命令测试系统是否正常工作：

```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 运行快速回测示例
python3 examples/quick_backtest.py
```

这个示例会：
- 从Binance获取BTC/USDT的历史数据
- 使用均线交叉策略进行回测
- 显示详细的回测结果和性能指标

---

## ⚠️ 注意事项

1. **首次运行**: 首次运行会从Binance下载历史数据，需要网络连接
2. **API密钥**: 回测不需要API密钥，但实盘交易需要配置 `.env` 文件
3. **Python版本**: 需要Python 3.10或更高版本
4. **依赖安装**: 如果遇到依赖问题，运行 `pip install -r requirements.txt`

---

## 🔧 故障排除

### 问题1: 找不到 btc-trade 命令
```bash
# 解决方案：重新安装项目
pip install -e .
```

### 问题2: 无法获取数据
```bash
# 解决方案：检查网络连接，或使用本地数据
# 数据会自动保存到 ./data/db/trading.db
```

### 问题3: 依赖安装失败
```bash
# 解决方案：升级pip并重试
pip install --upgrade pip
pip install -e .
```

---

## 📞 获取帮助

- 查看详细使用指南: `cat README_USAGE.md`
- 查看开发文档: `cat CLAUDE.md`
- 运行帮助命令: `btc-trade --help`

---

**祝你使用愉快！** 🎉
