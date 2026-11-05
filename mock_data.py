"""
Тестовые данные в формате настоящих API.
Включаются переменной RELOKOT_MOCK=1 — удобно, когда нет интернета или ключей.
"""
import time
from datetime import date, timedelta

_now = int(time.time())

ARBEITNOW = {
    "data": [
        {
            "slug": "backend-engineer-python-berlin-123",
            "company_name": "Example Mobility GmbH",
            "title": "Backend Engineer (Python) – Visa Sponsorship",
            "description": "<p>We are a growing mobility startup in Berlin. You will build APIs in Python and FastAPI.</p>"
                           "<ul><li>3+ years of experience with Python</li><li>Fluent English, German is a plus</li></ul>"
                           "<p>We offer visa sponsorship (EU Blue Card), a relocation package and German classes. "
                           "Salary range 65,000–80,000 EUR. Our team works in English and we help you with the visa and relocation process. "
                           "Apply via our careers page.</p>",
            "remote": False,
            "url": "https://www.arbeitnow.com/jobs/companies/example/backend-engineer-123",
            "tags": ["Software Development", "Python"],
            "job_types": ["full time"],
            "location": "Berlin",
            "created_at": _now - 2 * 86400,
        },
        {
            "slug": "pflegefachkraft-koeln-456",
            "company_name": "Beispiel Pflege GmbH",
            "title": "Pflegefachkraft (m/w/d)",
            "description": "<p>Wir suchen eine Pflegefachkraft für unser Team in Köln. Sie haben eine abgeschlossene Ausbildung "
                           "und sehr gute Deutschkenntnisse (B2). Wir bieten Unterstützung bei der Anerkennung, eine Umzugspauschale "
                           "und eine unbefristete Stelle. Wir freuen uns auf Ihre Bewerbung mit Lebenslauf und Zeugnissen. "
                           "Die Stelle ist in Vollzeit und Teilzeit möglich, mit einer attraktiven Vergütung nach Tarif.</p>",
            "remote": False,
            "url": "https://www.arbeitnow.com/jobs/companies/beispiel/pflegefachkraft-456",
            "tags": ["Healthcare"],
            "job_types": ["full time"],
            "location": "Köln",
            "created_at": _now - 6 * 86400,
        },
        {
            "slug": "frontend-react-munich-789",
            "company_name": "Sample Insurance AG",
            "title": "Senior Frontend Developer (React)",
            "description": "<p>Join our team in Munich. Requirements: 5 years with React and TypeScript, fluent German (C1) and English. "
                           "Unfortunately we cannot offer visa sponsorship; you must already have a valid work permit for Germany. "
                           "We offer hybrid work, 30 days vacation and a modern office. Our product is used by millions of customers.</p>",
            "remote": False,
            "url": "https://www.arbeitnow.com/jobs/companies/sample/frontend-789",
            "tags": ["Frontend", "React"],
            "job_types": ["full time"],
            "location": "München",
            "created_at": _now - 20 * 86400,
        },
        {
            "slug": "data-entry-amsterdam-000",
            "company_name": "",
            "title": "Data entry assistant – no experience needed, guaranteed visa",
            "description": "Earn $3000 per week from home! Guaranteed visa in 3 days. Pay a small processing fee and contact us on Telegram.",
            "remote": False,
            "url": "https://www.arbeitnow.com/jobs/example/data-entry-000",
            "tags": ["Data"],
            "job_types": [],
            "location": "Amsterdam",
            "created_at": _now - 1 * 86400,
        },
    ],
    "links": {"next": None},
}

JOBICY = {
    "jobs": [
        {
            "id": 1001,
            "url": "https://jobicy.com/jobs/1001-devops-engineer",
            "jobTitle": "DevOps Engineer (Kubernetes)",
            "companyName": "Remote Example Inc",
            "jobIndustry": ["DevOps & Sysadmin"],
            "jobType": ["full-time"],
            "jobGeo": "Anywhere",
            "jobLevel": "Midweight",
            "jobExcerpt": "Fully remote role.",
            "jobDescription": "<p>We are a fully remote team hiring a DevOps engineer with 2+ years of experience with Kubernetes, "
                              "Terraform and AWS. You can work from anywhere in the world. We pay in USD via a contractor agreement. "
                              "Our hiring process has three interviews and a paid test task.</p>",
            "pubDate": "2026-11-03 10:00:00",
            "annualSalaryMin": 50000,
            "annualSalaryMax": 70000,
            "salaryCurrency": "USD",
        },
        {
            "id": 1002,
            "url": "https://jobicy.com/jobs/1002-qa-engineer",
            "jobTitle": "QA Automation Engineer",
            "companyName": "Euro Test Labs",
            "jobIndustry": ["QA"],
            "jobType": ["full-time"],
            "jobGeo": "Europe",
            "jobLevel": "Midweight",
            "jobExcerpt": "Remote in Europe",
            "jobDescription": "<p>Remote position for candidates located in Europe. 2 years of experience with Playwright or Selenium, "
                              "good English. We provide equipment and a learning budget. Contract via employer of record in your country of residence.</p>",
            "pubDate": "2026-10-28 09:00:00",
        },
    ]
}

AI_PROGRAMS = [
    {
        "country_code": "DE", "name": "Chancenkarte (Карта возможностей) — тест", "type": "job-search",
        "summary_ru": "Тестовые данные (RELOKOT_MOCK=1). Виза для поиска работы по балльной системе.",
        "requirements_ru": ["Признанное образование", "Немецкий A1 или английский B2", "Подтверждение средств"],
        "fit_ru": {"ok": ["Подходит под цель «работа»"], "no": ["Нужны сбережения"]},
        "match": 82, "scores": {"rel": 10, "ease": 6, "speed": 6, "cost": 5, "pr": 7},
        "official_url": "https://www.make-it-in-germany.com/en/visa-residence/types/job-search-opportunity-card",
        "sources": ["https://www.make-it-in-germany.com/en/visa-residence/types/job-search-opportunity-card"],
        "checked_note_ru": "Тестовая запись, без реальной проверки.",
    },
    {
        "country_code": "NL", "name": "Highly Skilled Migrant — тест", "type": "work",
        "summary_ru": "Тестовые данные. Работодатель-спонсор подаёт документы за вас.",
        "requirements_ru": ["Оффер от признанного спонсора", "Зарплата выше порога"],
        "fit_ru": {"ok": ["Английский достаточен"], "no": ["Нужен оффер"]},
        "match": 74, "scores": {"rel": 10, "ease": 6, "speed": 9, "cost": 5, "pr": 7},
        "official_url": "https://ind.nl/en/residence-permits/work/highly-skilled-migrant",
        "sources": ["https://ind.nl/en/residence-permits/work/highly-skilled-migrant"],
        "checked_note_ru": "Тестовая запись.",
    },
]

AI_EVENTS = [
    {"date": (date.today() + timedelta(days=12)).isoformat(), "title_ru": "Тестовый вебинар о работе в Германии", "cat": "webinar", "country_code": "DE",
     "url": "https://www.make-it-in-germany.com/en/", "note_ru": "Тестовые данные (RELOKOT_MOCK=1)"},
    {"date": (date.today() + timedelta(days=30)).isoformat(), "title_ru": "Тестовый дедлайн стипендии", "cat": "deadline", "country_code": "DE",
     "url": "https://www.daad.de/en/", "note_ru": "Тестовые данные"},
]
