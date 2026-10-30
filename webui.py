"""Local showcase UI: python webui.py --provider deepseek."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from knowledge_agent.web import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
