import os
import json
from fastapi.responses import JSONResponse
from openai import OpenAI
from services.language_spec_service import check_language_regularity

from services.language_spec_service import build_language_spec
from services.dfa_validator import validate_dfa_against_spec

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

"""
====================================================================
 AUTOMATON SERVICE – Updated Version  
 - Reasoning in English
 - Output in Hebrew
====================================================================
"""

# -----------------------------------------------------------
# Fallback DFA
# -----------------------------------------------------------
def fallback_even_length_dfa():
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
        "explanation": "האוטומט מקבל מילים שאורכן זוגי.",
        "logic": "בכל פעם שנקלט תו, עוברים בין המצבים q_even ↔ q_odd.",
        "source": "fallback",
        "accuracy": 0
    }


# -----------------------------------------------------------
# Validate and fix missing DFA fields
# -----------------------------------------------------------
def validate_and_fix_dfa(raw: dict) -> dict:
    """
    Makes the DFA formally TOTAL and safe to run.
    Any referenced but undefined state (e.g. TRAP / reject)
    becomes a closed sink state.
    """

    alphabet = raw.get("alphabet", ["0", "1"])
    states = list(dict.fromkeys(raw.get("states", []))) or ["q0"]
    start_state = raw.get("start_state", states[0])

    if start_state not in states:
        states.insert(0, start_state)

    accept_states = raw.get("accept_states", [])
    transitions = raw.get("transitions", {})

    fixed_transitions = {}
    referenced_states = set(states)

    # --- Build transitions & collect referenced states ---
    for state in states:
        fixed_transitions[state] = {}

        for sym in alphabet:
            dst = transitions.get(state, {}).get(sym)

            if dst is None:
                dst = "TRAP"

            fixed_transitions[state][sym] = dst
            referenced_states.add(dst)

    # --- Add missing referenced states as sink states ---
    for state in referenced_states:
        if state not in fixed_transitions:
            fixed_transitions[state] = {}
            for sym in alphabet:
                fixed_transitions[state][sym] = state

            if state not in states:
                states.append(state)

    # --- Sink states must never be accepting ---
    accept_states = [s for s in accept_states if s in states and s not in referenced_states - set(states)]

    return {
        "type": "DFA",
        "alphabet": alphabet,
        "states": states,
        "start_state": start_state,
        "accept_states": accept_states,
        "transitions": fixed_transitions,
        "explanation": raw.get("explanation", ""),
        "logic": raw.get("logic", ""),
        "simulation": raw.get("simulation", {}),
    }





# -----------------------------------------------------------
# Build DFA from SPEC
# -----------------------------------------------------------
def build_dfa_from_spec(spec: dict) -> dict:
    system_prompt = (
        "You are an expert in automata theory and DFA construction. "
        "Think and reason internally in ENGLISH only. "
        "BUT produce the final DFA explanation, logic, and all text fields IN HEBREW. "
        "You MUST build the DFA strictly based on the provided SPEC only. "
        "Do NOT interpret natural language. "
        "Use ONLY the formal_rules, alphabet, and state_logic from the SPEC. "
        "Your JSON output must be fully valid."
    )

    user_prompt = (
        "Build a DFA according to the following SPEC:\n\n"
        f"{json.dumps(spec, ensure_ascii=False)}\n\n"
        "Return ONLY valid JSON in the following structure (Hebrew content):\n\n"
        "{\n"
        "  \"type\": \"DFA\",\n"
        "  \"alphabet\": [\"0\", \"1\"],\n"
        "  \"states\": [\"q0\", \"q1\", \"q2\"],\n"
        "  \"start_state\": \"q0\",\n"
        "  \"accept_states\": [\"q1\"],\n"
        "  \"transitions\": {\n"
        "      \"q0\": {\"0\": \"q1\", \"1\": \"q0\"}\n"
        "  },\n"
        "  \"explanation\": \"הסבר בעברית על מה האוטומט מקבל.\",\n"
        "  \"logic\": \"היגיון הפעולה של האוטומט בעברית.\",\n"
        "  \"simulation\": {\n"
        "      \"accepted_example\": {},\n"
        "      \"rejected_example\": {}\n"
        "  }\n"
        "}\n"
    )

    response = client.chat.completions.create(
        model="gpt-4.1",
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_dfa = json.loads(response.choices[0].message.content)
    return validate_and_fix_dfa(raw_dfa)


# -----------------------------------------------------------
# Repair DFA
# -----------------------------------------------------------
def repair_dfa(description: str, spec: dict, dfa: dict, errors: list) -> dict:
    system_prompt = (
        "You are an expert in repairing incorrect DFAs. "
        "Think internally in ENGLISH, but OUTPUT all explanations in HEBREW. "
        "The corrected DFA must satisfy the SPEC completely."
    )

    user_prompt = (
        "The DFA failed validation.\n\n"
        f"Description:\n\"{description}\"\n\n"
        f"SPEC:\n{json.dumps(spec, ensure_ascii=False)}\n\n"
        f"Current DFA:\n{json.dumps(dfa, ensure_ascii=False)}\n\n"
        f"Errors:\n{json.dumps(errors, ensure_ascii=False)}\n\n"
        "Please FIX the DFA. Return ONLY valid JSON for the corrected DFA.\n"
        "The explanation and logic MUST be in Hebrew."
    )

    response = client.chat.completions.create(
        model="gpt-4.1",
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    fixed_raw = json.loads(response.choices[0].message.content)
    return validate_and_fix_dfa(fixed_raw)


# -----------------------------------------------------------
# Non-regular detection
# -----------------------------------------------------------
NON_REGULAR_KEYWORDS = [
    "equal number", "same number", "count", "counts equal",
    "שווה למספר", "מספר זהה", "aⁿbⁿ", "anbn"
]


def is_non_regular_text(description: str) -> bool:
    return any(kw in description for kw in NON_REGULAR_KEYWORDS)


def check_regular_with_gpt(description: str) -> bool:
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Return {'regular': true/false} only."},
                {"role": "user", "content": f"Language: {description}"}
            ],
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("regular", True)
    except Exception:
        return True

# automaton_service.py
# ספי מוצר – אפשר לכוונן
DISPLAY_THRESHOLD = 70      # מציגים אוטומט
REPAIR_THRESHOLD = 85       # שווה לנסות Repair
STRICT_THRESHOLD = 95       # אוטומט “כמעט מושלם”

async def generate_automaton_html(description: str) -> JSONResponse:
    print("\n========== New Automaton Request ==========")
    print("[Input]", description)

    # ====================================================
    # 0️⃣ בדיקת רגולריות – דרך ה־API (שלב חדש!)
    # ====================================================
    regularity = check_language_regularity(description)
    print("[Regularity Check]", regularity)

    if not regularity.get("is_regular", False):
        return JSONResponse({
            "type": "none",
            "status": "non_regular_language",

            # 👇 הודעה קצרה וברורה למשתמש
            "user_message": "השפה שביקשת אינה שפה רגולרית ולכן לא ניתן לבנות עבורה אוטומט סופי.",

            # 👇 הסבר ארוך יותר (לא חובה להציג ב־UI)
            "details": regularity.get("reason", "")
        })

    # ====================================================
    # 1️⃣ בניית SPEC
    # ====================================================
    spec = build_language_spec(description)
    print("[SPEC Built]")

    # ====================================================
    # 2️⃣ בניית DFA ראשוני
    # ====================================================
    dfa = build_dfa_from_spec(spec)
    print("[DFA Built]")

    # ====================================================
    # 3️⃣ אימות (רך)
    # ====================================================
    validation = validate_dfa_against_spec(dfa, spec)
    print("[Validation Result]", validation)

    score = validation.get("score", 0)

    # 🟢 אוטומט איכותי מאוד
    if score >= STRICT_THRESHOLD:
        dfa["source"] = "model"
        dfa["accuracy"] = score
        dfa["status"] = "high_confidence"
        dfa["warnings"] = []
        return JSONResponse(dfa)

    # 🟡 אוטומט סביר – מציגים עם אזהרות
    if score >= DISPLAY_THRESHOLD:
        dfa["source"] = "model"
        dfa["accuracy"] = score
        dfa["status"] = "approximate"
        dfa["warnings"] = validation.get("errors", [])
        return JSONResponse(dfa)

    # 🔵 ניסיון Repair (רשות)
    if score >= REPAIR_THRESHOLD:
        print("[Repair Attempt]")
        repaired = repair_dfa(description, spec, dfa, validation.get("errors", []))
        validation2 = validate_dfa_against_spec(repaired, spec)
        print("[Re-Validation Result]", validation2)

        score2 = validation2.get("score", 0)

        if score2 >= DISPLAY_THRESHOLD:
            repaired["source"] = "repaired"
            repaired["accuracy"] = score2
            repaired["status"] = "approximate"
            repaired["warnings"] = validation2.get("errors", [])
            return JSONResponse(repaired)

    # 🔴 איכות נמוכה – עדיין מציגים (מדיניות מוצר)
    dfa["source"] = "low_confidence"
    dfa["accuracy"] = score
    dfa["status"] = "low_confidence"
    dfa["warnings"] = validation.get("errors", [])
    dfa["note"] = (
        "⚠️ האוטומט הוצג ברמת אמינות נמוכה. "
        "ייתכן שאינו מייצג במדויק את השפה."
    )
    return JSONResponse(dfa)