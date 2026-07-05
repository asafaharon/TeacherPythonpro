# services/tm_service.py
import json
import logging
import os
import re
from typing import Any, Dict, Tuple

from openai import OpenAI

from services.tm_simulator import validate_tm_spec, TMSpecError

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL_NAME = os.getenv("TM_MODEL", "gpt-4o-mini")


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Robustly extract JSON object from LLM output (handles code fences).
    """
    if not text:
        raise ValueError("Empty model response")

    # Remove code fences if present
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    # Try direct JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to find first {...} block
    m = re.search(r"(\{.*\})", text, re.DOTALL)
    if not m:
        raise ValueError("Could not locate JSON object in model output")
    return json.loads(m.group(1))


def _build_prompts(language_description: str, alphabet_hint: str | None) -> Tuple[str, str]:
    system_prompt = (
        "You are an expert in Turing Machines (single-tape deterministic TM) and formal languages. "
        "Think internally in ENGLISH. "
        "Return ONLY valid JSON. No markdown. No code fences.\n\n"
        "Goal: Build a deterministic TM specification that DECIDES the language described by the user.\n\n"
        "Constraints:\n"
        "- Return JSON with fields:\n"
        "  type: 'TM' or 'none'\n"
        "  states: [..]\n"
        "  input_alphabet: [..] (single-character symbols)\n"
        "  tape_alphabet: [..] must include blank\n"
        "  blank: '_' (single char)\n"
        "  start_state: 'q0'\n"
        "  accept_states: [..]\n"
        "  reject_states: [..]\n"
        "  transitions: [ {from, read, to, write, move} ... ]\n"
        "- move is one of: 'L','R','S'\n"
        "- Deterministic: for each (from, read) at most one transition.\n"
        "- All read/write symbols must be single characters and in tape_alphabet.\n"
        "- Keep the machine SMALL and DEMO-friendly.\n"
        "- If the language description is unclear / non-decidable / requires multi-tape, return type='none' with a Hebrew explanation.\n\n"
        "Also include (optional) extra fields for UI:\n"
        "- explanation_he: short Hebrew explanation\n"
        "- examples: { accepted: [...], rejected: [...] }\n"
    )

    user_prompt = (
        "Build a deterministic single-tape TM that decides the following language.\n\n"
        f"Language description (natural language):\n\"{language_description.strip()}\"\n\n"
    )
    if alphabet_hint and alphabet_hint.strip():
        user_prompt += f"Alphabet hint from user (may help): \"{alphabet_hint.strip()}\"\n\n"
    user_prompt += "Return ONLY the JSON TM spec."

    return system_prompt, user_prompt


def generate_tm_from_nl(language_description: str, alphabet_hint: str | None = None) -> Dict[str, Any]:
    """
    Generate a TM spec from natural language description.
    Performs validation and one repair attempt if needed.
    """
    system_prompt, user_prompt = _build_prompts(language_description, alphabet_hint)

    def call(messages):
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.2,
            max_tokens=1200,
        )
        return (resp.choices[0].message.content or "").strip()

    try:
        raw = call(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        data = _extract_json(raw)

        if data.get("type") == "none":
            return data

        # enforce a few defaults if missing
        data.setdefault("type", "TM")
        data.setdefault("blank", "_")
        if "start_state" not in data:
            data["start_state"] = "q0"

        # Validate
        validate_tm_spec(data)
        return data

    except (TMSpecError, ValueError, json.JSONDecodeError) as e:
        logger.warning("TM generation produced invalid spec. Attempting repair. Error=%s", e)

        # One repair attempt with explicit error message
        repair_system = system_prompt + "\nYou must FIX the JSON to satisfy the constraints and validation."
        repair_user = (
            "Your previous output was invalid.\n"
            f"Validation/parse error: {str(e)}\n\n"
            "Return a corrected TM JSON spec now, ONLY JSON."
        )

        try:
            raw2 = call(
                [
                    {"role": "system", "content": repair_system},
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": "INVALID"},
                    {"role": "user", "content": repair_user},
                ]
            )
            data2 = _extract_json(raw2)
            if data2.get("type") == "none":
                return data2
            data2.setdefault("type", "TM")
            data2.setdefault("blank", "_")
            data2.setdefault("start_state", "q0")
            validate_tm_spec(data2)
            return data2
        except Exception as e2:
            logger.exception("TM repair attempt failed")
            return {
                "type": "none",
                "explanation_he": "לא הצלחתי לייצר מכונת טיורינג תקינה מהתיאור. נסה לתאר את השפה בצורה יותר פורמלית (אלפבית, תנאי קבלה, דוגמאות).",
                "error": str(e2),
            }
    except Exception as e:
        logger.exception("Unexpected TM generation error")
        return {
            "type": "none",
            "explanation_he": "שגיאה לא צפויה בזמן יצירת מכונת טיורינג.",
            "error": str(e),
        }
