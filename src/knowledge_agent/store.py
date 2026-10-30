"""Small, inspectable document store for the synthetic exam corpus."""

from __future__ import annotations

import json
import re
from pathlib import Path


def terms(value: str) -> set[str]:
    """Character bigrams work for Chinese without external tokenizers."""
    result: set[str] = set()
    for chunk in re.findall(r"[\u3400-\u9fff]+|[a-zA-Z0-9]+", value.lower()):
        if re.fullmatch(r"[\u3400-\u9fff]+", chunk):
            result.update(chunk[i : i + 2] for i in range(len(chunk) - 1))
            if len(chunk) == 1:
                result.add(chunk)
        else:
            result.add(chunk)
    return result


class DocumentStore:
    def __init__(self, path: Path):
        records = json.loads(path.read_text(encoding="utf-8"))
        self.docs = {item["id"]: item for item in records}
        if len(self.docs) != len(records):
            raise ValueError("文档 ID 重复")
        for doc in records:
            section_text = "\n".join(s["text"] for s in doc["sections"])
            for claim in doc["claims"]:
                if claim["quote"] not in section_text:
                    raise ValueError(f"{doc['id']} 的 claim 引文不在原文中")

    def get(self, doc_id: str) -> dict:
        if doc_id not in self.docs:
            raise ValueError(f"未知文档 ID: {doc_id}")
        return self.docs[doc_id]

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        query_terms = terms(query)
        if not query_terms:
            return []
        ranked: list[tuple[float, dict]] = []
        for doc in self.docs.values():
            title_terms = terms(doc["title"])
            body = " ".join(s["text"] for s in doc["sections"])
            body_terms = terms(body)
            score = 3 * len(query_terms & title_terms) + len(query_terms & body_terms)
            if score:
                ranked.append((float(score), doc))
        ranked.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
        return [
            {
                "doc_id": doc["id"],
                "title": doc["title"],
                "version": doc["version"],
                "scope": doc["scope"],
                "score": score,
                "preview": doc["sections"][0]["text"][:90],
                "claim_keys": sorted({claim["key"] for claim in doc["claims"]}),
            }
            for score, doc in ranked[: max(1, min(top_k, 8))]
        ]

    def read(self, doc_id: str) -> dict:
        return self.get(doc_id).copy()

    def check_conflicts(self, doc_ids: list[str]) -> dict:
        if not 2 <= len(doc_ids) <= 8 or len(set(doc_ids)) != len(doc_ids):
            raise ValueError("请提供 2～8 个不同的文档 ID")
        docs = [self.get(doc_id) for doc_id in doc_ids]
        conflicts: list[dict] = []
        for index, left in enumerate(docs):
            for right in docs[index + 1 :]:
                if left["scope"] != right["scope"]:
                    continue
                for a in left["claims"]:
                    for b in right["claims"]:
                        if a["key"] != b["key"] or a["value"] == b["value"]:
                            continue
                        explicit_override = (
                            right["id"] in left["supersedes"]
                            or left["id"] in right["supersedes"]
                        )
                        conflicts.append(
                            {
                                "key": a["key"],
                                "left": {"doc_id": left["id"], "value": a["value"], "quote": a["quote"]},
                                "right": {"doc_id": right["id"], "value": b["value"], "quote": b["quote"]},
                                "resolution": "explicit_supersession" if explicit_override else "unresolved",
                                "note": "仅凭版本日期不能认定新文档覆盖旧文档" if not explicit_override else "存在显式替代关系，请核对方向",
                            }
                        )
        return {"checked_ids": doc_ids, "conflicts": conflicts}
