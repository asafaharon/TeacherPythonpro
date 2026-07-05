# routers/tm_router.py
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from services.tm_service import generate_tm_from_nl
from services.tm_simulator import (
    init_config,
    snapshot_window,
    step_tm,
    run_tm,
    TMSpecError,
)

logger = logging.getLogger(__name__)

# חייב להיקרא router כדי שה-import ב-main.py יעבוד
router = APIRouter(prefix="/tm", tags=["TM"])
templates = Jinja2Templates(directory="templates")


class GenerateRequest(BaseModel):
    language_description: str = Field(min_length=3)
    alphabet_hint: Optional[str] = None


class InitRequest(BaseModel):
    spec: Dict[str, Any]
    input_str: str = ""
    window_radius: int = Field(default=12, ge=3, le=40)


class StepRequest(BaseModel):
    spec: Dict[str, Any]
    config: Dict[str, Any]
    window_radius: int = Field(default=12, ge=3, le=40)


class RunRequest(BaseModel):
    spec: Dict[str, Any]
    input_str: str = ""
    max_steps: int = Field(default=300, ge=1, le=5000)
    window_radius: int = Field(default=12, ge=3, le=40)


@router.get("", response_class=HTMLResponse)
async def tm_page(request: Request):
    return templates.TemplateResponse("tm.html", {"request": request})


@router.post("/generate")
async def tm_generate(payload: GenerateRequest):
    """
    Generate a TM spec from natural language (the core product behavior).
    """
    try:
        spec = generate_tm_from_nl(
            language_description=payload.language_description,
            alphabet_hint=payload.alphabet_hint,
        )

        if spec.get("type") == "none":
            return {"ok": False, "type": "none", "message": spec.get("explanation_he", "לא ניתן לייצר TM"), "raw": spec}

        # success
        return {
            "ok": True,
            "type": "TM",
            "spec": spec,
            "explanation_he": spec.get("explanation_he", ""),
            "examples": spec.get("examples", {}),
        }

    except Exception:
        logger.exception("Unexpected TM generate error")
        return {"ok": False, "message": "שגיאה לא צפויה ביצירת TM"}


@router.post("/init")
async def tm_init(payload: InitRequest):
    """
    Initialize a run configuration for a given spec+input.
    """
    try:
        spec = payload.spec
        blank = spec.get("blank", "_")
        start_state = spec.get("start_state", "q0")

        config = init_config(
            input_str=payload.input_str,
            blank=blank,
            start_state=start_state,
        )

        return {
            "ok": True,
            "config": config,
            "window": snapshot_window(
                tape=config["tape"],
                head=config["head"],
                blank=blank,
                radius=payload.window_radius,
            ),
        }

    except TMSpecError as e:
        logger.warning("TM init failed: %s", e)
        return {"ok": False, "message": str(e)}
    except Exception:
        logger.exception("Unexpected TM init error")
        return {"ok": False, "message": "שגיאה לא צפויה באתחול"}


@router.post("/step")
async def tm_step(payload: StepRequest):
    """
    One step simulation (stateless; client holds config).
    """
    try:
        res = step_tm(payload.spec, payload.config, window_radius=payload.window_radius)
        return {"ok": True, **res}
    except TMSpecError as e:
        logger.warning("TM step failed: %s", e)
        return {"ok": False, "message": str(e)}
    except Exception:
        logger.exception("Unexpected TM step error")
        return {"ok": False, "message": "שגיאה לא צפויה בצעד"}


@router.post("/run")
async def tm_run(payload: RunRequest):
    """
    Full run (returns trace) - optional.
    """
    try:
        res = run_tm(
            spec=payload.spec,
            input_str=payload.input_str,
            max_steps=payload.max_steps,
            window_radius=payload.window_radius,
        )
        return {"ok": True, **res}
    except TMSpecError as e:
        logger.warning("TM run failed: %s", e)
        return {"ok": False, "message": str(e)}
    except Exception:
        logger.exception("Unexpected TM run error")
        return {"ok": False, "message": "שגיאה לא צפויה בהרצה"}
