"""CLI wrapper for the split-reports pipeline entry point."""

import importlib
import sys
from pathlib import Path


def _load_main():
    """Load the pipeline CLI entry point when running this file directly."""
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    return importlib.import_module("pipeline.cli").main


if __name__ == "__main__":
    _load_main()()
