"""
Скоринг вакансий: определяем страну, язык, визу, «красные флаги»,
ставим оценки 1–10 и считаем совпадение с анкетой пользователя.

Все правила — эвристики. Их легко менять: каждое правило — одна строка.
"""
import re
from datetime import datetime, timezone

# код страны: (название, флаг, регион, базовая «перспектива ПМЖ» 1–10)
COUNTRIES = {
    "DE": ("Германия", "🇩🇪", "eu", 9), "NL": ("Нидерланды", "🇳🇱", "eu", 7),
    "AT": ("Австрия", "🇦🇹", "eu", 7), "CH": ("Швейцария", "🇨🇭", "eu", 6),
    "PL": ("Польша", "🇵🇱", "eu", 6), "CZ": ("Чехия", "🇨🇿", "eu", 6),
    "FR": ("Франция", "🇫🇷", "eu", 7), "ES": ("Испания", "🇪🇸", "eu", 7),
    "PT": ("Португалия", "🇵🇹", "eu", 7), "IT": ("Италия", "🇮🇹", "eu", 6),
    "IE": ("Ирландия", "🇮🇪", "eu", 8), "GB": ("Великобритания", "🇬🇧", "eu", 6),
    "BE": ("Бельгия", "🇧🇪", "eu", 7), "SE": ("Швеция", "🇸🇪", "eu", 7),
    "DK": ("Дания", "🇩🇰", "eu", 6), "FI": ("Финляндия", "🇫🇮", "eu", 7),
    "NO": ("Норвегия", "🇳🇴", "eu", 6), "EE": ("Эстония", "🇪🇪", "eu", 6),
    "LT": ("Литва", "🇱🇹", "eu", 6), "LV": ("Латвия", "🇱🇻", "eu", 6),
    "LU": ("Люксембург", "🇱🇺", "eu", 7), "GR": ("Греция", "🇬🇷", "eu", 6),
    "HU": ("Венгрия", "🇭🇺", "eu", 5), "RO": ("Румыния", "🇷🇴", "eu", 6),
    "CY": ("Кипр", "🇨🇾", "eu", 6), "RS": ("Сербия", "🇷🇸", "eu", 5),
    "GE": ("Грузия", "🇬🇪", "near", 3), "AM": ("Армения", "🇦🇲", "near", 4),
    "TR": ("Турция", "🇹🇷", "near", 4), "AE": ("ОАЭ", "🇦🇪", "asia", 2),
    "US": ("США", "🇺🇸", "na", 5), "CA": ("Канада", "🇨🇦", "na", 9),
}

_ALIASES = {
    "DE": "germany deutschland berlin munich münchen muenchen hamburg frankfurt cologne köln koeln stuttgart düsseldorf duesseldorf leipzig dresden hannover nuremberg nürnberg bonn karlsruhe mannheim essen dortmund bremen potsdam heidelberg",
    "NL": "netherlands holland amsterdam rotterdam utrecht eindhoven den_haag the_hague groningen",
    "AT": "austria österreich vienna wien graz linz salzburg",
    "CH": "switzerland schweiz zurich zürich geneva genf basel bern lausanne",
    "PL": "poland polska warsaw warszawa krakow kraków wroclaw wrocław gdansk gdańsk poznan poznań lodz łódź",
    "CZ": "czechia czech_republic prague praha brno",
    "FR": "france paris lyon toulouse marseille",
    "ES": "spain españa madrid barcelona valencia malaga málaga",
    "PT": "portugal lisbon lisboa porto",
    "IT": "italy italia milan milano rome roma turin torino",
    "IE": "ireland dublin cork galway",
    "GB": "united_kingdom england scotland london manchester edinburgh",
    "BE": "belgium brussels bruxelles antwerp ghent",
    "SE": "sweden stockholm gothenburg malmö",
    "DK": "denmark copenhagen aarhus",
    "FI": "finland helsinki espoo tampere",
    "NO": "norway oslo bergen",
    "EE": "estonia tallinn tartu",
    "LT": "lithuania vilnius kaunas",
    "LV": "latvia riga",
    "LU": "luxembourg",
    "GR": "greece athens thessaloniki",
    "HU": "hungary budapest",
    "RO": "romania bucharest cluj",
    "CY": "cyprus limassol nicosia larnaca",
    "RS": "serbia belgrade beograd novi_sad",
    "GE": "tbilisi batumi",
    "AM": "armenia yerevan",
    "TR": "turkey türkiye istanbul ankara",
    "AE": "uae united_arab_emirates dubai abu_dhabi",
    "US": "usa united_states new_york san_francisco",
    "CA": "canada toronto vancouver montreal calgary ottawa",
}
# длинные варианты проверяем первыми ("new york" раньше "york")
ALIASES = sorted(
    ((a.replace("_", " "), code) for code, s in _ALIASES.items() for a in s.split()),
    key=lambda x: -len(x[0]),
)


def detect_country(text: str):
    s = (text or "").lower()
    for alias, code in ALIASES:
        if re.search(r"(?<![a-zäöüßа-я])" + re.escape(alias) + r"(?![a-zäöüßа-я])", s):
            return code
    return None


LVL = ["none", "A1", "A2", "B1", "B2", "C1"]
EDU = ["school", "vocational", "bachelor", "master", "phd"]

# ---------- сфера работы ----------
SECTOR_WORDS = [
    ("med", r"nurse|nursing|pflege|arzt|ärzt|doctor|physician|medical|clinic|klinik|caregiver|hospital|therapist|pharma"),
    ("eng", r"mechanical|electrical engineer|civil engineer|ingenieur|maschinenbau|cad\b|manufacturing|elektro|construction|bauingenieur|hvac"),
    ("it", r"developer|software|devops|frontend|front-end|backend|back-end|full[- ]?stack|data (engineer|scientist|analyst)|machine learning|\bml\b|\bai\b|\bqa\b|tester|python|java\b|javascript|typescript|react|golang|\bgo\b|kotlin|php|ruby|cloud|\bsre\b|kubernetes|entwickler|informatik|\bit\b|cyber|security engineer|product manager|ux|ui designer"),
    ("service", r"logistic|warehouse|lager|driver|fahrer|customer (support|service|success)|kundenservice|sales|vertrieb|hotel|restaurant|koch|chef|retail|verkauf|support agent"),
    ("edu", r"teacher|lehrer|tutor|instructor|educator|trainer"),
]


def detect_sector(text: str) -> str:
    s = (text or "").lower()
    for sector, rx in SECTOR_WORDS:
        if re.search(rx, s):
            return sector
    return "other"


# ---------- язык, опыт, виза ----------
_DE_STOP = re.compile(r"\b(und|der|die|das|wir|für|mit|sie|ihre|bei|eine|unser)\b")
_EN_STOP = re.compile(r"\b(and|the|we|for|with|you|your|our|are|will|this)\b")


def detect_languages(title: str, text: str):
    """Возвращает (english_min, german_min) — уровни из LVL."""
    s = (title + " " + text).lower()
    de_words = len(_DE_STOP.findall(s))
    en_words = len(_EN_STOP.findall(s))
    german_posting = de_words > en_words * 1.2 and de_words > 15

    german = "none"
    explicit = re.search(r"(german|deutsch)\w*[^.\n]{0,25}?\b([abc][12])\b", s)
    if explicit and not re.search(r"german\s+(is\s+)?(a\s+)?(plus|nice|bonus)", s):
        german = explicit.group(2).upper() if explicit.group(2).upper() != "C2" else "C1"
    elif re.search(r"german\s+(is\s+)?(a\s+)?(plus|nice|bonus|advantage|beneficial)|deutsch\w*\s+(ist\s+)?(ein\s+)?(plus|von vorteil|wünschenswert)", s):
        german = "none"
    elif re.search(r"(fluent|native|excellent|business[- ]fluent|verhandlungssicher|fließend\w*|sehr gute)\s+(\w+\s+){0,2}(german|deutsch)|german\s*\(?\s*c[12]|deutsch\w*\s*\(?\s*c[12]", s):
        german = "C1"
    elif re.search(r"(good|solid|working|gute)\s+(\w+\s+){0,2}(german|deutsch)|german\s*\(?\s*b2|deutsch\w*\s*\(?\s*b2|german (language )?skills|deutschkenntnisse", s):
        german = "B2"
    elif german_posting:
        german = "B2"

    if german_posting:
        english = "none"
    elif re.search(r"(native|excellent|business[- ]fluent|c1|c2)\s+(\w+\s+){0,2}english|english\s*\(?\s*c[12]", s):
        english = "C1"
    else:
        english = "B2"
    return english, german


def detect_min_experience(title: str, text: str) -> int:
    s = (title + " " + text).lower()
    nums = [int(n) for n in re.findall(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:years|yrs|jahre)", s) if 0 < int(n) <= 15]
    if nums:
        return min(nums)
    t = title.lower()
    if re.search(r"\b(lead|principal|head of|staff)\b", t):
        return 7
    if re.search(r"\b(senior|sr\.?)\b", t):
        return 5
    if re.search(r"\b(junior|jr\.?|entry|graduate|werkstudent|intern|praktikum|trainee|ausbildung)\b", t):
        return 0
    return 2


VISA_YES = re.compile(r"visa sponsor|sponsor(ship)?\s+(of\s+)?(your\s+)?(work\s+)?visa|blue card|work permit (support|assistance)|visa support|visum|help (you )?with (the )?visa|visa (and|&) relocation|relocation (and|&) visa")
VISA_NO = re.compile(r"(no|not|unable to|cannot|can't|do not|don't|won't)\s+(\w+\s+){0,2}(visa\s+)?sponsor|must (already )?(have|hold|possess) (a |the )?(valid )?(right to work|work permit|eu citizenship|work authori[sz]ation)|eu citizens only|only eu|arbeitserlaubnis (ist )?(erforderlich|voraussetzung)|without (the )?need (for|of) (visa )?sponsorship")
RELOC_YES = re.compile(r"relocation (package|support|assistance|bonus|budget|help|allowance)|(help|support|assist)\w* (you )?(with )?(your )?relocat|umzugs(kosten|unterstützung|hilfe|pauschale)|relocation is (offered|provided|possible)")

# (регулярка, сообщение, штраф к надёжности)
RED_FLAGS = [
    (re.compile(r"(application|registration|processing|visa|training|placement|onboarding)\s+fee|pay\s+(a\s+)?(small\s+)?(fee|deposit)|upfront payment"), "Просят оплатить «сбор» — частый признак мошенников", 4),
    (re.compile(r"telegram|whatsapp|viber|wechat"), "Связь через мессенджер вместо официального отклика", 2),
    (re.compile(r"@(gmail|yahoo|hotmail|outlook|mail\.ru|yandex|proton)\."), "Контакт — личная почта, а не корпоративная", 2),
    (re.compile(r"guarantee[d]?\s+(\w+\s+)?(visa|job|income|placement)|100\s*%\s*(visa|guarantee|success)"), "Обещают «гарантию» визы или дохода", 3),
    (re.compile(r"(earn|make)\s+(up to\s+)?[$€£]?\s?\d[\d,.]*\s*k?\s*(per|a|/)\s*(day|week)"), "Обещают большой заработок «в неделю/день»", 2),
    (re.compile(r"\b(mlm|network marketing|crypto trading|forex trading|binary options|be your own boss)\b"), "Признаки MLM или трейдинговых схем", 3),
]

SOURCE_TRUST = {"arbeitnow": 7, "adzuna": 6, "jobicy": 6}
EXPENSIVE = {"CH", "GB", "IE", "NL", "AE", "US", "LU", "NO", "DK"}


def clamp(v, lo=1, hi=10):
    return int(max(lo, min(hi, round(v))))


def strip_html(html: str) -> str:
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", html or "", flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
            .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()


def posted_ru(dt):
    if not dt:
        return ""
    days = (datetime.now(timezone.utc) - dt).days
    if days <= 0:
        return "сегодня"
    if days == 1:
        return "вчера"
    if days < 30:
        return f"{days} дн. назад"
    return f"{days // 30} мес. назад"


def analyze_job(raw: dict) -> dict:
    """raw — вакансия в общем формате из sources.py. Добавляет оценки и признаки."""
    title, desc = raw["title"], raw["description"]
    full = (title + "\n" + " ".join(raw.get("tags", [])) + "\n" + desc).lower()

    english, german = detect_languages(title, desc)
    min_exp = detect_min_experience(title, desc)
    visa = bool(VISA_YES.search(full))
    visa_denied = bool(VISA_NO.search(full))
    if visa_denied:
        visa = False
    reloc = bool(RELOC_YES.search(full))
    sector = detect_sector(title + " " + " ".join(raw.get("tags", [])))

    flags = []
    penalty = 0
    for rx, msg, pen in RED_FLAGS:
        if rx.search(full):
            flags.append(msg)
            penalty += pen
    if len(desc) < 200:
        flags.append("Слишком короткое описание")
        penalty += 1
    if not raw.get("company"):
        flags.append("Не указана компания")
        penalty += 2
    if min_exp == 0 and raw.get("salary_month_eur", 0) > 8000:
        flags.append("Очень высокая зарплата без опыта")
        penalty += 3

    age_days = (datetime.now(timezone.utc) - raw["posted_at"]).days if raw.get("posted_at") else None
    country = raw.get("country_code")
    remote = raw.get("remote", False)

    rel = SOURCE_TRUST.get(raw["source"], 6) + (1 if raw.get("salary") else 0) - penalty
    if age_days is not None and age_days > 45:
        rel -= 1
    ease = 5 + (2 if visa else 0) - (3 if visa_denied and not remote else 0) + (2 if remote else 0) + (1 if reloc else 0)
    speed = 5 + (3 if remote else 0) + (1 if visa else 0) + (1 if visa and country in ("DE", "NL") else 0) - (2 if visa_denied and not remote else 0)
    cost = 5 + (3 if reloc else 0) + (2 if remote else 0) - (1 if country in EXPENSIVE else 0)
    pr = COUNTRIES[country][3] if country in COUNTRIES and not remote else (3 if remote else 4)
    if visa_denied and not remote:
        pr -= 2

    raw.update(
        english=english, german=german, minExp=min_exp, visa=visa, visa_denied=visa_denied,
        reloc=reloc, sector=sector, flags=flags, flagged=penalty >= 4,
        s={"rel": clamp(rel), "ease": clamp(ease), "speed": clamp(speed), "cost": clamp(cost), "pr": clamp(pr)},
        posted=posted_ru(raw.get("posted_at")),
    )
    return raw


SECTOR_RU = {"it": "IT", "med": "Медицина", "eng": "Инженерия", "service": "Сервис / логистика", "edu": "Образование", "other": "Другое"}


def match_job(job: dict, profile: dict) -> dict:
    """Совпадение вакансии с анкетой 0–100 + причины (как во фронтенде)."""
    score, ok, no = 100, [], []
    p_sector = profile.get("sector", "other")
    if p_sector not in ("other", "any") and job["sector"] != p_sector:
        score -= 35
        no.append("Другая сфера: " + SECTOR_RU.get(job["sector"], job["sector"]))
    else:
        ok.append("Твоя сфера")

    regions = profile.get("regions") or []
    if job["remote"] and job.get("remote_scope") == "anywhere":
        ok.append("Удалёнка из любой страны")
    elif regions and job["region"] not in regions:
        score -= 20
        no.append("Не в выбранных регионах")
    else:
        ok.append("Регион подходит")
    if job["remote"] and job.get("remote_scope") not in (None, "anywhere"):
        no.append("Удалёнка с ограничением: " + job.get("remote_geo", ""))
        score -= 10

    def lvl(x):
        return LVL.index(x) if x in LVL else 0
    if lvl(profile.get("english", "none")) < lvl(job["english"]):
        score -= 25
        no.append("Английский от " + job["english"])
    elif job["english"] != "none":
        ok.append("Английский " + job["english"])
    if job["german"] != "none":
        if lvl(profile.get("german", "none")) < lvl(job["german"]):
            score -= 25
            no.append("Немецкий от " + job["german"])
        else:
            ok.append("Немецкий подходит")

    exp = int(profile.get("experience") or 0)
    if exp < job["minExp"]:
        score -= 20
        no.append(f"Опыт от {job['minExp']} лет")
    else:
        ok.append("Опыт подходит")

    if job["visa"]:
        ok.append("Спонсируют визу")
    if job["reloc"]:
        ok.append("Помощь с переездом")
    if job["visa_denied"] and not job["remote"]:
        score -= 30
        no.append("Визу не спонсируют")
    for f in job["flags"][:3]:
        no.append("⚠ " + f)
    if job["flagged"]:
        score = min(score - 40, 10)
    return {"score": max(0, min(100, score)), "ok": ok, "no": no}
