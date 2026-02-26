#!/usr/bin/env python3
"""Test Rich Live context"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'examples'))

from professional_realtime import ProfessionalDashboard
from rich.live import Live
from rich.console import Console

async def test():
    console = Console()
    console.print("[cyan]Testing Rich Live...[/cyan]\n")

    dashboard = ProfessionalDashboard(max_points=100)
    console.print("✓ Dashboard created")

    console.print("Entering Live context...")

    try:
        with Live(dashboard.render(), refresh_per_second=2, console=console) as live:
            console.print("[green]✓ Inside Live context![/green]")

            for i in range(5):
                await asyncio.sleep(0.5)
                dashboard.update_price(66886 + i, 100)
                live.update(dashboard.render())
                console.print(f"[dim]Update {i+1}/5[/dim]")

            console.print("[green]✓ Test complete![/green]")

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
