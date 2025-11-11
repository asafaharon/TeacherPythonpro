from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from services.automaton_service import generate_automaton_html
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()

@router.get("/automaton", response_class=HTMLResponse)
async def automaton_page(request: Request):
    # כעת אין הורשה או stats – פשוט מציג את הדף
    return templates.TemplateResponse("automaton.html", {"request": request})

@router.post("/generate_automaton", response_class=HTMLResponse)
async def generate_automaton(request: Request, description: str = Form(...)):
    html_result = await generate_automaton_html(description)
    return html_result
