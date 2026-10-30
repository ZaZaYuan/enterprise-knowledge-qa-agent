import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_agent.web import make_handler


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler("mock"))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def post(self, body):
        request = urllib.request.Request(
            self.base + "/api/ask", data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.load(response)

    def test_health_reports_mock_without_secret(self):
        with urllib.request.urlopen(self.base + "/api/health", timeout=5) as response:
            data = json.load(response)
        self.assertEqual(data["document_count"], 5)
        self.assertEqual(data["provider"], "mock")
        self.assertNotIn("key", data)

    def test_web_question_returns_evidence_and_trace(self):
        result = self.post({"question": "一般费用报销期限多久？", "history": []})
        self.assertEqual(result["status"], "conflict")
        self.assertEqual({x["doc_id"] for x in result["citations"]}, {"D01", "D02"})
        self.assertTrue(result["trace"])

    def test_web_follow_up_uses_history(self):
        history = json.loads((ROOT / "examples" / "context-history.json").read_text(encoding="utf-8"))
        result = self.post({"question": "那紧急情况呢？", "history": history})
        self.assertEqual(result["status"], "answered")
        self.assertIn("返岗后", result["answer"])


if __name__ == "__main__":
    unittest.main()
