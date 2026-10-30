"""DeepSeek Chat Completions adapter and an explicitly offline test double."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid


class ModelError(RuntimeError):
    pass


class DeepSeekClient:
    def __init__(self):
        self.key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not self.key:
            raise ModelError("未设置 DEEPSEEK_API_KEY；请仅在本机环境变量中配置")
        self.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash").strip()
        self.base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        if not self.base_url.startswith("https://"):
            raise ModelError("DEEPSEEK_BASE_URL 必须使用 HTTPS")

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "required",
            "thinking": {"type": "disabled"},
            "temperature": 0,
            "max_tokens": 900,
            "stream": False,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=body,
            headers={
                "Authorization": "Bearer " + self.key,
                "Content-Type": "application/json",
                "User-Agent": "enterprise-knowledge-agent/0.1",
            },
            method="POST",
        )
        for attempt in range(2):
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    data = json.loads(response.read().decode("utf-8"))
                return data["choices"][0]["message"]
            except urllib.error.HTTPError as exc:
                # Never include request headers or the API key in errors or traces.
                if exc.code in (429, 500, 502, 503, 504) and attempt == 0:
                    time.sleep(1)
                    continue
                raise ModelError(f"DeepSeek API 返回 HTTP {exc.code}") from None
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, IndexError) as exc:
                raise ModelError(f"模型请求失败：{type(exc).__name__}") from None
        raise ModelError("模型请求重试后仍失败")


class MockClient:
    """Offline script: demonstrates orchestration only, never model quality."""

    model = "OFFLINE_MOCK"

    @staticmethod
    def _call(name: str, arguments: dict) -> dict:
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "mock-" + uuid.uuid4().hex[:12],
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
                }
            ],
        }

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        question = next(m["content"] for m in reversed(messages) if m["role"] == "user")
        tool_messages = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        if not tool_messages:
            return self._call("search_docs", {"query": question, "top_k": 5, "basis": "先查找相关制度"})
        if tool_messages[-1].get("error"):
            return self._call("submit_answer", {
                "status": "tool_error", "answer": "检索工具暂时不可用，无法核实制度原文。",
                "citations": [], "missing_info": ["请稍后重试检索"], "basis": "工具故障使证据不足",
            })
        read_ids = {
            result["document"]["id"]
            for result in tool_messages
            if "document" in result
        }
        if "紧急" in question and any(
            "事假" in m["content"] for m in messages if m["role"] == "user"
        ):
            if "L01" not in read_ids:
                return self._call("read_doc", {"doc_id": "L01", "basis": "结合前文读取事假紧急情况条款"})
            return self._call("submit_answer", {
                "status": "answered", "answer": "普通事假遇突发紧急情况，可先电话告知主管，并在返岗后补交申请。",
                "citations": [{"doc_id": "L01", "quote": "突发紧急情况可先电话告知主管，并在返岗后补交申请。"}],
                "missing_info": [], "basis": "L01 原文直接说明紧急情况",
            })
        if "差旅" in question and "报销" in question:
            if "D03" not in read_ids:
                return self._call("read_doc", {"doc_id": "D03", "basis": "读取差旅报销适用范围和期限"})
            return self._call("submit_answer", {
                "status": "answered", "answer": "差旅费用应在返程后 10 个自然日内提交报销申请。",
                "citations": [{"doc_id": "D03", "quote": "差旅费用应在返程后 10 个自然日内提交报销申请。"}],
                "missing_info": [], "basis": "差旅制度原文直接回答该问题",
            })
        if "报销" in question and "差旅" not in question:
            for doc_id in ("D01", "D02"):
                if doc_id not in read_ids:
                    return self._call("read_doc", {"doc_id": doc_id, "basis": "核对报销期限的原文"})
            if not any("checked_ids" in result for result in tool_messages):
                return self._call("check_conflicts", {"doc_ids": ["D01", "D02"], "basis": "两份制度给出不同期限"})
            return self._call("submit_answer", {
                "status": "conflict",
                "answer": "D01 规定 30 个自然日，D02 规定 15 个自然日；两份材料适用范围相同，未说明替代关系，暂不能确定统一期限。请确认应采用哪份制度。",
                "citations": [
                    {"doc_id": "D01", "quote": "所有正式员工应在费用发生后 30 个自然日内提交一般费用报销申请。"},
                    {"doc_id": "D02", "quote": "一般费用报销应在费用发生后 15 个自然日内提交，适用于所有正式员工。"},
                ],
                "missing_info": ["D01 与 D02 的优先级或替代关系"],
                "basis": "冲突检查结果为 unresolved",
            })
        if "请假" in question or "事假" in question:
            if "L01" not in read_ids:
                return self._call("read_doc", {"doc_id": "L01", "basis": "读取请假制度原文"})
            return self._call("submit_answer", {
                "status": "answered", "answer": "普通事假至少提前 2 个工作日向直属主管申请。",
                "citations": [{"doc_id": "L01", "quote": "普通事假应至少提前 2 个工作日向直属主管提交申请。"}],
                "missing_info": [], "basis": "原文直接回答该问题",
            })
        if "远程" in question:
            if "R01" not in read_ids:
                return self._call("read_doc", {"doc_id": "R01", "basis": "核对远程办公说明"})
            return self._call("submit_answer", {
                "status": "insufficient", "answer": "现有说明没有规定每月可远程办公的天数，请向所在部门确认。",
                "citations": [{"doc_id": "R01", "quote": "本说明未规定每月可远程办公的天数。"}],
                "missing_info": ["所在部门关于每月远程办公天数的通知"],
                "basis": "文档明确未给出所问数值",
            })
        return self._call("submit_answer", {
            "status": "insufficient", "answer": "当前资料中没有足够依据回答该问题。",
            "citations": [], "missing_info": ["相关制度或 FAQ"], "basis": "检索未得到可用原文",
        })
