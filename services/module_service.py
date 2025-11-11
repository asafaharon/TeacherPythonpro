import json, re
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
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
