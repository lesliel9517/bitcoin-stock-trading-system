#!/bin/bash
# Paper trading with real Binance market data
# This uses real market prices but simulates order execution (no real money at risk)

echo "Starting paper trading with real Binance data..."
echo "Mode: Paper Trading (real data, virtual money)"
echo ""

# Run the trading command with paper mode
btc-trade trade start \
    --strategy ma_cross \
    --symbol BTC-USD \
    --mode paper \
    --capital 100000

echo ""
echo "Paper trading session completed."
