#!/usr/bin/env python3
"""Test Live with simplified dashboard (no plotext)"""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

from rich.live import Live
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table

def create_simple_dashboard(price, equity):
    """Create a simple dashboard without plotext"""
    layout = Layout()

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1)
    )

    # Header
    layout["header"].update(Panel(f"BTC-USD: ${price:,.2f}", style="bold cyan"))

    # Body - just a table
    table = Table(show_header=False)
    table.add_column("Label", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("账户总值", f"${equity:,.2f}")
    table.add_row("持仓状态", "空仓")

    layout["body"].update(Panel(table, title="实时数据"))

    return layout

print("Testing Live with simplified dashboard (no plotext)...")

try:
    console = Console()

    with Live(create_simple_dashboard(66886, 100000), refresh_per_second=4, console=console) as live:
        print("Inside Live context!")
        for i in range(10):
            price = 66886 + i * 10
            equity = 100000 + i * 100
            live.update(create_simple_dashboard(price, equity))
            time.sleep(0.3)

    print("\n✓ Simplified dashboard works!")
    print("\nConclusion: The issue is with plotext in Live context.")
    print("Solution: Need to fix plotext usage in professional_realtime.py")

except Exception as e:
    print(f"\n✗ Failed: {e}")
    import traceback
    traceback.print_exc()
