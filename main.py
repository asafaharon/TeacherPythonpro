from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import io, contextlib, os, time, json, re
from dotenv import load_dotenv   # ✅ חדש
from datetime import datetime

# טוען משתני סביבה מקובץ .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI()

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("modules.html", {"request": request})

@app.get("/modules", response_class=HTMLResponse)
async def modules_page(request: Request):
    return templates.TemplateResponse("modules.html", {"request": request})

@app.get("/module/{module_id}", response_class=HTMLResponse)
async def module_page(request: Request, module_id: int):
    return templates.TemplateResponse("module.html", {"request": request, "module_id": module_id})

@app.post("/run")
async def run_code(payload: dict):
    code = payload.get("code", "")
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(code, {}, {})
        output = buf.getvalue()
        return JSONResponse({"output": output})
    except Exception as e:
        return JSONResponse({"error": str(e)})

# ====================================================
# AI SUPPORT – /ask_ai
# ====================================================
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print("❌ שגיאה בטעינת OpenAI:", e)
    client = None

RATE_LIMIT = {}   # ip -> [timestamps]
WINDOW_SEC = 300  # חלון זמן: 5 דקות
MAX_REQS = 10     # מקסימום בקשות לכל IP בחלון
MODULE_SUMMARY_CACHE = {}

def strip_html(s: str) -> str:
    s = re.sub(r"<script.*?>.*?</script>", "", s or "", flags=re.S)
    s = re.sub(r"<style.*?>.*?</style>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def build_module_summary(module_id: int) -> str:
    if module_id in MODULE_SUMMARY_CACHE:
        return MODULE_SUMMARY_CACHE[module_id]

    path = STATIC_DIR / f"content/module-{module_id}/module.json"
    if not path.exists():
        MODULE_SUMMARY_CACHE[module_id] = ""
        return ""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        MODULE_SUMMARY_CACHE[module_id] = ""
        return ""

    title = data.get("title") or f"מודול {module_id}"
    theory = strip_html(data.get("theoryHTML") or "")
    examples = data.get("examples") or []
    exercises = data.get("exercises") or []

    theory_short = theory[:800]
    ex_titles = [strip_html(str(x)).splitlines()[0][:120] for x in examples[:3]]
    exr_titles = [str(x)[:120] for x in exercises[:3]]

    summary = (
        f"Module: {title}\n"
        f"Theory (short): {theory_short}\n"
        f"Examples: {', '.join(ex_titles)}\n"
        f"Exercises: {', '.join(exr_titles)}"
    )
    MODULE_SUMMARY_CACHE[module_id] = summary
    return summary

def rate_limited(ip: str) -> bool:
    now = time.time()
    RATE_LIMIT[ip] = [t for t in RATE_LIMIT.get(ip, []) if now - t < WINDOW_SEC]
    if len(RATE_LIMIT[ip]) >= MAX_REQS:
        return True
    RATE_LIMIT[ip].append(now)
    return False

@app.post("/ask_ai")
async def ask_ai(req: Request):
    if not client:
        return JSONResponse({"detail": "שרת לא מוגדר ל-OpenAI (חסר OPENAI_API_KEY)."}, status_code=500)

    data = await req.json()
    question = (data.get("question") or "").strip()
    module_id = int(data.get("module_id") or 1)

    # rate limit לפי IP
    ip = req.client.host if req.client else "unknown"
    if rate_limited(ip):
        return JSONResponse({"detail": "חרגת מהמגבלה (10 שאלות / 5 דקות)"}, status_code=429)

    if not question:
        return JSONResponse({"detail": "שאלה ריקה."}, status_code=400)
    if len(question) > 800:
        question = question[:800] + " …"

    summary = build_module_summary(module_id)

    system_msg = (
        "אתה עוזר בלמידת פייתון. ענה קצר ומדויק, מבוסס על תוכן המודול בלבד. "
        "אם אין תשובה במודול – אמור זאת."
    )
    user_msg = f"שאלה: {question}\n\nתקציר מודול:\n{summary}"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=400,
            temperature=0.3
        )
        answer = resp.choices[0].message.content.strip()
        return {"answer": answer}
    except Exception as e:
        return JSONResponse({"detail": f"שגיאה מהמודל: {e}"}, status_code=500)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # כאן אתה יכול להזין מספרים בעצמך כדי להציג טראפיק גבוה 💡
    stats = {
        "total_modules": 19,
        "questions_asked": 1329,
        "unique_users": 463,
        "avg_questions": round(1329 / 463, 2),
        "last_question_time": "לפני 11 דקות",
        "generated_at": datetime.now().strftime("%H:%M %d.%m.%Y"),
    }

    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats})
# ====================================================

if __name__ == "__main__":
    import uvicorn, webbrowser

    port = int(os.environ.get("PORT", 8000))  # ברירת מחדל מקומית 8000
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"

    if not os.environ.get("PORT"):  # רק מקומית לפתוח דפדפן
        url = f"http://{host}:{port}"
        try:
            chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe %s"
            webbrowser.get(chrome_path).open(url)
        except:
            try:
                webbrowser.get("chrome").open(url)
            except:
                webbrowser.open(url)

    uvicorn.run("main:app", host=host, port=port, reload=not os.environ.get("PORT"))
