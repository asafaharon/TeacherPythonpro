import json
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

"""
--------------------------------------------------------------------
 LANGUAGE SPECIFICATION SERVICE – FIXED & IMPROVED VERSION
--------------------------------------------------------------------
תפקיד הקובץ:
1. לקבל תיאור טבעי של שפה (בעברית).
2. לבצע reasoning באנגלית (בפנים, כדי לשמור על דיוק).
3. להחזיר SPEC פורמלי, מלא וברור – בעברית בלבד.
4. ה-SPEC הוא הבסיס שממנו נבנה DFA.
--------------------------------------------------------------------
"""

def build_language_spec(description: str) -> dict:
    """
    מקבל תיאור טבעי של שפה ומחזיר SPEC פורמלי בעברית בלבד.
    """

    # -----------------------------
    # SYSTEM PROMPT (באנגלית)
    # -----------------------------
    system_prompt = (
        "You are an expert in automata theory, formal languages, and DFA construction. "
        "You analyze the user's natural-language description IN ENGLISH internally for accuracy, "
        "logic, and completeness. "
        "However, your OUTPUT must be entirely in HEBREW, written clearly and professionally. "
        "The result must be a precise SPEC used to build a DFA. "
        "All text fields must be in Hebrew except DFA state names (q0, q1, etc.). "
        "You must avoid ambiguity entirely and explain the rules and logic in a way suitable "
        "for high-school computer science students (5 units)."
    )

    # -----------------------------
    # USER PROMPT (בטוח ל-f-string)
    # -----------------------------
    user_prompt = (
        "The user described the language in Hebrew:\n"
        f"\"{description}\"\n\n"
        "IMPORTANT:\n"
        "- Think and reason internally IN ENGLISH.\n"
        "- BUT produce the final output entirely in HEBREW.\n"
        "- Output MUST be VALID JSON ONLY.\n"
        "- All fields must contain Hebrew text except state names (q0, q1).\n"
        "- Rules and explanations must be clear and suitable for high-school CS students.\n\n"
        "Return ONLY valid JSON with the following structure (Hebrew content):\n\n"
        "{\n"
        "  \"alphabet\": [\"0\", \"1\"],\n"
        "  \"description_clean\": \"תיאור ברור וקצר של השפה בעברית\",\n"
        "  \"formal_rules\": [\n"
        "      \"כלל 1: ...\",\n"
        "      \"כלל 2: ...\"\n"
        "  ],\n"
        "  \"state_logic\": [\n"
        "      \"q0 = ...\",\n"
        "      \"q1 = ...\"\n"
        "  ],\n"
        "  \"accepted_examples\": [\"דוג1\", \"דוג2\", \"דוג3\"],\n"
        "  \"rejected_examples\": [\"לא1\", \"לא2\", \"לא3\"]\n"
        "}\n\n"
        "Rules:\n"
        "- Return JSON ONLY (no text outside the JSON).\n"
        "- All content must be in Hebrew.\n"
        "- Examples must be short (length ≤ 5).\n"
        "- Rules must be explicit and unambiguous.\n"
    )

    # -----------------------------
    # GPT CALL
    # -----------------------------
    response = client.chat.completions.create(
        model="gpt-4.1",
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    # JSON שמגיע מהמודל
    spec = json.loads(response.choices[0].message.content)

    # -----------------------------
    # ניקוי ותקינות בסיסית
    # -----------------------------
    spec["alphabet"] = spec.get("alphabet", ["0", "1"])
    spec["description_clean"] = spec.get("description_clean", "")
    spec["formal_rules"] = spec.get("formal_rules", [])
    spec["state_logic"] = spec.get("state_logic", [])
    spec["accepted_examples"] = spec.get("accepted_examples", [])
    spec["rejected_examples"] = spec.get("rejected_examples", [])

    return spec
