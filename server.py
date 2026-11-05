"""
Релокот — локальный сервер.

Запуск:  python server.py   (или start.bat / start.sh)
Открой:  http://127.0.0.1:8000
"""
import os
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent


def load_env(path=ROOT / ".env"):
    """Мини-загрузчик .env: строки вида KEY=value."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()

from fastapi import Body, FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402

import ai  # noqa: E402
import sources  # noqa: E402

app = FastAPI(title="Релокот API")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "mock": sources.mock_mode(),
        "ai": ai.ai_enabled(),
        "model": ai._model() if ai.ai_enabled() else None,
        "sources": {"arbeitnow": True, "jobicy": True, "adzuna": sources.adzuna_enabled()},
    }


@app.post("/api/jobs/search")
async def jobs_search(body: dict = Body(...)):
    return await sources.search_jobs(body.get("profile") or {}, body.get("query", ""), body.get("countries") or [])


@app.post("/api/programs/search")
async def programs_search(body: dict = Body(...)):
    try:
        return await ai.search_programs(body.get("profile") or {}, body.get("extra", ""), bool(body.get("refresh")))
    except ai.AINotConfigured as e:
        raise HTTPException(503, str(e))
    except Exception as e:  # ошибка API, сети или разбора JSON
        raise HTTPException(502, f"Поиск не удался: {e}")


@app.post("/api/events/search")
async def events_search(body: dict = Body(...)):
    try:
        return await ai.search_events(body.get("profile") or {}, int(body.get("months") or 4), bool(body.get("refresh")))
    except ai.AINotConfigured as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(502, f"Поиск не удался: {e}")


if __name__ == "__main__":
    import uvicorn

    host, port = "127.0.0.1", int(os.environ.get("PORT", 8000))
    url = f"http://{host}:{port}"
    print(f"\n  Релокот запущен: {url}\n  Остановить: Ctrl+C\n")
    if "--no-browser" not in sys.argv:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")
