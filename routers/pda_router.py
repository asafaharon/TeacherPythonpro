from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
from typing import Any, Dict
import logging

from services.pda_service import generate_pda, simulate_pda_word

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


class PdaSimulationRequest(BaseModel):
    """
    בקשת סימולציה: מקבלת את ה-PDA כפי שנוצר ע"י ה-API,
    ואת המחרוזת שברצוננו לבדוק.
    """
    pda: Dict[str, Any]
    word: str


@router.get("/pda", response_class=HTMLResponse, tags=["PDA"])
async def pda_page(request: Request) -> HTMLResponse:
    """
    דף ה-UI למחולל אוטומט מחסנית (PDA) משפה טבעית.
    """
    return templates.TemplateResponse("pda.html", {"request": request})


@router.post("/pda/generate", response_class=JSONResponse, tags=["PDA"])
async def generate_pda_endpoint(
    description: str = Form(...)
) -> JSONResponse:
    """
    יוצר PDA מתיאור מילולי (בעברית/אנגלית) של שפה פורמלית.
    """
    try:
        logger.info("PDA generation requested. Description=%s", description)
        pda = await generate_pda(description)
        return JSONResponse(pda)
    except Exception as exc:
        logger.exception("Error while generating PDA: %s", exc)
        return JSONResponse(
            {
                "type": "none",
                "explanation": "❌ שגיאה ביצירת אוטומט מחסנית. נסה שוב מאוחר יותר.",
                "source": "error",
                "logic": "",
                "accuracy": 0,
            },
            status_code=500,
        )


@router.post("/pda/simulate", response_class=JSONResponse, tags=["PDA"])
async def simulate_pda_endpoint(payload: PdaSimulationRequest) -> JSONResponse:
    """
    מריץ את ה-PDA על מחרוזת בודדת ומחזיר האם התקבלה, יחד עם Trace של ההרצה.
    """
    try:
        logger.info("PDA simulation requested. Word='%s'", payload.word)
        result = await simulate_pda_word(payload.pda, payload.word)
        return JSONResponse(result)
    except Exception as exc:
        logger.exception("Error while simulating PDA: %s", exc)
        return JSONResponse(
            {
                "accepted": False,
                "trace": [],
                "error": "❌ שגיאה בהרצת האוטומט על המחרוזת.",
            },
            status_code=500,
        )
