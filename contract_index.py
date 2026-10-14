"""Compatibility entry point. Prefer python -m highway_contracts."""
from highway_contracts.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
