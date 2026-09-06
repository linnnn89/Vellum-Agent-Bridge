"""Unit test runner for vellum-wpf-bridge."""

from pathlib import Path
import sys
import unittest

# Ensure src/ is on sys.path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover(str(Path(__file__).parent), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
