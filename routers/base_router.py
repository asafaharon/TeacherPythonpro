from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # תיקון תואם: שימוש בפרמטרים מפורשים למניעת שגיאות Cache
    return templates.TemplateResponse(name="modules.html", context={"request": request})

@router.get("/modules", response_class=HTMLResponse)
async def modules_page(request: Request):
    # תוקן: הועבר המילון תחת כותרת הפרמטר context
    return templates.TemplateResponse(name="modules.html", context={"request": request})

@router.get("/module/{module_id}", response_class=HTMLResponse)
async def module_page(request: Request, module_id: int):
    # תוקן: הועבר ה-context בצורה מפורשת עם המשתנים הנדרשים
    return templates.TemplateResponse(
        name="module.html",
        context={"request": request, "module_id": module_id}
    )

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = {
        "total_modules": 19,
        "questions_asked": 1329,
        "unique_users": 463,
        "avg_questions": round(1329 / 463, 2),
        "last_question_time": "לפני 11 דקות",
        "generated_at": datetime.now().strftime("%H:%M %d.%m.%Y"),
    }
    # תוקן: העברת הנתונים וה-request בצורה בטוחה
    return templates.TemplateResponse(
        name="dashboard.html",
        context={"request": request, "stats": stats}
    )