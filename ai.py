"""
ИИ-поиск программ переезда и событий: Claude с инструментом веб-поиска.

Нужен ключ ANTHROPIC_API_KEY в файле .env.
Каждый поиск стоит денег (токены + плата за веб-поиски), поэтому
результаты кэшируются на 12 часов для одинаковой анкеты.
"""
import hashlib
import json
import os
import re
import time
from datetime import date, timedelta
from urllib.parse import urlparse

import httpx

import mock_data
from scoring import COUNTRIES

API_URL = "https://api.anthropic.com/v1/messages"
CACHE_TTL = 12 * 3600
_cache: dict = {}


class AINotConfigured(Exception):
    pass


class AIError(Exception):
    pass


def ai_enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY")) or os.environ.get("RELOKOT_MOCK") == "1"


def _model():
    return os.environ.get("RELOKOT_MODEL", "claude-sonnet-5-5")


def extract_json(text: str):
    """Достаёт JSON-массив из ответа модели (даже если вокруг есть текст)."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise AIError("В ответе нет JSON-массива")
    return json.loads(text[start:end + 1])


async def ask_claude(prompt: str, max_searches: int = 8):
    """Возвращает (текст ответа, множество доменов, которые реально встретились в поиске)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise AINotConfigured("Добавь ANTHROPIC_API_KEY в файл .env")
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    messages = [{"role": "user", "content": prompt}]
    seen_domains: set[str] = set()
    text_parts: list[str] = []

    async with httpx.AsyncClient(timeout=300) as client:
        for _ in range(5):  # pause_turn: длинный поиск может прийти в несколько заходов
            r = await client.post(API_URL, headers=headers, json={
                "model": _model(),
                "max_tokens": 16000,
                "messages": messages,
                "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": max_searches}],
            })
            if r.status_code >= 400:
                raise AIError(f"Claude API {r.status_code}: {r.text[:300]}")
            data = r.json()
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "web_search_tool_result" and isinstance(block.get("content"), list):
                    for res in block["content"]:
                        if res.get("url"):
                            seen_domains.add(_domain(res["url"]))
            if data.get("stop_reason") == "pause_turn":
                messages.append({"role": "assistant", "content": data["content"]})
                continue
            break
    return "".join(text_parts), seen_domains


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except ValueError:
        return ""


def _safe_url(u):
    return u if isinstance(u, str) and u.startswith(("https://", "http://")) else None


def _score(v):
    try:
        return max(1, min(10, int(round(float(v)))))
    except (TypeError, ValueError):
        return 5


def _cache_key(kind, payload):
    return kind + hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


PROFILE_FIELDS = ["citizenship", "goal", "education", "english", "german", "sector", "experience", "budget", "family", "regions"]


def _profile_text(profile: dict) -> str:
    return json.dumps({k: profile.get(k) for k in PROFILE_FIELDS}, ensure_ascii=False)


PROGRAM_TYPES = {"job-search", "work", "study", "nomad", "talent", "business", "pr", "visa-free"}


async def search_programs(profile: dict, extra: str = "", refresh: bool = False) -> dict:
    key = _cache_key("prog", {"p": {k: profile.get(k) for k in PROFILE_FIELDS}, "x": extra})
    hit = _cache.get(key)
    if hit and hit[0] > time.time() and not refresh:
        return hit[1] | {"cached": True}

    if os.environ.get("RELOKOT_MOCK") == "1":
        raw, seen = mock_data.AI_PROGRAMS, {_domain(p["official_url"]) for p in mock_data.AI_PROGRAMS}
    else:
        today = date.today().isoformat()
        prompt = f"""You are a careful relocation research assistant. Today is {today}.
Use web search to find immigration / relocation programs that are CURRENTLY open and fit this person.
Person's profile (JSON, values are codes): {_profile_text(profile)}
Codes: goal work|study|remote|business; education school|vocational|bachelor|master|phd; english/german none|A1..C1;
budget low(<$3k)|mid($3-10k)|high(>$10k); regions eu|na|asia|near(Caucasus & nearby).
{('Extra wishes from the user: ' + extra) if extra else ''}

Rules:
- Prefer official government pages; open them via search to confirm the program still exists in {today[:4]}.
- Consider the person's citizenship (visa-free regimes, special agreements).
- Mention concrete thresholds (salary, income, savings) ONLY if you saw them in a source; add the year.
- Return 6 to 10 programs, best fit first.

Reply with ONLY a JSON array, no prose. Each item:
{{"country_code":"DE","name":"name in Russian (original name)","type":"job-search|work|study|nomad|talent|business|pr|visa-free",
"summary_ru":"2-3 sentences in Russian","requirements_ru":["2-5 short items in Russian"],
"fit_ru":{{"ok":["why it fits, Russian"],"no":["what doesn't fit, Russian"]}},"match":0-100,
"scores":{{"rel":1-10,"ease":1-10,"speed":1-10,"cost":1-10,"pr":1-10}},
"official_url":"https://... official page","sources":["https://..."],"checked_note_ru":"what you verified and the page's update date if visible"}}
Scores: rel = reliability of the source/program, ease = how few requirements and bureaucracy, speed = how fast to obtain,
cost = how cheap to start (10 = cheap), pr = how well it leads to permanent residence/citizenship."""
        text, seen = await ask_claude(prompt, max_searches=10)
        raw = extract_json(text)

    programs = []
    for i, p in enumerate(raw):
        if not isinstance(p, dict):
            continue
        url = _safe_url(p.get("official_url"))
        sources = [u for u in (p.get("sources") or []) if _safe_url(u)][:5]
        if not url and not sources:
            continue  # без ссылки на источник — не показываем
        cc = str(p.get("country_code", "")).upper()
        c = COUNTRIES.get(cc)
        s = p.get("scores") or {}
        scores = {k: _score(s.get(k)) for k in ("rel", "ease", "speed", "cost", "pr")}
        verified = _domain(url or sources[0]) in seen or any(_domain(u) in seen for u in sources)
        if not verified:
            scores["rel"] = min(scores["rel"], 5)  # ссылку не видели в результатах поиска → меньше доверия
        fit = p.get("fit_ru") or {}
        programs.append({
            "id": f"ai-{cc.lower()}-{i}-{hashlib.md5(str(p.get('name')).encode()).hexdigest()[:6]}",
            "kind": "program", "live": True,
            "flag": c[1] if c else "🌍", "country": c[0] if c else cc, "region": c[2] if c else "other",
            "name": str(p.get("name", "Программа"))[:160],
            "type": p.get("type") if p.get("type") in PROGRAM_TYPES else "work",
            "desc": str(p.get("summary_ru", ""))[:800],
            "need": [str(x)[:200] for x in (p.get("requirements_ru") or [])][:6],
            "match": {"score": max(0, min(100, int(p.get("match") or 50))),
                      "ok": [str(x) for x in fit.get("ok", [])][:4], "no": [str(x) for x in fit.get("no", [])][:4]},
            "s": scores, "url": url or sources[0], "site": _domain(url or sources[0]), "sources": sources,
            "verified": verified, "checked": str(p.get("checked_note_ru", ""))[:300],
        })
    result = {"programs": programs, "model": _model(), "searched_at": int(time.time())}
    _cache[key] = (time.time() + CACHE_TTL, result)
    return result


EVENT_CATS = {"deadline", "webinar", "fair", "docs"}


async def search_events(profile: dict, months: int = 4, refresh: bool = False) -> dict:
    key = _cache_key("ev", {"p": {k: profile.get(k) for k in PROFILE_FIELDS}, "m": months})
    hit = _cache.get(key)
    if hit and hit[0] > time.time() and not refresh:
        return hit[1] | {"cached": True}

    today = date.today()
    until = today + timedelta(days=30 * months)
    if os.environ.get("RELOKOT_MOCK") == "1":
        raw = mock_data.AI_EVENTS
    else:
        prompt = f"""You are a relocation research assistant. Today is {today.isoformat()}.
Use web search to find UPCOMING events between {today.isoformat()} and {until.isoformat()} useful for this person:
application deadlines (scholarships, universities, visa programs, lotteries), official webinars/info sessions,
and job fairs (online, or in the person's target regions).
Person's profile: {_profile_text(profile)}
Rules: include an event ONLY if you found its date on a web page, and give that page as url. 8-15 events, sorted by date.
Reply with ONLY a JSON array, no prose. Each item:
{{"date":"YYYY-MM-DD","title_ru":"short title in Russian","cat":"deadline|webinar|fair|docs","country_code":"DE","url":"https://...","note_ru":"one short line in Russian"}}"""
        text, _seen = await ask_claude(prompt, max_searches=10)
        raw = extract_json(text)

    events = []
    for i, e in enumerate(raw):
        if not isinstance(e, dict) or not _safe_url(e.get("url")):
            continue
        d = str(e.get("date", ""))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) or d < today.isoformat():
            continue
        events.append({
            "id": f"ai-ev-{d}-{i}", "date": d, "title": str(e.get("title_ru", "Событие"))[:160],
            "cat": e.get("cat") if e.get("cat") in EVENT_CATS else "webinar",
            "url": e["url"], "note": str(e.get("note_ru", ""))[:200], "found": True,
        })
    result = {"events": events, "searched_at": int(time.time())}
    _cache[key] = (time.time() + CACHE_TTL, result)
    return result
