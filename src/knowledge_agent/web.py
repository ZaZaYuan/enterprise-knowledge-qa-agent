"""Small localhost-only HTTP server for inspecting answers and tool traces."""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .agent import KnowledgeAgent
from .providers import DeepSeekClient, MockClient, ModelError
from .store import DocumentStore

ROOT = Path(__file__).resolve().parents[2]
ASSETS = {
    "/": (ROOT / "web" / "index.html", "text/html; charset=utf-8"),
    "/style.css": (ROOT / "web" / "style.css", "text/css; charset=utf-8"),
    "/app.js": (ROOT / "web" / "app.js", "text/javascript; charset=utf-8"),
}


def make_handler(provider: str):
    store = DocumentStore(ROOT / "data" / "documents.json")

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, data: dict):
            self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/health":
                self._json(200, {"provider": provider, "ready": provider == "mock" or bool(os.environ.get("DEEPSEEK_API_KEY")), "document_count": len(store.docs)})
                return
            asset = ASSETS.get(path)
            if asset is None:
                self._json(404, {"error": "页面不存在"})
                return
            file_path, content_type = asset
            self._send(200, file_path.read_bytes(), content_type)

        def do_POST(self):
            if urlparse(self.path).path != "/api/ask":
                self._json(404, {"error": "接口不存在"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise ValueError("请求体须为 1～65536 字节")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("请求体必须是 JSON 对象")
                question = data.get("question")
                history = data.get("history", [])
                if not isinstance(question, str) or not isinstance(history, list):
                    raise ValueError("question/history 格式错误")
                model = DeepSeekClient() if provider == "deepseek" else MockClient()
                result = KnowledgeAgent(store, model).run(question, history=history)
                self._json(200, result)
            except (ValueError, ModelError) as exc:
                self._json(400, {"error": str(exc)})
            except Exception:
                self._json(500, {"error": "服务暂时不可用，请查看本地终端日志"})

        def log_message(self, fmt: str, *args):
            # Do not print questions, trace data or credentials in server logs.
            print("HTTP", self.command, urlparse(self.path).path, args[1] if len(args) > 1 else "")

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="企业知识问答 Agent 本地展示界面")
    parser.add_argument("--provider", choices=["deepseek", "mock"], default="deepseek")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("端口必须在 1～65535 之间")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.provider))
    print(f"Local showcase: http://127.0.0.1:{args.port}  provider={args.provider}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
