from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from dotenv import load_dotenv
import os

# טוען משתני סביבה
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ====================================================
# רישום Routerים
# ====================================================
from routers.base_router import router as base_router
from routers.ai_router import router as ai_router
from routers.run_router import router as run_router
from routers.automaton_router import router as automaton_router  # 👈 העבר לכאן
from routers.pda_router import router as pda_router
from routers.tm_router import router as tm_router
app.include_router(tm_router)

# הסדר הנכון
app.include_router(base_router)
app.include_router(ai_router)
app.include_router(run_router)
app.include_router(automaton_router)  # 👈 נטען אחרון כדי שיעבוד תקין
app.include_router(pda_router)
# ====================================================
# הרצה מקומית
# ====================================================
if __name__ == "__main__":
    import uvicorn, webbrowser
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"

    if not os.environ.get("PORT"):
        url = f"http://{host}:{port}"
        try:
            webbrowser.get("chrome").open(url)
        except:
            webbrowser.open(url)

    uvicorn.run("main:app", host=host, port=port, reload=not os.environ.get("PORT"))
