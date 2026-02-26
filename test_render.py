#!/usr/bin/env python3
"""Test dashboard rendering"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'examples'))

from professional_realtime import ProfessionalDashboard

print("Testing dashboard rendering...")

try:
    dashboard = ProfessionalDashboard(max_points=100)
    print("✓ Dashboard created")

    # Try to render
    print("Attempting to render...")
    layout = dashboard.render()
    print("✓ Dashboard rendered successfully!")

    # Try to render again
    layout = dashboard.render()
    print("✓ Second render successful!")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
