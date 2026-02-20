"""Smoke test for app.py CLI"""

import subprocess
import sys


def test_cli_runs():
    """Test that app.py runs successfully and produces expected output."""
    result = subprocess.run(
        [sys.executable, "app.py"],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Check it ran without errors
    assert result.returncode == 0, f"APP failed with: {result.stderr}"
    
    # Check for expected output sections
    assert "LNG DIVERSION TRADE NOTE" in result.stdout
    assert "Decision:" in result.stdout
    assert "netback" in result.stdout.lower()
    assert "Hedge:" in result.stdout