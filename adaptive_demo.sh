#!/bin/bash

# Adaptive Strategy Demo Script
# Runs the new adaptive strategy with visualization

echo "🚀 Starting Adaptive Strategy Demo..."
echo ""

# Create necessary directories
mkdir -p data/reports
mkdir -p data/exports
mkdir -p data/db

# Run the demo
python examples/adaptive_backtest_demo.py

echo ""
echo "✅ Demo completed!"
echo ""
echo "📊 To view the interactive chart:"
echo "   Open the HTML file in data/reports/ with your browser"
echo ""
