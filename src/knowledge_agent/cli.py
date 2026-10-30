"""Reproducible CLI entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import KnowledgeAgent
from .providers import DeepSeekClient, MockClient, ModelError
from .store import DocumentStore

ROOT = Path(__file__).resolve().parents[2]


def render(result: dict) -> str:
    labels = {
        "answered": "已回答", "conflict": "资料冲突，待确认", "insufficient": "资料不足",
        "tool_error": "工具故障", "model_error": "模型故障", "incomplete": "未完成",
    }
    lines = [
        "=" * 66,
        "企业知识问答 Agent  |  " + labels.get(result["status"], result["status"]),
        "=" * 66,
        "问题  " + result["question"],
        "答复  " + result["answer"],
    ]
    if result["citations"]:
        lines.append("\n依据")
        for index, item in enumerate(result["citations"], 1):
            lines.append(f"  {index}. [{item['doc_id']}] {item['quote']}")
    if result["missing_info"]:
        lines.append("\n待补充")
        lines.extend("  - " + item for item in result["missing_info"])
    lines.append(f"\n模型 {result['model']}  ·  决策轮次 {result['steps']}  ·  工具调用 {result['tool_calls']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="可追溯的企业知识问答 Agent")
    sub = parser.add_subparsers(dest="command", required=True)
    ask = sub.add_parser("ask", help="对合成制度资料提问")
    ask.add_argument("question", help="自然语言问题")
    ask.add_argument("--provider", choices=["deepseek", "mock"], default="deepseek")
    ask.add_argument("--trace", type=Path, help="保存完整 JSON 输出与执行记录")
    ask.add_argument("--history", type=Path, help="可选：包含前序 user/assistant 消息的 JSON 文件")
    ask.add_argument("--max-steps", type=int, default=9)
    ask.add_argument("--max-tools", type=int, default=12)
    ask.add_argument("--fail-tool", choices=["search_docs", "read_doc", "check_conflicts"], help="仅用于故障演示")
    sub.add_parser("list-docs", help="列出合成文档 ID 和版本")
    args = parser.parse_args(argv)
    store = DocumentStore(ROOT / "data" / "documents.json")
    if args.command == "list-docs":
        for doc in store.docs.values():
            print(f"{doc['id']:4}  {doc['version']}  {doc['title']}  |  {doc['scope']}")
        return 0
    if args.max_steps < 1 or args.max_tools < 1:
        parser.error("执行上限必须大于 0")
    try:
        model = DeepSeekClient() if args.provider == "deepseek" else MockClient()
    except ModelError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        history = json.loads(args.history.read_text(encoding="utf-8")) if args.history else []
    except (OSError, ValueError) as exc:
        parser.error("无法读取历史 JSON：" + str(exc))
    result = KnowledgeAgent(
        store, model, max_steps=args.max_steps, max_tool_calls=args.max_tools,
        fail_tool=args.fail_tool,
    ).run(args.question, history=history)
    print(render(result))
    if args.trace:
        args.trace.parent.mkdir(parents=True, exist_ok=True)
        args.trace.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\nTrace 已保存：" + str(args.trace.resolve()))
    return 0 if result["status"] in {"answered", "conflict", "insufficient"} else 1
