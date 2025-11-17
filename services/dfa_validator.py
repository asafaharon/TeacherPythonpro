"""
--------------------------------------------------------------------
 DFA VALIDATION SERVICE
--------------------------------------------------------------------
המטרה:
1. לבדוק האם ה-DFA שיצר GPT תואם את החוקים הפורמליים.
2. להריץ את האוטומט על דוגמאות מתקבלות ונדחות.
3. לזהות שגיאות (false accept / false reject).
4. להחזיר רשימת טעויות מלאה — כדי ששלב ה-Repair יתקן.

--------------------------------------------------------------------
"""

def run_dfa(dfa: dict, input_word: str) -> bool:
    """
    מריץ DFA על מחרוזת ומחזיר True אם מתקבלת, אחרת False.
    """
    try:
        current = dfa["start_state"]
        transitions = dfa["transitions"]

        for sym in input_word:
            # אם המשתמש ביקש אלפבית אחר (נדיר), עדיין נטפל
            if sym not in dfa["alphabet"]:
                return False
            current = transitions[current][sym]

        return current in dfa["accept_states"]

    except Exception as e:
        print("[Validator] Error while running DFA:", e)
        return False


def validate_dfa_against_spec(dfa: dict, spec: dict) -> dict:
    """
    מחזיר:
    {
      "valid": bool,
      "errors": [ ... רשימת שגיאות ... ],
      "score": 0–100
    }
    """

    errors = []
    score = 100

    accepted_examples = spec.get("accepted_examples", [])
    rejected_examples = spec.get("rejected_examples", [])

    # --- בדיקה על מילים שצריכות להתקבל ---
    for word in accepted_examples:
        res = run_dfa(dfa, word)
        if not res:
            errors.append({
                "type": "false_reject",
                "word": word,
                "expected": "accept",
                "actual": "reject"
            })
            score -= 15  # כל טעות מורידה ניקוד

    # --- בדיקה על מילים שצריכות להידחות ---
    for word in rejected_examples:
        res = run_dfa(dfa, word)
        if res:
            errors.append({
                "type": "false_accept",
                "word": word,
                "expected": "reject",
                "actual": "accept"
            })
            score -= 15

    # הגבלת ניקוד סופי
    if score < 0:
        score = 0

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "score": score,
    }
