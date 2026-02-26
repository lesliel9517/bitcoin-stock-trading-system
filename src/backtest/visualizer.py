"""Backtest visualization module"""

from typing import Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

from ..utils.logger import logger


class BacktestVisualizer:
    """Backtest results visualizer

    Creates interactive charts for backtest analysis
    """

    def __init__(self):
        """Initialize visualizer"""
        self.colors = {
            'up': '#26a69a',      # Green for bullish
            'down': '#ef5350',    # Red for bearish
            'buy': '#00e676',     # Bright green for buy signals
            'sell': '#ff1744',    # Bright red for sell signals
            'equity': '#2196f3',  # Blue for equity curve
            'drawdown': '#ff9800', # Orange for drawdown
            'ma_short': '#9c27b0', # Purple for short MA
            'ma_long': '#ff5722'   # Deep orange for long MA
        }

    def create_report(
        self,
        data: pd.DataFrame,
        trades: List[Dict],
        equity_curve: pd.DataFrame,
        metrics: Dict,
        output_path: str = "./data/reports/backtest_report.html"
    ):
        """Create comprehensive backtest report

        Args:
            data: Market data with signals
            trades: List of trade records
            equity_curve: Equity curve data
            metrics: Performance metrics
            output_path: Output HTML file path
        """
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.5, 0.25, 0.25],
            subplot_titles=(
                'Price & Trading Signals',
                'Equity Curve',
                'Drawdown'
            )
        )

        # 1. Candlestick chart with signals
        self._add_candlestick(fig, data, trades, row=1)

        # 2. Equity curve
        self._add_equity_curve(fig, equity_curve, row=2)

        # 3. Drawdown
        self._add_drawdown(fig, equity_curve, row=3)

        # Update layout
        fig.update_layout(
            title={
                'text': self._create_title(metrics),
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'color': '#333'}
            },
            height=1200,
            showlegend=True,
            hovermode='x unified',
            template='plotly_white',
            font={'family': 'Arial, sans-serif', 'size': 12},
            margin=dict(l=80, r=80, t=120, b=80)
        )

        # Update axes
        fig.update_xaxes(
            rangeslider_visible=False,
            showgrid=True,
            gridcolor='#e0e0e0'
        )
        fig.update_yaxes(
            showgrid=True,
            gridcolor='#e0e0e0'
        )

        # Save to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_file))

        logger.info(f"Backtest report saved to {output_path}")
        return str(output_file)

    def _add_candlestick(self, fig, data: pd.DataFrame, trades: List[Dict], row: int):
        """Add candlestick chart with trading signals"""
        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name='Price',
                increasing_line_color=self.colors['up'],
                decreasing_line_color=self.colors['down'],
                showlegend=False
            ),
            row=row, col=1
        )

        # Add moving averages if available
        if 'ma_short' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['ma_short'],
                    name='MA Short',
                    line=dict(color=self.colors['ma_short'], width=1.5),
                    opacity=0.7
                ),
                row=row, col=1
            )

        if 'ma_long' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['ma_long'],
                    name='MA Long',
                    line=dict(color=self.colors['ma_long'], width=1.5),
                    opacity=0.7
                ),
                row=row, col=1
            )

        # Add trade markers
        if trades:
            trades_df = pd.DataFrame(trades)

            # Buy signals
            buy_trades = trades_df[trades_df['side'] == 'buy']
            if not buy_trades.empty:
                fig.add_trace(
                    go.Scatter(
                        x=buy_trades['timestamp'],
                        y=buy_trades['price'],
                        mode='markers',
                        name='Buy',
                        marker=dict(
                            symbol='triangle-up',
                            size=12,
                            color=self.colors['buy'],
                            line=dict(color='white', width=1)
                        ),
                        hovertemplate='<b>Buy</b><br>Price: %{y:.2f}<br>%{x}<extra></extra>'
                    ),
                    row=row, col=1
                )

            # Sell signals
            sell_trades = trades_df[trades_df['side'] == 'sell']
            if not sell_trades.empty:
                fig.add_trace(
                    go.Scatter(
                        x=sell_trades['timestamp'],
                        y=sell_trades['price'],
                        mode='markers',
                        name='Sell',
                        marker=dict(
                            symbol='triangle-down',
                            size=12,
                            color=self.colors['sell'],
                            line=dict(color='white', width=1)
                        ),
                        hovertemplate='<b>Sell</b><br>Price: %{y:.2f}<br>%{x}<extra></extra>'
                    ),
                    row=row, col=1
                )

    def _add_equity_curve(self, fig, equity_curve: pd.DataFrame, row: int):
        """Add equity curve chart"""
        fig.add_trace(
            go.Scatter(
                x=equity_curve['timestamp'],
                y=equity_curve['equity'],
                name='Equity',
                line=dict(color=self.colors['equity'], width=2),
                fill='tozeroy',
                fillcolor='rgba(33, 150, 243, 0.1)',
                hovertemplate='<b>Equity</b><br>Value: %{y:,.2f}<br>%{x}<extra></extra>'
            ),
            row=row, col=1
        )

    def _add_drawdown(self, fig, equity_curve: pd.DataFrame, row: int):
        """Add drawdown chart"""
        # Calculate drawdown
        equity = equity_curve['equity'].values
        running_max = pd.Series(equity).expanding().max()
        drawdown = ((equity - running_max) / running_max * 100)

        fig.add_trace(
            go.Scatter(
                x=equity_curve['timestamp'],
                y=drawdown,
                name='Drawdown',
                line=dict(color=self.colors['drawdown'], width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 152, 0, 0.2)',
                hovertemplate='<b>Drawdown</b><br>%{y:.2f}%<br>%{x}<extra></extra>'
            ),
            row=row, col=1
        )

        # Add zero line
        fig.add_hline(
            y=0, line_dash="dash", line_color="gray",
            opacity=0.5, row=row, col=1
        )

    def _create_title(self, metrics: Dict) -> str:
        """Create report title with key metrics"""
        total_return = metrics.get('total_return', 0)
        sharpe = metrics.get('sharpe_ratio', 0)
        max_dd = metrics.get('max_drawdown', 0)
        win_rate = metrics.get('win_rate', 0)

        return (
            f"Backtest Report | "
            f"Return: {total_return:.2f}% | "
            f"Sharpe: {sharpe:.2f} | "
            f"Max DD: {max_dd:.2f}% | "
            f"Win Rate: {win_rate:.2f}%"
        )

    def create_simple_chart(
        self,
        data: pd.DataFrame,
        trades: List[Dict],
        output_path: str = "./data/reports/simple_chart.html"
    ):
        """Create simple price chart with trades

        Args:
            data: Market data
            trades: Trade records
            output_path: Output file path
        """
        fig = go.Figure()

        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name='Price',
                increasing_line_color=self.colors['up'],
                decreasing_line_color=self.colors['down']
            )
        )

        # Trade markers
        if trades:
            trades_df = pd.DataFrame(trades)

            buy_trades = trades_df[trades_df['side'] == 'buy']
            if not buy_trades.empty:
                fig.add_trace(
                    go.Scatter(
                        x=buy_trades['timestamp'],
                        y=buy_trades['price'],
                        mode='markers',
                        name='Buy',
                        marker=dict(
                            symbol='triangle-up',
                            size=15,
                            color=self.colors['buy']
                        )
                    )
                )

            sell_trades = trades_df[trades_df['side'] == 'sell']
            if not sell_trades.empty:
                fig.add_trace(
                    go.Scatter(
                        x=sell_trades['timestamp'],
                        y=sell_trades['price'],
                        mode='markers',
                        name='Sell',
                        marker=dict(
                            symbol='triangle-down',
                            size=15,
                            color=self.colors['sell']
                        )
                    )
                )

        fig.update_layout(
            title='Trading Chart',
            xaxis_title='Date',
            yaxis_title='Price',
            height=600,
            template='plotly_white',
            hovermode='x unified'
        )

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_file))

        logger.info(f"Chart saved to {output_path}")
        return str(output_file)
