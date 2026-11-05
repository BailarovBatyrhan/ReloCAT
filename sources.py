"""
Источники вакансий. Каждый источник:
  1) скачивает данные из открытого API,
  2) приводит их к общему формату (normalize_*),
  3) кладёт в кэш, чтобы не дёргать сайт слишком часто.

Чтобы добавить новый источник — напиши функцию fetch_xxx и добавь её в search_jobs().
"""
import asyncio
import os
import re
import time
from datetime import datetime, timezone

import httpx

import mock_data
from scoring import COUNTRIES, analyze_job, detect_country, match_job, strip_html

UA = {"User-Agent": "Relokot/0.2 (personal relocation helper)", "Accept": "application/json"}
CACHE_TTL = 30 * 60  # 30 минут
_cache: dict = {}


def mock_mode() -> bool:
    return os.environ.get("RELOKOT_MOCK") == "1"


async def cached_get(client: httpx.AsyncClient, url: str, params: dict | None = None):
    key = url + "?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()) if "key" not in k)
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    r = await client.get(url, params=params, headers=UA, timeout=25)
    r.raise_for_status()
    data = r.json()
    _cache[key] = (time.time() + CACHE_TTL, data)
    return data


def _dt_from_unix(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _dt_from_iso(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00").replace(" ", "T"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _base(source, sid, title, company, location, country, remote, url, desc, tags, posted_at, salary="", salary_month_eur=0):
    c = COUNTRIES.get(country)
    return {
        "id": f"{source}-{sid}",
        "kind": "job",
        "live": True,
        "source": source,
        "title": (title or "").strip(),
        "company": (company or "").strip(),
        "city": location or ("Удалённо" if remote else ""),
        "country": c[0] if c else ("Удалённо" if remote else "—"),
        "country_code": country,
        "flag": c[1] if c else ("🌍" if remote else "🏳️"),
        "region": c[2] if c else ("any" if remote else "other"),
        "remote": bool(remote),
        "url": url,
        "description": desc,
        "desc": (desc[:420] + "…") if len(desc) > 420 else desc,
        "tags": [str(t) for t in (tags or [])][:8],
        "posted_at": posted_at,
        "salary": salary or "Зарплата не указана",
        "salary_month_eur": salary_month_eur,
        "program": None,
    }


# ---------- Arbeitnow: вакансии в Европе (в основном Германия), без ключа ----------
ARBEITNOW = "https://www.arbeitnow.com/api/job-board-api"


def normalize_arbeitnow(j: dict) -> dict:
    loc = j.get("location") or ""
    remote = bool(j.get("remote"))
    country = detect_country(loc) or (None if remote and not loc else "DE")
    desc = strip_html(j.get("description", ""))
    return _base("arbeitnow", j.get("slug") or j.get("url"), j.get("title"), j.get("company_name"), loc,
                 country, remote, j.get("url"), desc, (j.get("tags") or []) + (j.get("job_types") or []),
                 _dt_from_unix(j.get("created_at")))


async def fetch_arbeitnow(client, pages=3):
    if mock_mode():
        payloads = [mock_data.ARBEITNOW]
    else:
        payloads = await asyncio.gather(*[cached_get(client, ARBEITNOW, {"page": p}) for p in range(1, pages + 1)], return_exceptions=True)
        errors = [p for p in payloads if isinstance(p, Exception)]
        payloads = [p for p in payloads if isinstance(p, dict)]
        if not payloads:
            raise errors[0]
    jobs = [normalize_arbeitnow(j) for p in payloads for j in (p.get("data") or [])]
    return jobs


# ---------- Jobicy: удалённые вакансии, без ключа ----------
JOBICY = "https://jobicy.com/api/v2/remote-jobs"


def normalize_jobicy(j: dict) -> dict:
    geo = j.get("jobGeo") or j.get("geo") or "Anywhere"
    g = geo.lower()
    scope = "anywhere" if re.search(r"anywhere|worldwide|global", g) else ("europe" if re.search(r"europe|emea|eu\b", g) else "country")
    country = detect_country(geo) if scope == "country" else None
    smin, smax = j.get("annualSalaryMin") or j.get("salaryMin"), j.get("annualSalaryMax") or j.get("salaryMax")
    cur = j.get("salaryCurrency") or ""
    salary = f"{smin}–{smax} {cur} / год" if smin and smax else ""
    month_eur = int(float(smax) / 12) if smax and str(smax).replace(".", "").isdigit() else 0
    desc = strip_html(j.get("jobDescription") or j.get("jobExcerpt") or "")
    tags = (j.get("jobIndustry") or []) + (j.get("jobType") or []) + ([j["jobLevel"]] if j.get("jobLevel") else [])
    job = _base("jobicy", j.get("id"), j.get("jobTitle") or j.get("title"), j.get("companyName"), "Удалённо · " + geo,
                country, True, j.get("url"), desc, tags, _dt_from_iso(j.get("pubDate")), salary, month_eur)
    job["remote_scope"] = scope
    job["remote_geo"] = geo
    if scope == "europe":
        job["region"] = "eu"
    return job


async def fetch_jobicy(client, query: str, regions: list[str]):
    geos = ["anywhere"] + (["europe"] if "eu" in regions else []) + (["canada"] if "na" in regions else [])
    if mock_mode():
        payloads = [mock_data.JOBICY]
    else:
        params = [{"count": 50, "geo": g} | ({"tag": query[:50]} if 3 <= len(query) else {}) for g in geos]
        payloads = await asyncio.gather(*[cached_get(client, JOBICY, p) for p in params], return_exceptions=True)
        payloads = [p for p in payloads if isinstance(p, dict)]
        if not payloads:
            raise RuntimeError("Jobicy не ответил")
    return [normalize_jobicy(j) for p in payloads for j in (p.get("jobs") or [])]


# ---------- Adzuna: большой агрегатор, нужен бесплатный ключ ----------
ADZUNA = "https://api.adzuna.com/v1/api/jobs/{cc}/search/1"
ADZUNA_BY_REGION = {"eu": ["de", "nl", "pl", "at", "gb", "fr", "es", "it", "be", "ch"], "na": ["ca", "us"]}


def adzuna_enabled():
    return bool(os.environ.get("ADZUNA_APP_ID") and os.environ.get("ADZUNA_APP_KEY"))


def normalize_adzuna(j: dict, cc: str) -> dict:
    country = cc.upper()
    loc = (j.get("location") or {}).get("display_name", "")
    smin, smax = j.get("salary_min"), j.get("salary_max")
    salary = f"{int(smin):,}–{int(smax):,} / год".replace(",", " ") if smin and smax else ""
    return _base("adzuna", j.get("id"), j.get("title"), (j.get("company") or {}).get("display_name"), loc,
                 country, False, j.get("redirect_url"), strip_html(j.get("description", "")),
                 [(j.get("category") or {}).get("label", "")], _dt_from_iso(j.get("created")),
                 salary, int(smax / 12) if smax else 0)


async def fetch_adzuna(client, query: str, regions: list[str], countries: list[str]):
    ccs = [c.lower() for c in countries] or [cc for r in regions for cc in ADZUNA_BY_REGION.get(r, [])][:4]
    ccs = ccs[:4]
    params = {"app_id": os.environ["ADZUNA_APP_ID"], "app_key": os.environ["ADZUNA_APP_KEY"],
              "results_per_page": 30, "what": query or "relocation", "content-type": "application/json"}
    payloads = await asyncio.gather(*[cached_get(client, ADZUNA.format(cc=cc), params) for cc in ccs], return_exceptions=True)
    out = []
    for cc, p in zip(ccs, payloads):
        if isinstance(p, dict):
            out += [normalize_adzuna(j, cc) for j in p.get("results", [])]
    return out


# ---------- общий поиск ----------
SECTOR_QUERY = {"it": "developer", "med": "nurse", "eng": "engineer", "service": "logistics", "edu": "teacher", "other": ""}


def _text_match(job, words):
    hay = (job["title"] + " " + " ".join(job["tags"]) + " " + job["description"][:1500]).lower()
    return all(w in hay for w in words)


async def search_jobs(profile: dict, query: str = "", countries: list[str] | None = None) -> dict:
    query = (query or "").strip()
    regions = profile.get("regions") or ["eu"]
    tag_query = query or SECTOR_QUERY.get(profile.get("sector", "other"), "")
    status = []
    jobs: list[dict] = []

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = {"arbeitnow": fetch_arbeitnow(client), "jobicy": fetch_jobicy(client, tag_query, regions)}
        if adzuna_enabled() and not mock_mode():
            tasks["adzuna"] = fetch_adzuna(client, tag_query, regions, countries or [])
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for name, res in zip(tasks.keys(), results):
        if isinstance(res, Exception):
            status.append({"source": name, "ok": False, "count": 0, "error": f"{type(res).__name__}: {str(res)[:160]}"})
        else:
            status.append({"source": name, "ok": True, "count": len(res)})
            jobs += res
    if not adzuna_enabled():
        status.append({"source": "adzuna", "ok": False, "count": 0, "error": "нет ключа (необязательно)"})

    # фильтр по запросу: все слова запроса должны встретиться
    words = [w for w in re.split(r"\s+", query.lower()) if len(w) >= 2]
    if words:
        jobs = [j for j in jobs if _text_match(j, words)]

    # убираем дубликаты (одна вакансия на нескольких сайтах)
    seen, unique = set(), []
    for j in jobs:
        k = (j["title"].lower(), j["company"].lower())
        if k not in seen:
            seen.add(k)
            unique.append(j)

    if countries:
        cc = {c.upper() for c in countries}
        unique = [j for j in unique if j["country_code"] in cc or j["remote"]]

    for j in unique:
        analyze_job(j)
        j["match"] = match_job(j, profile)
        j.pop("posted_at", None)
        j.pop("description", None)
    unique.sort(key=lambda j: (-j["match"]["score"], -j["s"]["rel"]))
    return {"jobs": unique[:150], "sources": status, "total": len(unique)}
