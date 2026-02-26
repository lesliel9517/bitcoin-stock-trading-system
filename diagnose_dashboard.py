#!/usr/bin/env python3
"""Diagnose dashboard rendering issue"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'examples'))

print("Step 1: Testing basic Rich Live...")
try:
    from rich.live import Live
    from rich.panel import Panel
    from rich.console import Console
    import time

    console = Console()
    with Live(Panel("Test"), refresh_per_second=2, console=console) as live:
        for i in range(3):
            live.update(Panel(f"Count: {i}"))
            time.sleep(0.5)
    print("✓ Basic Rich Live works\n")
except Exception as e:
    print(f"✗ Basic Rich Live failed: {e}\n")
    import traceback
    traceback.print_exc()

print("Step 2: Testing plotext...")
try:
    import plotext as plt
    plt.clf()
    plt.plot([1, 2, 3], [1, 4, 2])
    plt.title("Test")
    chart_str = plt.build()
    print("✓ Plotext works")
    print(f"Chart length: {len(chart_str)} chars\n")
except Exception as e:
    print(f"✗ Plotext failed: {e}\n")
    import traceback
    traceback.print_exc()

print("Step 3: Testing dashboard render...")
try:
    from professional_realtime import ProfessionalDashboard
    dashboard = ProfessionalDashboard(max_points=100)
    dashboard.update_price(66886.0, 100.0)

    print("Calling dashboard.render()...")
    layout = dashboard.render()
    print("✓ Dashboard render works\n")
except Exception as e:
    print(f"✗ Dashboard render failed: {e}\n")
    import traceback
    traceback.print_exc()

print("Step 4: Testing Live with dashboard...")
try:
    from rich.live import Live
    from rich.console import Console
    from professional_realtime import ProfessionalDashboard
    import time

    console = Console()
    dashboard = ProfessionalDashboard(max_points=100)
    dashboard.update_price(66886.0, 100.0)

    print("Entering Live context with dashboard...")
    with Live(dashboard.render(), refresh_per_second=2, console=console) as live:
        print("Inside Live context!")
        for i in range(3):
            dashboard.update_price(66886.0 + i, 100.0)
            live.update(dashboard.render())
            time.sleep(0.5)
    print("✓ Live with dashboard works\n")
except Exception as e:
    print(f"✗ Live with dashboard failed: {e}\n")
    import traceback
    traceback.print_exc()

print("All tests complete!")
