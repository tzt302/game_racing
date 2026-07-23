"""Compatibility copy for tools that put ``src`` first on sys.path."""

from pathlib import Path

_root_config = Path(__file__).resolve().parents[1] / "config.py"
exec(compile(_root_config.read_text(encoding="utf-8"), str(_root_config), "exec"))
