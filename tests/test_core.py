"""Тесты: python -m pytest -q"""
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["RELOKOT_MOCK"] = "1"

import ai  # noqa: E402
import sources  # noqa: E402
from scoring import detect_country, detect_languages, detect_min_experience  # noqa: E402

PROFILE = {"sector": "it", "regions": ["eu"], "english": "B2", "german": "none", "experience": 3}


def test_country():
    assert detect_country("München, Bayern") == "DE"
    assert detect_country("Remote - New York") == "US"
    assert detect_country("Kraków") == "PL"
    assert detect_country("Anywhere") is None


def test_languages():
    assert detect_languages("Dev", "Fluent English, German is a plus") == ("B2", "none")
    assert detect_languages("Dev", "fluent German (C1) and English")[1] == "C1"
    de = "Wir suchen Sie für unser Team und die Pflege. Sie haben sehr gute Deutschkenntnisse (B2) und wir freuen uns " * 3
    assert detect_languages("Pflegefachkraft", de) == ("none", "B2")


def test_experience():
    assert detect_min_experience("Backend", "3+ years of experience") == 3
    assert detect_min_experience("Senior Engineer", "") == 5
    assert detect_min_experience("Junior QA", "") == 0


def test_search_mock():
    r = asyncio.run(sources.search_jobs(PROFILE))
    by_title = {j["title"]: j for j in r["jobs"]}
    backend = by_title["Backend Engineer (Python) – Visa Sponsorship"]
    assert backend["visa"] and backend["reloc"] and backend["match"]["score"] >= 90
    scam = next(j for j in r["jobs"] if "guaranteed visa" in j["title"])
    assert scam["flagged"] and scam["s"]["rel"] <= 2 and scam["match"]["score"] <= 10
    react = by_title["Senior Frontend Developer (React)"]
    assert react["visa_denied"] and not react["visa"]


def test_query_filter():
    r = asyncio.run(sources.search_jobs(PROFILE, query="kubernetes"))
    assert [j["title"] for j in r["jobs"]] == ["DevOps Engineer (Kubernetes)"]


def test_ai_parsing_with_pause_turn(monkeypatch):
    """Проверяем разбор ответа Claude API, включая pause_turn и проверку источников."""
    monkeypatch.setenv("RELOKOT_MOCK", "0")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    answer = [{"country_code": "DE", "name": "Тест", "type": "work", "summary_ru": "x", "requirements_ru": ["a"],
               "fit_ru": {"ok": ["ok"], "no": []}, "match": 90, "scores": {"rel": 10, "ease": 7, "speed": 7, "cost": 6, "pr": 9},
               "official_url": "https://www.make-it-in-germany.com/x", "sources": []},
              {"country_code": "PL", "name": "Не проверено", "type": "work", "official_url": "https://unknown.example/x",
               "scores": {"rel": 10}}]
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return httpx.Response(200, json={"stop_reason": "pause_turn", "content": [
                {"type": "server_tool_use", "id": "s1", "name": "web_search", "input": {"query": "q"}},
                {"type": "web_search_tool_result", "tool_use_id": "s1",
                 "content": [{"type": "web_search_result", "url": "https://make-it-in-germany.com/a", "title": "t"}]}]})
        return httpx.Response(200, json={"stop_reason": "end_turn", "content": [
            {"type": "text", "text": "```json\n" + json.dumps(answer, ensure_ascii=False) + "\n```"}]})

    real = httpx.AsyncClient
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    ai._cache.clear()
    r = asyncio.run(ai.search_programs(PROFILE, refresh=True))
    assert len(calls) == 2 and calls[1]["messages"][-1]["role"] == "assistant"
    de, pl = r["programs"]
    assert de["verified"] and de["s"]["rel"] == 10 and de["flag"] == "🇩🇪"
    assert not pl["verified"] and pl["s"]["rel"] <= 5


def test_events_mock():
    ai._cache.clear()
    r = asyncio.run(ai.search_events(PROFILE, refresh=True))
    assert r["events"] and all(e["url"].startswith("https://") for e in r["events"])
