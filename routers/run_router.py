from fastapi import APIRouter
from fastapi.responses import JSONResponse
import io, contextlib

router = APIRouter()

@router.post("/run")
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
