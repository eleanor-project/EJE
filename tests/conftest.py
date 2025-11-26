"""Test configuration for ensuring project modules are importable."""
from pathlib import Path
import sys

# Ensure the project src directory is on the import path for tests
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))
