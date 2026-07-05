from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
from typing import Any, Dict
import logging

from services.pda_service import generate_pda, simulate_pda_word
from services.npda_tree_engine import run_npda_with_tree

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()

# ============================================================
# Schemas
# ============================================================

class PdaSimulationRequest(BaseModel):
    """
    סימולציה רגילה (מסלול אחד).
    """
    pda: Dict[str, Any]
    word: str


class PdaTreeSimulationRequest(BaseModel):
    """
    סימולציה עם עץ חישוב (NPDA לא־דטרמיניסטי).
    """
    pda: Dict[str, Any]
    word: str
    max_steps: int = 2000
    max_nodes: int = 4000


class PdaGenerateAndTreeSimulationRequest(BaseModel):
    """
    יצירת NPDA משפה טבעית + סימולציה עם עץ חישוב.
    """
    description: str
    word: str
    max_steps: int = 2000
    max_nodes: int = 4000


# ============================================================
# Pages
# ============================================================

@router.get("/pda", response_class=HTMLResponse, tags=["PDA"])
async def pda_page(request: Request) -> HTMLResponse:
    """
    דף ה-UI למחולל אוטומט מחסנית (PDA).
    """
    return templates.TemplateResponse("pda.html", {"request": request})


# ============================================================
# API – Generation
# ============================================================

@router.post("/pda/generate", response_class=JSONResponse, tags=["PDA"])
async def generate_pda_endpoint(description: str = Form(...)) -> JSONResponse:
    """
    יוצר NPDA מתיאור שפה טבעית.
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
                "explanation": "❌ שגיאה ביצירת אוטומט מחסנית.",
                "source": "error",
                "logic": "",
                "accuracy": 0,
            },
            status_code=500,
        )


# ============================================================
# API – Simulation (single path)
# ============================================================

@router.post("/pda/simulate", response_class=JSONResponse, tags=["PDA"])
async def simulate_pda_endpoint(payload: PdaSimulationRequest) -> JSONResponse:
    """
    סימולציה רגילה – מחזירה מסלול אחד (אם קיים).
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
                "error": "❌ שגיאה בהרצת האוטומט.",
            },
            status_code=500,
        )


# ============================================================
# API – Simulation with computation tree (NPDA)
# ============================================================

@router.post("/pda/simulate/tree", response_class=JSONResponse, tags=["PDA"])
async def simulate_pda_tree_endpoint(
    payload: PdaTreeSimulationRequest,
) -> JSONResponse:
    """
    סימולציית NPDA עם החזרת עץ חישוב מלא.
    """
    try:
        logger.info(
            "NPDA TREE simulation requested. Word='%s'", payload.word
        )

        result = run_npda_with_tree(
            pda=payload.pda,
            input_word=payload.word,
            max_steps=payload.max_steps,
            max_nodes=payload.max_nodes,
        )

        return JSONResponse(result)

    except Exception as exc:
        logger.exception("Error while simulating NPDA tree: %s", exc)
        return JSONResponse(
            {
                "accepted": False,
                "tree": {},
                "error": "❌ שגיאה בהרצת NPDA עם עץ חישוב.",
            },
            status_code=500,
        )


# ============================================================
# API – Generate + Tree Simulation
# ============================================================

@router.post(
    "/pda/generate_and_simulate/tree",
    response_class=JSONResponse,
    tags=["PDA"],
)
async def generate_and_simulate_pda_tree_endpoint(
    payload: PdaGenerateAndTreeSimulationRequest,
) -> JSONResponse:
    """
    יוצר NPDA משפה טבעית ומריץ סימולציה עם עץ חישוב.
    """
    try:
        logger.info(
            "Generate + NPDA TREE simulation requested. Word='%s'",
            payload.word,
        )

        pda = await generate_pda(payload.description)

        if pda.get("type") != "PDA":
            return JSONResponse(
                {
                    "accepted": False,
                    "pda": pda,
                    "error": "❌ לא ניתן היה לבנות NPDA עבור התיאור.",
                }
            )

        result = run_npda_with_tree(
            pda=pda,
            input_word=payload.word,
            max_steps=payload.max_steps,
            max_nodes=payload.max_nodes,
        )

        return JSONResponse(
            {
                "pda": pda,
                "result": result,
            }
        )

    except Exception as exc:
        logger.exception(
            "Error while generating/simulating NPDA tree: %s", exc
        )
        return JSONResponse(
            {
                "accepted": False,
                "error": "❌ שגיאה ביצירה או בהרצת NPDA.",
            },
            status_code=500,
        )
