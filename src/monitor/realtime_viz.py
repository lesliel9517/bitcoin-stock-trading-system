"""Real-time trading visualization"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
import pandas as pd
from pathlib import Path
import json

from ..utils.logger import logger


class RealtimeVisualizer:
    """Real-time trading visualizer

    Updates visualization during live trading
    """

    def __init__(self, output_dir: str = "./data/realtime"):
        """Initialize real-time visualizer

        Args:
            output_dir: Output directory for real-time data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.data_file = self.output_dir / "realtime_data.json"
        self.html_file = self.output_dir / "realtime_chart.html"

        # Data buffers
        self.prices: List[Dict] = []
        self.trades: List[Dict] = []
        self.equity: List[Dict] = []
        self.signals: List[Dict] = []

        self._initialize_html()

    def _initialize_html(self):
        """Initialize HTML file with auto-refresh"""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>实时交易监控</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 28px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-label {
            color: #666;
            font-size: 12px;
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .stat-value.positive {
            color: #26a69a;
        }
        .stat-value.negative {
            color: #ef5350;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .status {
            text-align: center;
            padding: 10px;
            background: #4caf50;
            color: white;
            border-radius: 5px;
            font-weight: bold;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 实时交易监控</h1>
        <div class="status" id="status">正在加载数据...</div>
    </div>

    <div class="stats" id="stats"></div>

    <div class="chart-container">
        <div id="priceChart"></div>
    </div>

    <div class="chart-container">
        <div id="equityChart"></div>
    </div>

    <script>
        let updateInterval;

        async function loadData() {
            try {
                const response = await fetch('realtime_data.json?t=' + Date.now());
                const data = await response.json();
                updateCharts(data);
                updateStats(data);
                document.getElementById('status').textContent = '🟢 实时更新中 - ' + new Date().toLocaleTimeString();
                document.getElementById('status').style.background = '#4caf50';
            } catch (error) {
                console.error('加载数据失败:', error);
                document.getElementById('status').textContent = '🔴 连接断开';
                document.getElementById('status').style.background = '#ef5350';
            }
        }

        function updateStats(data) {
            const stats = data.stats || {};
            const statsHtml = `
                <div class="stat-card">
                    <div class="stat-label">当前价格</div>
                    <div class="stat-value">$${(stats.current_price || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">账户总值</div>
                    <div class="stat-value">$${(stats.total_equity || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">总收益</div>
                    <div class="stat-value ${stats.total_pnl >= 0 ? 'positive' : 'negative'}">
                        ${stats.total_pnl >= 0 ? '+' : ''}$${(stats.total_pnl || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">收益率</div>
                    <div class="stat-value ${stats.return_pct >= 0 ? 'positive' : 'negative'}">
                        ${stats.return_pct >= 0 ? '+' : ''}${(stats.return_pct || 0).toFixed(2)}%
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">交易次数</div>
                    <div class="stat-value">${stats.total_trades || 0}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">持仓状态</div>
                    <div class="stat-value">${stats.position_status || '空仓'}</div>
                </div>
            `;
            document.getElementById('stats').innerHTML = statsHtml;
        }

        function updateCharts(data) {
            // Price chart with trades
            const prices = data.prices || [];
            const trades = data.trades || [];
            const signals = data.signals || [];

            if (prices.length > 0) {
                const priceTrace = {
                    x: prices.map(p => p.timestamp),
                    y: prices.map(p => p.price),
                    type: 'scatter',
                    mode: 'lines',
                    name: '价格',
                    line: {color: '#2196f3', width: 2}
                };

                const buyTrades = trades.filter(t => t.side === 'buy');
                const sellTrades = trades.filter(t => t.side === 'sell');

                const buyTrace = {
                    x: buyTrades.map(t => t.timestamp),
                    y: buyTrades.map(t => t.price),
                    type: 'scatter',
                    mode: 'markers',
                    name: '买入',
                    marker: {
                        symbol: 'triangle-up',
                        size: 15,
                        color: '#26a69a',
                        line: {color: 'white', width: 2}
                    }
                };

                const sellTrace = {
                    x: sellTrades.map(t => t.timestamp),
                    y: sellTrades.map(t => t.price),
                    type: 'scatter',
                    mode: 'markers',
                    name: '卖出',
                    marker: {
                        symbol: 'triangle-down',
                        size: 15,
                        color: '#ef5350',
                        line: {color: 'white', width: 2}
                    }
                };

                const priceLayout = {
                    title: '价格走势与交易信号',
                    xaxis: {title: '时间'},
                    yaxis: {title: '价格 (USD)'},
                    hovermode: 'x unified',
                    showlegend: true,
                    height: 400
                };

                Plotly.newPlot('priceChart', [priceTrace, buyTrace, sellTrace], priceLayout, {responsive: true});
            }

            // Equity chart
            const equity = data.equity || [];

            if (equity.length > 0) {
                const equityTrace = {
                    x: equity.map(e => e.timestamp),
                    y: equity.map(e => e.value),
                    type: 'scatter',
                    mode: 'lines',
                    name: '账户总值',
                    fill: 'tozeroy',
                    line: {color: '#9c27b0', width: 2},
                    fillcolor: 'rgba(156, 39, 176, 0.1)'
                };

                const equityLayout = {
                    title: '账户资金曲线',
                    xaxis: {title: '时间'},
                    yaxis: {title: '总值 (USD)'},
                    hovermode: 'x unified',
                    showlegend: true,
                    height: 300
                };

                Plotly.newPlot('equityChart', [equityTrace], equityLayout, {responsive: true});
            }
        }

        // Initial load
        loadData();

        // Auto refresh every 2 seconds
        updateInterval = setInterval(loadData, 2000);

        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (updateInterval) {
                clearInterval(updateInterval);
            }
        });
    </script>
</body>
</html>"""

        self.html_file.write_text(html_content, encoding='utf-8')
        logger.info(f"Real-time visualization initialized: {self.html_file}")

    def update_price(self, timestamp: datetime, price: Decimal):
        """Update price data

        Args:
            timestamp: Timestamp
            price: Current price
        """
        self.prices.append({
            'timestamp': timestamp.isoformat(),
            'price': float(price)
        })

        # Keep last 500 points
        if len(self.prices) > 500:
            self.prices = self.prices[-500:]

    def add_trade(self, timestamp: datetime, side: str, price: Decimal, quantity: Decimal):
        """Add trade marker

        Args:
            timestamp: Trade timestamp
            side: buy or sell
            price: Trade price
            quantity: Trade quantity
        """
        self.trades.append({
            'timestamp': timestamp.isoformat(),
            'side': side,
            'price': float(price),
            'quantity': float(quantity)
        })

    def update_equity(self, timestamp: datetime, equity: Decimal):
        """Update equity curve

        Args:
            timestamp: Timestamp
            equity: Total equity
        """
        self.equity.append({
            'timestamp': timestamp.isoformat(),
            'value': float(equity)
        })

        # Keep last 500 points
        if len(self.equity) > 500:
            self.equity = self.equity[-500:]

    def add_signal(self, timestamp: datetime, signal_type: str, price: Decimal):
        """Add trading signal

        Args:
            timestamp: Signal timestamp
            signal_type: Signal type (buy/sell)
            price: Price at signal
        """
        self.signals.append({
            'timestamp': timestamp.isoformat(),
            'type': signal_type,
            'price': float(price)
        })

    def update_stats(self, stats: Dict):
        """Update statistics

        Args:
            stats: Statistics dictionary
        """
        self.stats = stats

    def save(self):
        """Save current data to JSON file"""
        data = {
            'prices': self.prices,
            'trades': self.trades,
            'equity': self.equity,
            'signals': self.signals,
            'stats': getattr(self, 'stats', {}),
            'updated_at': datetime.now().isoformat()
        }

        self.data_file.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def get_url(self) -> str:
        """Get visualization URL

        Returns:
            File URL for browser
        """
        return f"file://{self.html_file.absolute()}"
