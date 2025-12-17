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
from services.language_spec_service import check_language_regularity

def run_dfa(dfa: dict, input_word: str) -> bool:
    """
    מריץ DFA על מחרוזת ומחזיר True אם מתקבלת, אחרת False.
    במקרה של שגיאה פנימית – מדפיס ומרים חריגה, כדי שה-validator ידע שיש בעיה.
    """
    try:
        current = dfa["start_state"]
        transitions = dfa["transitions"]

        for sym in input_word:
            if sym not in dfa["alphabet"]:
                return False
            current = transitions[current][sym]

        return current in dfa["accept_states"]

    except Exception as e:
        print("[Validator] Error while running DFA:", e)
        # כאן עדיף לזרוק חריגה, כדי שלא תיספר “סתם” כדחייה:
        raise


def validate_dfa_against_spec(dfa: dict, spec: dict) -> dict:
    errors = []
    score = 100

    accepted_examples = spec.get("accepted_examples", [])
    rejected_examples = spec.get("rejected_examples", [])

    # אם אין בכלל דוגמאות – לא סומכים על ה-DFA
    if not accepted_examples and not rejected_examples:
        return {
            "valid": False,
            "errors": [{
                "type": "no_examples",
                "msg": "לא סופקו דוגמאות מתקבלות/נדחות ב-SPEC."
            }],
            "score": 0,
        }

    # --- מילים שצריכות להתקבל ---
    for word in accepted_examples:
        res = run_dfa(dfa, word)
        if not res:
            errors.append({
                "type": "false_reject",
                "word": word,
                "expected": "accept",
                "actual": "reject"
            })
            score -= 15

    # --- מילים שצריכות להידחות ---
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

    if score < 0:
        score = 0

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "score": score,
    }
