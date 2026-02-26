#!/bin/bash
# Quick start script for live trading simulation

echo "Starting live trading simulation..."
echo ""

# Run the trading command with default parameters
btc-trade trade start \
    --strategy ma_cross \
    --symbol BTC-USD \
    --mode simulation \
    --capital 100000 \
    --update-interval 0.5 \
    --duration 60

echo ""
echo "Trading session completed."
