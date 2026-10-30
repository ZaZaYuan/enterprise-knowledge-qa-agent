import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_agent.agent import KnowledgeAgent
from knowledge_agent.providers import DeepSeekClient, MockClient
from knowledge_agent.store import DocumentStore


class BadCitationClient(MockClient):
    def complete(self, messages, tools):
        if not any(m["role"] == "tool" for m in messages):
            return self._call("search_docs", {"query": "请假提前几天", "basis": "先检索"})
        if not any("document" in json.loads(m["content"]) for m in messages if m["role"] == "tool"):
            return self._call("read_doc", {"doc_id": "L01", "basis": "核对原文"})
        return self._call("submit_answer", {
            "status": "answered", "answer": "普通事假提前 99 天申请。",
            "citations": [{"doc_id": "L01", "quote": "普通事假提前 99 天申请。"}],
            "missing_info": [], "basis": "尝试提交无效引用",
        })


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = DocumentStore(ROOT / "data" / "documents.json")

    def test_normal_answer_is_grounded(self):
        result = KnowledgeAgent(self.store, MockClient()).run("普通事假要提前几天申请？")
        self.assertEqual(result["status"], "answered")
        self.assertEqual([event["action"] for event in result["trace"]], ["search_docs", "read_doc", "submit_answer"])
        self.assertEqual(result["citations"][0]["doc_id"], "L01")

    def test_unresolved_conflict_is_not_silently_resolved_by_date(self):
        result = KnowledgeAgent(self.store, MockClient()).run("报销期限多久？")
        self.assertEqual(result["status"], "conflict")
        self.assertEqual({item["doc_id"] for item in result["citations"]}, {"D01", "D02"})
        self.assertIn("check_conflicts", [event["action"] for event in result["trace"]])
        self.assertEqual(self.store.check_conflicts(["D01", "D02"])["conflicts"][0]["resolution"], "unresolved")

    def test_unrelated_scope_does_not_create_false_conflict(self):
        self.assertEqual(self.store.check_conflicts(["D01", "D03"])["conflicts"], [])

    def test_missing_detail_asks_for_source(self):
        result = KnowledgeAgent(self.store, MockClient()).run("每月可以远程办公几天？")
        self.assertEqual(result["status"], "insufficient")
        self.assertIn("所在部门", result["missing_info"][0])

    def test_tool_failure_is_not_recorded_as_answer(self):
        result = KnowledgeAgent(self.store, MockClient(), fail_tool="search_docs").run("报销期限多久？")
        self.assertEqual(result["status"], "tool_error")
        self.assertFalse(result["citations"])
        self.assertIn("error", result["trace"][0]["result"])

    def test_invalid_quote_is_rejected_even_if_model_repeats_it(self):
        result = KnowledgeAgent(self.store, BadCitationClient(), max_steps=4).run("请假提前几天？")
        self.assertEqual(result["status"], "incomplete")
        self.assertTrue(any("引用片段不在" in item["result"].get("error", "") for item in result["trace"]))

    def test_execution_limit_returns_explicit_incomplete_state(self):
        result = KnowledgeAgent(self.store, MockClient(), max_tool_calls=1).run("报销期限多久？")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["tool_calls"], 1)

    def test_uncited_document_mentioned_in_answer_is_rejected(self):
        agent = KnowledgeAgent(self.store, MockClient())
        value = {
            "status": "answered", "answer": "L01 写明提前两天，D03 另有规定。",
            "citations": [{"doc_id": "L01", "quote": "普通事假应至少提前 2 个工作日向直属主管提交申请。"}],
            "missing_info": [],
        }
        error = agent._validate_final(value, True, self.store.search("事假"), {"L01"}, [], False)
        self.assertIn("D03", error)

    def test_uncited_value_from_other_policy_is_rejected(self):
        agent = KnowledgeAgent(self.store, MockClient())
        value = {
            "status": "answered", "answer": "普通事假提前两天；差旅返程后 10 个自然日。",
            "citations": [{"doc_id": "L01", "quote": "普通事假应至少提前 2 个工作日向直属主管提交申请。"}],
            "missing_info": [],
        }
        error = agent._validate_final(value, True, self.store.search("事假"), {"L01"}, [], False)
        self.assertIn("D03", error)

    def test_deepseek_adapter_sends_required_tool_call_without_leaking_key(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"choices":[{"message":{"role":"assistant","tool_calls":[]}}]}'

        captured = []

        def fake_urlopen(request, timeout):
            captured.append(request)
            return FakeResponse()

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-only-token"}), patch(
            "knowledge_agent.providers.urllib.request.urlopen", side_effect=fake_urlopen
        ):
            response = DeepSeekClient().complete([{"role": "user", "content": "测试"}], [])
        self.assertEqual(response["role"], "assistant")
        payload = json.loads(captured[0].data)
        self.assertEqual(payload["tool_choice"], "required")
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertNotIn("test-only-token", captured[0].data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
