# services/tm_language_library.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class TMLanguage:
    id: str
    title: str
    description: str
    alphabet_hint: str
    examples_accept: List[str]
    examples_reject: List[str]
    spec: Dict[str, Any]


def _spec_only_as() -> Dict[str, Any]:
    # L = { a* } over alphabet {a,b}. Accepts empty.
    return {
        "type": "TM",
        "states": ["q0", "qa", "qr"],
        "input_alphabet": ["a", "b"],
        "tape_alphabet": ["a", "b", "_"],
        "blank": "_",
        "start_state": "q0",
        "accept_states": ["qa"],
        "reject_states": ["qr"],
        "transitions": [
            {"from": "q0", "read": "a", "to": "q0", "write": "a", "move": "R"},
            {"from": "q0", "read": "_", "to": "qa", "write": "_", "move": "S"},
            {"from": "q0", "read": "b", "to": "qr", "write": "b", "move": "S"},
        ],
    }


def _spec_even_as() -> Dict[str, Any]:
    # L = { a^(2k) } (even number of a). Treats any b/c as reject.
    return {
        "type": "TM",
        "states": ["qE", "qO", "qa", "qr"],
        "input_alphabet": ["a", "b"],
        "tape_alphabet": ["a", "b", "_"],
        "blank": "_",
        "start_state": "qE",
        "accept_states": ["qa"],
        "reject_states": ["qr"],
        "transitions": [
            {"from": "qE", "read": "a", "to": "qO", "write": "a", "move": "R"},
            {"from": "qO", "read": "a", "to": "qE", "write": "a", "move": "R"},
            {"from": "qE", "read": "_", "to": "qa", "write": "_", "move": "S"},
            {"from": "qO", "read": "_", "to": "qr", "write": "_", "move": "S"},
            {"from": "qE", "read": "b", "to": "qr", "write": "b", "move": "S"},
            {"from": "qO", "read": "b", "to": "qr", "write": "b", "move": "S"},
        ],
    }


def _spec_anbn() -> Dict[str, Any]:
    # L = { a^n b^n | n>=1 }.
    # Strategy:
    # 1) Mark leftmost unmarked a as X
    # 2) Scan right to first unmarked b and mark as Y
    # 3) Go back to left boundary and repeat
    # 4) When no a left -> verify no unmarked b left -> accept
    return {
        "type": "TM",
        "states": ["qS", "q0", "q1", "qBack", "qCheck", "qa", "qr"],
        "input_alphabet": ["a", "b"],
        "tape_alphabet": ["a", "b", "X", "Y", "_"],
        "blank": "_",
        "start_state": "qS",
        "accept_states": ["qa"],
        "reject_states": ["qr"],
        "transitions": [
            # qS: enforce n>=1
            {"from": "qS", "read": "a", "to": "q0", "write": "a", "move": "S"},
            {"from": "qS", "read": "b", "to": "qr", "write": "b", "move": "S"},
            {"from": "qS", "read": "_", "to": "qr", "write": "_", "move": "S"},

            # q0: find an unmarked a
            {"from": "q0", "read": "X", "to": "q0", "write": "X", "move": "R"},
            {"from": "q0", "read": "Y", "to": "q0", "write": "Y", "move": "R"},
            {"from": "q0", "read": "a", "to": "q1", "write": "X", "move": "R"},
            {"from": "q0", "read": "b", "to": "qr", "write": "b", "move": "S"},
            {"from": "q0", "read": "_", "to": "qCheck", "write": "_", "move": "L"},

            # q1: find matching unmarked b
            {"from": "q1", "read": "a", "to": "q1", "write": "a", "move": "R"},
            {"from": "q1", "read": "X", "to": "q1", "write": "X", "move": "R"},
            {"from": "q1", "read": "Y", "to": "q1", "write": "Y", "move": "R"},
            {"from": "q1", "read": "b", "to": "qBack", "write": "Y", "move": "L"},
            {"from": "q1", "read": "_", "to": "qr", "write": "_", "move": "S"},

            # qBack: go back to left boundary
            {"from": "qBack", "read": "a", "to": "qBack", "write": "a", "move": "L"},
            {"from": "qBack", "read": "b", "to": "qBack", "write": "b", "move": "L"},
            {"from": "qBack", "read": "X", "to": "qBack", "write": "X", "move": "L"},
            {"from": "qBack", "read": "Y", "to": "qBack", "write": "Y", "move": "L"},
            {"from": "qBack", "read": "_", "to": "q0", "write": "_", "move": "R"},

            # qCheck: ensure no unmarked b remains (we scan left to left blank)
            {"from": "qCheck", "read": "X", "to": "qCheck", "write": "X", "move": "L"},
            {"from": "qCheck", "read": "Y", "to": "qCheck", "write": "Y", "move": "L"},
            {"from": "qCheck", "read": "a", "to": "qr", "write": "a", "move": "S"},
            {"from": "qCheck", "read": "b", "to": "qr", "write": "b", "move": "S"},
            {"from": "qCheck", "read": "_", "to": "qa", "write": "_", "move": "S"},
        ],
    }


def _spec_anbncn() -> Dict[str, Any]:
    # L = { a^n b^n c^n | n>=1 } (NOT CFL).
    # Strategy:
    # 1) Mark leftmost unmarked a as X
    # 2) Find leftmost unmarked b and mark as Y
    # 3) Find leftmost unmarked c and mark as Z
    # 4) Return to left boundary and repeat
    # 5) When no a left -> verify no unmarked b/c -> accept
    return {
        "type": "TM",
        "states": ["qS", "q0", "q1", "q2", "qBack", "qCheck", "qa", "qr"],
        "input_alphabet": ["a", "b", "c"],
        "tape_alphabet": ["a", "b", "c", "X", "Y", "Z", "_"],
        "blank": "_",
        "start_state": "qS",
        "accept_states": ["qa"],
        "reject_states": ["qr"],
        "transitions": [
            # qS: enforce n>=1 and correct first symbol
            {"from": "qS", "read": "a", "to": "q0", "write": "a", "move": "S"},
            {"from": "qS", "read": "b", "to": "qr", "write": "b", "move": "S"},
            {"from": "qS", "read": "c", "to": "qr", "write": "c", "move": "S"},
            {"from": "qS", "read": "_", "to": "qr", "write": "_", "move": "S"},

            # q0: find unmarked a
            {"from": "q0", "read": "X", "to": "q0", "write": "X", "move": "R"},
            {"from": "q0", "read": "Y", "to": "q0", "write": "Y", "move": "R"},
            {"from": "q0", "read": "Z", "to": "q0", "write": "Z", "move": "R"},
            {"from": "q0", "read": "a", "to": "q1", "write": "X", "move": "R"},
            {"from": "q0", "read": "b", "to": "qr", "write": "b", "move": "S"},
            {"from": "q0", "read": "c", "to": "qr", "write": "c", "move": "S"},
            {"from": "q0", "read": "_", "to": "qCheck", "write": "_", "move": "L"},

            # q1: find unmarked b
            {"from": "q1", "read": "a", "to": "q1", "write": "a", "move": "R"},
            {"from": "q1", "read": "X", "to": "q1", "write": "X", "move": "R"},
            {"from": "q1", "read": "Y", "to": "q1", "write": "Y", "move": "R"},
            {"from": "q1", "read": "b", "to": "q2", "write": "Y", "move": "R"},
            {"from": "q1", "read": "Z", "to": "qr", "write": "Z", "move": "S"},
            {"from": "q1", "read": "c", "to": "qr", "write": "c", "move": "S"},
            {"from": "q1", "read": "_", "to": "qr", "write": "_", "move": "S"},

            # q2: find unmarked c
            {"from": "q2", "read": "b", "to": "q2", "write": "b", "move": "R"},
            {"from": "q2", "read": "Y", "to": "q2", "write": "Y", "move": "R"},
            {"from": "q2", "read": "Z", "to": "q2", "write": "Z", "move": "R"},
            {"from": "q2", "read": "c", "to": "qBack", "write": "Z", "move": "L"},
            {"from": "q2", "read": "a", "to": "qr", "write": "a", "move": "S"},
            {"from": "q2", "read": "X", "to": "qr", "write": "X", "move": "S"},
            {"from": "q2", "read": "_", "to": "qr", "write": "_", "move": "S"},

            # qBack: go back to left boundary
            {"from": "qBack", "read": "a", "to": "qBack", "write": "a", "move": "L"},
            {"from": "qBack", "read": "b", "to": "qBack", "write": "b", "move": "L"},
            {"from": "qBack", "read": "c", "to": "qBack", "write": "c", "move": "L"},
            {"from": "qBack", "read": "X", "to": "qBack", "write": "X", "move": "L"},
            {"from": "qBack", "read": "Y", "to": "qBack", "write": "Y", "move": "L"},
            {"from": "qBack", "read": "Z", "to": "qBack", "write": "Z", "move": "L"},
            {"from": "qBack", "read": "_", "to": "q0", "write": "_", "move": "R"},

            # qCheck: scan left to left blank and ensure no unmarked b/c/a remain
            {"from": "qCheck", "read": "X", "to": "qCheck", "write": "X", "move": "L"},
            {"from": "qCheck", "read": "Y", "to": "qCheck", "write": "Y", "move": "L"},
            {"from": "qCheck", "read": "Z", "to": "qCheck", "write": "Z", "move": "L"},
            {"from": "qCheck", "read": "a", "to": "qr", "write": "a", "move": "S"},
            {"from": "qCheck", "read": "b", "to": "qr", "write": "b", "move": "S"},
            {"from": "qCheck", "read": "c", "to": "qr", "write": "c", "move": "S"},
            {"from": "qCheck", "read": "_", "to": "qa", "write": "_", "move": "S"},
        ],
    }


_LANGUAGES: List[TMLanguage] = [
    TMLanguage(
        id="astar",
        title="L = a* (רק a-ים)",
        description="כל מחרוזת שמכילה רק את האות a (כולל ריקה). כל הופעה של b דוחה.",
        alphabet_hint="Σ = {a,b}",
        examples_accept=["", "a", "aaaa"],
        examples_reject=["b", "ab", "aab"],
        spec=_spec_only_as(),
    ),
    TMLanguage(
        id="even_a",
        title="מספר זוגי של a",
        description="המכונה מקבלת אם מספר ה-a בקלט הוא זוגי. (כל b דוחה).",
        alphabet_hint="Σ = {a,b}",
        examples_accept=["", "aa", "aaaa"],
        examples_reject=["a", "aaa", "b"],
        spec=_spec_even_as(),
    ),
    TMLanguage(
        id="anbn",
        title="L = a^n b^n (n≥1)",
        description="מספר ה-a שווה למספר ה-b, וכל ה-a לפני ה-b.",
        alphabet_hint="Σ = {a,b}",
        examples_accept=["ab", "aabb", "aaabbb"],
        examples_reject=["", "abb", "aab", "ba", "aabbb"],
        spec=_spec_anbn(),
    ),
    TMLanguage(
        id="anbncn",
        title="L = a^n b^n c^n (n≥1) — TM כן, PDA לא",
        description="מספר ה-a שווה למספר ה-b שווה למספר ה-c, לפי הסדר a...b...c. זו שפה שאינה חופשית־הקשר.",
        alphabet_hint="Σ = {a,b,c}",
        examples_accept=["abc", "aabbcc", "aaabbbccc"],
        examples_reject=["", "aabbc", "aaabbbcc", "abcabc", "abcc"],
        spec=_spec_anbncn(),
    ),
]


def list_languages() -> List[Dict[str, Any]]:
    return [
        {
            "id": l.id,
            "title": l.title,
            "description": l.description,
            "alphabet_hint": l.alphabet_hint,
            "examples_accept": l.examples_accept,
            "examples_reject": l.examples_reject,
        }
        for l in _LANGUAGES
    ]


def get_language(language_id: str) -> TMLanguage:
    for l in _LANGUAGES:
        if l.id == language_id:
            return l
    raise ValueError(f"Unknown language_id: {language_id}")
