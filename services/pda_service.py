import os
import json
import logging
from typing import Any, Dict, List

from openai import OpenAI

from services.pda_simulator import run_pda

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _normalize_symbol(symbol: Any, allow_epsilon: bool = True) -> str:
    """
    מנרמל סימן קלט/מחסנית כך שהערכים:
      - None
      - "" (מחרוזת ריקה)
      - "ε", "eps", "epsilon"
    ייחשבו כולם כמעבר אפסילון (אם allow_epsilon=True) ויוחזרו כמחרוזת ריקה "".

    בכל מקרה מחזיר מחרוזת.
    """
    if symbol is None:
        return "" if allow_epsilon else ""
    if not isinstance(symbol, str):
        symbol = str(symbol)

    s = symbol.strip()
    if allow_epsilon and s in {"", "ε", "eps", "epsilon"}:
        return ""
    return s


def _normalize_push_list(push_raw: Any) -> List[str]:
    """
    מנרמל את רשימת הסימנים שדוחפים למחסנית.
    • אם זה מחרוזת: "AZ" -> ["A", "Z"]
    • אם זה "ε" או ריק: -> []
    • אם זו רשימה: מחזיר רשימת מחרוזות ללא "ε" / ריקים.
    """
    if push_raw is None:
        return []

    # אם זו כבר רשימה
    if isinstance(push_raw, list):
        result: List[str] = []
        for item in push_raw:
            s = _normalize_symbol(item, allow_epsilon=True)
            if s != "":
                result.append(s)
        return result

    # אם זו מחרוזת
    if isinstance(push_raw, str):
        s = push_raw.strip()
        if s in {"", "ε", "eps", "epsilon"}:
            return []
        # מפרקים לתווים
        return [ch for ch in s if ch not in {" ", "ε"}]

    # כל דבר אחר – נתעלם
    return []


def _normalize_pda(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    מנרמל את מבנה ה-PDA ש-GPT מחזיר לפורמט אחיד עבור הסימולטור.
    תומך ב-NPDA עם מעברי אפסילון (read == "").
    """
    pda_type = raw.get("type", "PDA")

    # אם המודל ציין מפורשות שאין PDA מתאים
    if pda_type != "PDA":
        return {
            "type": "none",
            "explanation": raw.get(
                "explanation",
                "❌ לא ניתן היה לבנות אוטומט מחסנית עבור התיאור שניתן.",
            ),
            "source": raw.get("source", "model"),
            "logic": raw.get("logic", ""),
            "accuracy": 0,
        }

    input_alphabet = list(dict.fromkeys(raw.get("input_alphabet", [])))
    stack_alphabet = list(dict.fromkeys(raw.get("stack_alphabet", [])))
    states: List[str] = list(dict.fromkeys(raw.get("states", []))) or ["q0"]

    start_state = raw.get("start_state", states[0])
    if start_state not in states:
        states.insert(0, start_state)

    accept_states = raw.get("accept_states", [start_state])
    accept_states = [s for s in accept_states if s in states] or [start_state]

    initial_stack_symbol = raw.get("initial_stack_symbol", "Z")
    if initial_stack_symbol not in stack_alphabet:
        stack_alphabet.append(initial_stack_symbol)

    transitions_raw = raw.get("transitions", [])
    transitions_fixed: List[Dict[str, Any]] = []

    for idx, t in enumerate(transitions_raw):
        try:
            from_state = t["from"]
            to_state = t["to"]
        except KeyError:
            logger.warning("Skipping malformed PDA transition (missing from/to): %s", t)
            continue

        read_raw = t.get("read", "")
        pop_raw = t.get("pop", "")

        read_symbol = _normalize_symbol(read_raw, allow_epsilon=True)
        pop_symbol = _normalize_symbol(pop_raw, allow_epsilon=True)

        push_list = _normalize_push_list(t.get("push", []))

        transitions_fixed.append(
            {
                "from": from_state,
                "to": to_state,
                # read == "" → מעבר ε
                "read": read_symbol,
                # pop == "" → לא מושכים מהמחסנית
                "pop": pop_symbol,
                # push: רשימת סמלים לפי סדר "מלמטה למעלה"
                "push": push_list,
                "_index": idx,  # אינדקס פנימי, שימושי ל־UI
            }
        )

    return {
        "type": "PDA",
        "input_alphabet": input_alphabet,
        "stack_alphabet": stack_alphabet,
        "states": states,
        "start_state": start_state,
        "accept_states": accept_states,
        "initial_stack_symbol": initial_stack_symbol,
        "transitions": transitions_fixed,
        "explanation": raw.get("explanation", ""),
        "logic": raw.get("logic", ""),
        "simulation_examples": raw.get("simulation_examples", {}),
        "source": raw.get("source", "model"),
        "accuracy": raw.get("accuracy", 100),
    }


async def generate_pda(description: str) -> Dict[str, Any]:
    """
    יוצר NPDA (אוטומט מחסנית לא-דטרמיניסטי עם מעברי אפסילון) מתיאור שפה טבעית.
    """
    logger.info("Generating PDA from description: %s", description)

    system_prompt = (
        "You are an expert in nondeterministic pushdown automata (NPDA) "
        "and context-free languages. "
        "You reason and plan INTERNALLY in ENGLISH only. "
        "HOWEVER, all natural-language EXPLANATIONS in the JSON "
        "(explanation, logic) MUST be written in clear HEBREW, "
        "as if you are talking to Israeli CS students.\n\n"
        "You are allowed to build NONDETERMINISTIC PDAs with epsilon-transitions.\n"
        "- The PDA may have multiple transitions for the same (state, input_symbol, stack_top).\n"
        "- You MAY use epsilon-transitions where read == \"\" or \"ε\".\n"
        "- A transition with pop == \"\" means you do NOT pop from the stack.\n"
        "- The 'push' field is a LIST of stack symbols, ordered from BOTTOM to TOP.\n"
        "  For example, push: [\"A\", \"Z\"] means: first push Z, then A is below it.\n"
        "Your PDA should be correct but also reasonably small and readable.\n"
    )

    user_prompt = (
        "The user provides a natural-language description (in Hebrew or English) "
        "of a formal language. Your task: build a nondeterministic PDA (NPDA) "
        "that recognizes this language.\n\n"
        "Language description:\n"
        f"\"{description}\"\n\n"
        "Return ONLY valid JSON in the following structure:\n\n"
        "{\n"
        "  \"type\": \"PDA\" or \"none\",\n"
        "  \"input_alphabet\": [\"a\", \"b\"],\n"
        "  \"stack_alphabet\": [\"Z\", \"A\"],\n"
        "  \"states\": [\"q0\", \"q1\", \"q2\"],\n"
        "  \"start_state\": \"q0\",\n"
        "  \"accept_states\": [\"q2\"],\n"
        "  \"initial_stack_symbol\": \"Z\",\n"
        "  \"transitions\": [\n"
        "    {\n"
        "      \"from\": \"q0\",\n"
        "      \"to\": \"q0\",\n"
        "      \"read\": \"a\" or \"\" or \"ε\",  // empty string means epsilon-transition\n"
        "      \"pop\": \"Z\" or \"\" or \"ε\",   // empty => do not pop\n"
        "      \"push\": [\"A\", \"Z\"]          // list of symbols, bottom-to-top; [] means push nothing\n"
        "    }\n"
        "  ],\n"
        "  \"explanation\": \"הסבר בעברית על מה האוטומט מקבל.\",\n"
        "  \"logic\": \"היגיון הפעולה של האוטומט בעברית.\",\n"
        "  \"simulation_examples\": {\n"
        "      \"accepted\": [\"aaabbb\"],\n"
        "      \"rejected\": [\"aab\"]\n"
        "  },\n"
        "  \"source\": \"model\",\n"
        "  \"accuracy\": 100\n"
        "}\n\n"
        "If the language is clearly NOT context-free and cannot be modeled by any PDA, "
        "return JSON with:\n"
        "{ \"type\": \"none\", \"explanation\": \"הסבר בעברית למה זו לא שפה חופשית הקשר.\", \"source\": \"model\" }\n"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_content = response.choices[0].message.content
        logger.debug("Raw PDA JSON from GPT: %s", raw_content)

        raw = json.loads(raw_content)
        normalized = _normalize_pda(raw)
        logger.info("PDA normalized successfully. Type=%s", normalized.get("type"))
        return normalized

    except Exception as exc:
        logger.exception("Error while calling OpenAI for PDA generation: %s", exc)
        return {
            "type": "none",
            "explanation": "❌ התרחשה שגיאה בעת יצירת אוטומט המחסנית.",
            "source": "error",
            "logic": "",
            "accuracy": 0,
        }


async def simulate_pda_word(pda: Dict[str, Any], word: str) -> Dict[str, Any]:
    """
    מריץ NPDA על מחרוזת יחידה ומחזיר:
      - accepted: האם המילה התקבלה על ידי לפחות הרצה אחת.
      - trace: Trace של אחד המסלולים (בד\"כ מסלול מקבל, אם קיים).
    """
    try:
        accepted, trace = run_pda(pda, word)
        return {
            "accepted": accepted,
            "trace": trace,
        }
    except Exception as exc:
        logger.exception("Error while simulating PDA word: %s", exc)
        return {
            "accepted": False,
            "trace": [],
            "error": "❌ שגיאה בהרצת האוטומט על המחרוזת.",
        }
