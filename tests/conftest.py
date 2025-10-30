"""Common test configuration for all tests.

This file is automatically loaded by pytest and also sets up
the Python path for regular test execution.
"""

import sys
from pathlib import Path

# Add src directory to Python path so tests can import modules
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
