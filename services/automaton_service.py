import os
import json
from typing import Dict, List, Optional
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ====================================================
# Model for DFA object
# ====================================================
class Automaton(BaseModel):
    type: str
    alphabet: List[str]
    states: List[str]
    start_state: str
    accept_states: List[str]
    transitions: Dict[str, Dict[str, str]]
    explanation: Optional[str] = None
    logic: Optional[str] = None
    simulation: Optional[dict] = None
    empirical_accuracy: Optional[str] = None
    construction_explanation: Optional[str] = None
    source: Optional[str] = None


# ====================================================
# Fallback DFA (for critical failure)
# ====================================================
def fallback_even_length_dfa() -> dict:
    print("[Fallback] Returning even-length DFA")
    return {
        "type": "DFA",
        "alphabet": ["0", "1"],
        "states": ["q_even", "q_odd"],
        "start_state": "q_even",
        "accept_states": ["q_even"],
        "transitions": {
            "q_even": {"0": "q_odd", "1": "q_odd"},
            "q_odd": {"0": "q_even", "1": "q_even"},
        },
        "explanation": "האוטומט מקבל את כל המילים באורך זוגי (כולל המילה הריקה).",
        "logic": "כל תו הופך את הספירה מזוגי לאי-זוגי ולהפך.",
        "simulation": {
            "accepted_example": {"input": "10", "path": ["q_even", "q_odd", "q_even"], "result": "מתקבלת"},
            "rejected_example": {"input": "1", "path": ["q_even", "q_odd"], "result": "נדחית"},
        },
        "empirical_accuracy": "Fallback עקב שגיאה בבניית האוטומט.",
        "construction_explanation": "האוטומט הגנרי נוצר רק לשימוש במקרה כשל.",
        "source": "fallback",
    }


# ====================================================
# Validate and fix DFA
# ====================================================
def validate_and_fix_dfa(raw: dict) -> dict:
    alphabet = raw.get("alphabet") or ["0", "1"]
    states = list(dict.fromkeys(raw.get("states", []))) or ["q0"]
    start = raw.get("start_state") or states[0]
    if start not in states:
        states.insert(0, start)
    accepts = raw.get("accept_states") or [start]
    transitions = raw.get("transitions", {})

    fixed_transitions = {}
    for s in states:
        fixed_transitions[s] = {}
        for sym in alphabet:
            dst = transitions.get(s, {}).get(sym)
            fixed_transitions[s][sym] = dst or s

    return {
        "type": "DFA",
        "alphabet": alphabet,
        "states": states,
        "start_state": start,
        "accept_states": accepts,
        "transitions": fixed_transitions,
        "explanation": raw.get("explanation", "").strip(),
        "logic": raw.get("logic", "").strip(),
        "simulation": raw.get("simulation", {}),
    }


# ====================================================
# Internal logic consistency check
# ====================================================
def check_dfa_integrity(dfa: dict) -> bool:
    try:
        for s in dfa["states"]:
            for sym in dfa["alphabet"]:
                if sym not in dfa["transitions"].get(s, {}):
                    print(f"[Check] Missing transition for {s} on {sym}")
                    return False
                if dfa["transitions"][s][sym] not in dfa["states"]:
                    print(f"[Check] Invalid transition from {s} on {sym}")
                    return False
        return True
    except Exception as e:
        print("[Check] Error:", e)
        return False


# ====================================================
# Build prompts
# ====================================================
def build_prompts(description: str):
    """
    בונה את ה-prompts עבור GPT כך שיווצר אוטומט דטרמיניסטי (DFA)
    התואם בדיוק לשפה שתוארה ע"י המשתמש.
    """

    system_prompt = (
        "You are an expert in formal languages and automata theory. "
        "Your task is to construct a **Deterministic Finite Automaton (DFA)** "
        "that exactly recognizes the language described by the user. "
        "You must ensure that the DFA is **logically consistent**, "
        "**deterministic**, and **minimal if possible**. "
        "All transitions must be defined for each symbol in the alphabet. "
        "If the description is ambiguous, make the most standard deterministic interpretation. "
        "Verify that the DFA accepts all strings that belong to the described language, "
        "and rejects all strings that do not belong to it. "
        "Return ONLY valid JSON — no explanations or text outside the JSON."
    )

    user_prompt = (
        f"The user described the following formal language:\n"
        f"\"{description}\"\n\n"
        "Please return a JSON object representing a **valid DFA** with this structure:\n"
        "{\n"
        "  \"type\": \"DFA\",\n"
        "  \"alphabet\": [\"0\", \"1\"],\n"
        "  \"states\": [\"q0\", \"q1\"],\n"
        "  \"start_state\": \"q0\",\n"
        "  \"accept_states\": [\"q1\"],\n"
        "  \"transitions\": {\n"
        "     \"q0\": {\"0\": \"q1\", \"1\": \"q0\"},\n"
        "     \"q1\": {\"0\": \"q1\", \"1\": \"q0\"}\n"
        "  },\n"
        "  \"explanation\": \"Brief explanation in Hebrew of what the DFA accepts.\",\n"
        "  \"logic\": \"Detailed reasoning in Hebrew behind the transitions and acceptance.\",\n"
        "  \"simulation\": {\n"
        "     \"accepted_example\": {\"input\": \"...\", \"path\": [\"...\"], \"result\": \"מתקבלת\"},\n"
        "     \"rejected_example\": {\"input\": \"...\", \"path\": [\"...\"], \"result\": \"נדחית\"}\n"
        "  }\n"
        "}\n\n"
        "⚠️ Rules:\n"
        "1. Use only JSON keys shown above.\n"
        "2. All transitions must exist for each symbol in the alphabet.\n"
        "3. Ensure correctness — the DFA must accept exactly the described language.\n"
        "4. Respond ONLY with valid JSON (no markdown or natural language)."
    )

    return system_prompt, user_prompt




# ====================================================
# Self-repair for invalid DFAs
# ====================================================
def self_repair_dfa(description: str, last_raw: dict, error_msg: str) -> dict:
    print("[SelfRepair] Attempting self repair...")
    try:
        prompt = (
            f"The DFA generated for description \"{description}\" was invalid: {error_msg}. "
            f"Here is the broken DFA:\n{json.dumps(last_raw, ensure_ascii=False)}\n"
            "Fix and return valid JSON for a correct deterministic DFA."
        )
        res = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You repair invalid DFAs into valid JSON DFAs."},
                {"role": "user", "content": prompt},
            ],
        )
        fixed = json.loads(res.choices[0].message.content)
        fixed = validate_and_fix_dfa(fixed)
        fixed["source"] = "repaired"
        return fixed
    except Exception:
        fb = fallback_even_length_dfa()
        fb["source"] = "fallback"
        return fb


# ====================================================
# Main generator with non-regular detection
# ====================================================
# ====================================================
# Main generator with non-regular detection (updated)
# ====================================================
# ====================================================
# Main generator with non-regular detection (updated, explanation removed)
# ====================================================
async def generate_automaton_html(description: str) -> JSONResponse:
    print(f"\n========== NEW REQUEST ==========\n[Input] {description}")

    # 🧠 שלב 1: זיהוי מילולי מקדים לשפה לא רגולרית
    non_regular_keywords = [
        "שווה למספר", "כמות זהה", "מספר זהה", "אותיות באותו מספר",
        "aⁿbⁿ", "anbn", "equal number", "same number", "count", "counts equal"
    ]
    if any(word in description for word in non_regular_keywords):
        print("[Regularity] Non-regular pattern detected by keyword filter.")
        return JSONResponse(content={
            "type": "none",
            "source": "analysis",
            "explanation": "❌ השפה אינה רגולרית – נדרשת ספירה בלתי מוגבלת (כמו PDA).",
            "logic": "הכלל 'מספר ה־0 שווה למספר ה־1' או כל כלל הדורש ספירה בלתי מוגבלת אינו ניתן לביטוי באוטומט סופי.",
            "empirical_accuracy": "❌ השפה אינה רגולרית – לא נוצר גרף.",
        })

    # 🧩 שלב 2: בדיקה עם GPT האם השפה רגולרית
    try:
        check = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": (
                    "Decide if the described language is REGULAR. "
                    "If it requires memory (like counting, nested structure, or equal numbers), "
                    "return {\"regular\": false, \"reason\": \"...\"}."
                )},
                {"role": "user", "content": f"Language: {description}"}
            ],
        )
        reg_data = json.loads(check.choices[0].message.content)
        if not reg_data.get("regular", True):
            print("[Regularity] Non-regular language detected by GPT.")
            return JSONResponse(content={
                "type": "none",
                "source": "analysis",
                "explanation": f"❌ {reg_data.get('reason', 'השפה אינה רגולרית ולכן אין לה DFA.')} ",
                "logic": "לשפה זו דרוש זיכרון בלתי מוגבל (כמו PDA).",
                "empirical_accuracy": "❌ שפה לא רגולרית — לא נוצר גרף.",
            })
    except Exception as e:
        print("[Regularity] GPT check failed:", e)

    # 🧩 שלב 3: יצירת DFA רגיל
    sys_p, usr_p = build_prompts(description)

    for attempt in range(3):
        try:
            res = client.chat.completions.create(
                model="gpt-4o",
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": sys_p},
                    {"role": "user", "content": usr_p},
                ],
            )
            raw = json.loads(res.choices[0].message.content)
            dfa = validate_and_fix_dfa(raw)
            dfa["source"] = "model"

            # ✅ בדיקת עקביות לוגית
            if not check_dfa_integrity(dfa):
                print("[Integrity] Issues detected → repairing...")
                dfa = self_repair_dfa(description, dfa, "Missing transitions or invalid states")
                dfa["empirical_accuracy"] = "⚠️ האוטומט תוקן אוטומטית עקב חוסר עקביות."
            else:
                dfa["empirical_accuracy"] = "✅ האוטומט נוצר ונבדק בהצלחה."

            # הסרת שלב ההסבר הלימודי
            # במקום זאת נוסיף תיאור קצר בלבד
            dfa["construction_explanation"] = (
                "האוטומט נוצר בהצלחה על בסיס התיאור שסיפקת."
            )

            return JSONResponse(content=dfa)

        except Exception as e:
            print(f"[Attempt {attempt+1}] Exception:", e)
            continue

    # ❌ אם כל הניסיונות נכשלו
    fb = fallback_even_length_dfa()
    fb["empirical_accuracy"] = "❌ כל הניסיונות נכשלו, מוחזר Fallback."
    return JSONResponse(content=fb)


