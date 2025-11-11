from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from services.ai_service import process_ai_question

router = APIRouter()

@router.post("/ask_ai")
async def ask_ai(req: Request):
    try:
        data = await req.json()
        result = await process_ai_question(req, data)
        return result
    except Exception as e:
        return JSONResponse({"detail": f"שגיאה: {e}"}, status_code=500)
