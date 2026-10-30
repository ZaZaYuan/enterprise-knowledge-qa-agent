"""Validated, read-only tools exposed to the model."""

from __future__ import annotations

from .store import DocumentStore


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "按问题检索企业文档，返回文档 ID、范围、版本和摘要。回答前先检索，相关文档须读取原文。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索问题或改写后的查询"},
                    "top_k": {"type": "integer", "description": "最多返回多少条，1 到 8"},
                    "basis": {"type": "string", "description": "选择此动作的简短可公开依据，不包含内部推理过程"},
                },
                "required": ["query", "basis"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_doc",
            "description": "按文档 ID 读取完整原文、版本、适用范围和结构化声明。引用前必须读取。",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string"},
                    "basis": {"type": "string", "description": "选择此动作的简短可公开依据"},
                },
                "required": ["doc_id", "basis"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_conflicts",
            "description": "核对多份原文的同主题声明、适用范围和显式替代关系。发现相同主题的候选文档时应调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_ids": {"type": "array", "items": {"type": "string"}},
                    "basis": {"type": "string", "description": "选择此动作的简短可公开依据"},
                },
                "required": ["doc_ids", "basis"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_answer",
            "description": "结束任务，提交有依据的回答、冲突说明、资料不足或工具故障状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["answered", "conflict", "insufficient", "tool_error"]},
                    "answer": {"type": "string"},
                    "citations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"doc_id": {"type": "string"}, "quote": {"type": "string"}},
                            "required": ["doc_id", "quote"],
                            "additionalProperties": False,
                        },
                    },
                    "missing_info": {"type": "array", "items": {"type": "string"}},
                    "basis": {"type": "string", "description": "结束或追问的简短可公开依据"},
                },
                "required": ["status", "answer", "citations", "missing_info", "basis"],
                "additionalProperties": False,
            },
        },
    },
]


class ToolExecutor:
    def __init__(self, store: DocumentStore, fail_tool: str | None = None):
        self.store = store
        self.fail_tool = fail_tool

    def execute(self, name: str, arguments: dict) -> dict:
        if name == self.fail_tool:
            raise RuntimeError(f"{name} 暂时不可用（演示故障）")
        if name == "search_docs":
            query = arguments.get("query")
            if not isinstance(query, str) or not query.strip() or len(query) > 300:
                raise ValueError("query 必须是 1～300 字符的非空文本")
            top_k = arguments.get("top_k", 5)
            if not isinstance(top_k, int) or not 1 <= top_k <= 8:
                raise ValueError("top_k 必须在 1～8 之间")
            return {"matches": self.store.search(query, top_k)}
        if name == "read_doc":
            doc_id = arguments.get("doc_id")
            if not isinstance(doc_id, str):
                raise ValueError("doc_id 必须是字符串")
            return {"document": self.store.read(doc_id)}
        if name == "check_conflicts":
            doc_ids = arguments.get("doc_ids")
            if not isinstance(doc_ids, list) or not all(isinstance(x, str) for x in doc_ids):
                raise ValueError("doc_ids 必须是文档 ID 数组")
            return self.store.check_conflicts(doc_ids)
        raise ValueError(f"不支持的工具：{name}")
