import os
import json
from fastapi.responses import JSONResponse
from openai import OpenAI

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
    alphabet = raw.get("alphabet", ["0", "1"])
    states = list(dict.fromkeys(raw.get("states", []))) or ["q0"]
    start_state = raw.get("start_state", states[0])

    if start_state not in states:
        states.insert(0, start_state)

    accept_states = raw.get("accept_states", [start_state])
    transitions = raw.get("transitions", {})

    fixed_transitions = {}
    for s in states:
        fixed_transitions[s] = {}
        for sym in alphabet:
            dst = transitions.get(s, {}).get(sym, s)
            fixed_transitions[s][sym] = dst

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


# -----------------------------------------------------------
# MAIN ENTRY POINT
# -----------------------------------------------------------
async def generate_automaton_html(description: str) -> JSONResponse:
    print("\n========== New Automaton Request ==========")
    print("[Input]", description)

    if is_non_regular_text(description):
        return JSONResponse({
            "type": "none",
            "explanation": "❌ השפה אינה רגולרית.",
            "source": "analysis",
            "logic": "",
            "accuracy": 0
        })

    if not check_regular_with_gpt(description):
        return JSONResponse({
            "type": "none",
            "explanation": "❌ השפה אינה רגולרית לפי הבדיקה.",
            "source": "analysis",
            "logic": "",
            "accuracy": 0
        })

    # --- Build SPEC ---
    spec = build_language_spec(description)
    print("[SPEC Built]")

    # --- Build DFA ---
    dfa = build_dfa_from_spec(spec)
    print("[DFA Built]")

    # --- Validate DFA ---
    validation = validate_dfa_against_spec(dfa, spec)
    print("[Validation Result]", validation)

    if validation["valid"]:
        dfa["source"] = "model"
        dfa["accuracy"] = validation["score"]
        return JSONResponse(dfa)

    # --- Repair ---
    print("[Repair Attempt]")
    repaired = repair_dfa(description, spec, dfa, validation["errors"])

    validation2 = validate_dfa_against_spec(repaired, spec)
    print("[Re-Validation Result]", validation2)

    if validation2["valid"]:
        repaired["source"] = "repaired"
        repaired["accuracy"] = validation2["score"]
        return JSONResponse(repaired)

    # --- Fallback ---
    fallback = fallback_even_length_dfa()
    fallback["source"] = "fallback"
    fallback["accuracy"] = 0
    return JSONResponse(fallback)
