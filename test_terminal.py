#!/usr/bin/env python3
"""Test if Rich Live works in your terminal"""

import time
from rich.live import Live
from rich.panel import Panel
from rich.console import Console

console = Console()

print("Testing Rich Live in your terminal...")
print("You should see a counter updating below:\n")

try:
    with Live(Panel("Starting..."), refresh_per_second=4, console=console) as live:
        for i in range(1, 11):
            live.update(Panel(f"[cyan]Counter: {i}/10[/cyan]\n[yellow]If you see this updating, Rich Live works![/yellow]"))
            time.sleep(0.5)

    print("\n✓ Test complete! Rich Live works in your terminal.")
    print("\nNow try running: btc-trade trade dashboard --mode simulation")

except Exception as e:
    print(f"\n✗ Rich Live test failed: {e}")
    print("\nYour terminal might not support Rich Live.")
    print("This could be due to:")
    print("  - Terminal type not supporting ANSI escape codes")
    print("  - Running in a non-interactive environment")
    print("  - Terminal size too small")
