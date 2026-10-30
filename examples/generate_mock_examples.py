"""Regenerate actual OFFLINE_MOCK outputs and traces, without API credentials."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_agent.agent import KnowledgeAgent
from knowledge_agent.cli import render
from knowledge_agent.providers import MockClient
from knowledge_agent.store import DocumentStore


CASES = {
    "01-normal": ("普通事假要提前几天申请？", None),
    "02-conflict": ("一般费用报销期限多久？", None),
    "03-insufficient": ("每月可以远程办公几天？", None),
    "04-tool-failure": ("一般费用报销期限多久？", "search_docs"),
    "05-paraphrase": ("事假需要提前多久报批？", None),
    "06-travel-scope": ("差旅报销应在返程后几天提交？", None),
}


def main():
    store = DocumentStore(ROOT / "data" / "documents.json")
    directory = ROOT / "examples" / "mock"
    directory.mkdir(parents=True, exist_ok=True)
    for name, (question, fail_tool) in CASES.items():
        result = KnowledgeAgent(store, MockClient(), fail_tool=fail_tool).run(question)
        (directory / f"{name}.input.json").write_text(
            json.dumps({"question": question, "provider": "OFFLINE_MOCK", "fail_tool": fail_tool}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (directory / f"{name}.output.txt").write_text(render(result) + "\n", encoding="utf-8")
        (directory / f"{name}.trace.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(name, result["status"], result["steps"], result["tool_calls"])


if __name__ == "__main__":
    main()
