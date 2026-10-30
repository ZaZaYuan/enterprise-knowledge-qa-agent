"""Run with `python main.py ask "问题"`."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from knowledge_agent.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
