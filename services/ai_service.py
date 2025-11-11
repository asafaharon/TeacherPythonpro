from fastapi.responses import JSONResponse
from services.module_service import build_module_summary
import os, time
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RATE_LIMIT = {}   # ip -> [timestamps]
WINDOW_SEC = 300  # 5 דקות
MAX_REQS = 10     # מקסימום בקשות בחלון זמן

def rate_limited(ip: str) -> bool:
    now = time.time()
    RATE_LIMIT[ip] = [t for t in RATE_LIMIT.get(ip, []) if now - t < WINDOW_SEC]
    if len(RATE_LIMIT[ip]) >= MAX_REQS:
        return True
    RATE_LIMIT[ip].append(now)
    return False

async def process_ai_question(req, data):
    question = (data.get("question") or "").strip()
    module_id = int(data.get("module_id") or 1)

    ip = req.client.host if req.client else "unknown"
    if rate_limited(ip):
        return JSONResponse({"detail": "חרגת מהמגבלה (10 שאלות / 5 דקות)"}, status_code=429)

    if not question:
        return JSONResponse({"detail": "שאלה ריקה."}, status_code=400)

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
