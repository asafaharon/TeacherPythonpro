from collections import deque
from typing import Any, Deque, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

# קונפיגורציה של NPDA: מצב, מיקום בקלט, ותוכן מחסנית
Configuration = Tuple[str, int, Tuple[str, ...]]  # (state, position in input, stack tuple)


def run_pda(
    pda: Dict[str, Any],
    input_word: str,
    max_steps: int = 2000,
    max_configs: int = 3000,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    סימולטור ל-NPDA עם מעברי אפסילון.
    • מקבל PDA במבנה שנוצר על ידי _normalize_pda.
    • מריץ חיפוש BFS על מרחב הקונפיגורציות (state, position, stack).
    • מחזיר:
        - accepted: האם קיימת הרצה שמסתיימת במצב מקבל לאחר צריכת כל הקלט.
        - trace: Trace של אחד המסלולים (אם יש מסלול מקבל, נחזיר מסלול כזה).
    המגבלות max_steps, max_configs מגנות מפני לולאות אינסופיות והתפוצצות אי-דטרמיניזם.
    """
    if pda.get("type") != "PDA":
        logger.warning("run_pda called with non-PDA type: %s", pda.get("type"))
        return False, []

    states: List[str] = pda.get("states", [])
    start_state: str = pda.get("start_state", states[0] if states else "")
    accept_states = set(pda.get("accept_states", []))
    initial_stack_symbol: str = pda.get("initial_stack_symbol", "Z")

    transitions_raw = pda.get("transitions", [])

    # בניית מפה: (from_state, read_symbol) -> [transition, ...]
    # read_symbol == "" => מעבר אפסילון
    transitions_map: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for t in transitions_raw:
        from_state = t.get("from")
        read_symbol = t.get("read", "")
        if from_state is None:
            logger.warning("Skipping transition without 'from' field: %s", t)
            continue
        key = (from_state, read_symbol)
        transitions_map.setdefault(key, []).append(t)

    # קונפיגורציה התחלתית
    initial_stack: Tuple[str, ...] = (initial_stack_symbol,)
    initial_config: Configuration = (start_state, 0, initial_stack)

    # Trace התחלתית
    initial_trace_step = {
        "step": 0,
        "state": start_state,
        "consumed": "",
        "remaining_input": input_word,
        "stack": list(initial_stack),
    }

    queue: Deque[Tuple[Configuration, List[Dict[str, Any]]]] = deque()
    queue.append((initial_config, [initial_trace_step]))

    visited: set[Configuration] = {initial_config}

    steps_processed = 0
    configs_processed = 0

    last_trace: List[Dict[str, Any]] = [initial_trace_step]

    while queue and steps_processed < max_steps and configs_processed < max_configs:
        (state, position, stack), trace = queue.popleft()
        steps_processed += 1
        last_trace = trace

        # בדיקת קבלה – כל הקלט נצרך ואנו במצב מקבל
        if position == len(input_word) and state in accept_states:
            logger.info(
                "NPDA accepted word '%s' in %d steps (configs explored: %d).",
                input_word,
                steps_processed,
                configs_processed,
            )
            return True, trace

        configs_processed += 1

        stack_list = list(stack)

        # 1) מעברי אפסילון (read == "")
        for t in transitions_map.get((state, ""), []):
            new_state, new_position, new_stack, new_trace = _apply_transition(
                t, state, position, stack_list, trace, input_word, epsilon=True
            )
            if new_state is None:
                continue
            new_config: Configuration = (new_state, new_position, tuple(new_stack))
            if new_config not in visited:
                visited.add(new_config)
                queue.append((new_config, new_trace))

        # 2) מעברים שקוראים תו מהקלט
        if position < len(input_word):
            symbol = input_word[position]
            for t in transitions_map.get((state, symbol), []):
                new_state, new_position, new_stack, new_trace = _apply_transition(
                    t, state, position, stack_list, trace, input_word, epsilon=False
                )
                if new_state is None:
                    continue
                new_config = (new_state, new_position, tuple(new_stack))
                if new_config not in visited:
                    visited.add(new_config)
                    queue.append((new_config, new_trace))

    # אם לא התקבלה מילה עד פה – דחייה
    logger.info(
        "NPDA rejected word '%s'. steps=%d, configs=%d",
        input_word,
        steps_processed,
        configs_processed,
    )
    return False, last_trace


def _apply_transition(
    t: Dict[str, Any],
    current_state: str,
    position: int,
    stack_list: List[str],
    trace: List[Dict[str, Any]],
    input_word: str,
    epsilon: bool,
) -> Tuple[Any, int, List[str], List[Dict[str, Any]]]:
    """
    מיישם מעבר בודד של NPDA ומחזיר:
      new_state, new_position, new_stack, new_trace
    אם המעבר אינו חוקי (למשל pop לא מתאים למחסנית) – יחזיר (None, ...)
    """
    pop_symbol = t.get("pop", "")
    push_list_raw = t.get("push", [])

    # לא להרוס את המחסנית המקורית
    new_stack = list(stack_list)

    # pop == "" => לא מושכים מהמחסנית
    if pop_symbol not in ("", "ε", None):
        if not new_stack or new_stack[-1] != pop_symbol:
            # המעבר לא אפשרי – אין התאמה בין pop לראש המחסנית
            return None, position, stack_list, trace
        new_stack.pop()

    # טיפול ב-push – מתוך הנחה שזו כבר רשימה מתוקננת, אבל להיות סלחניים
    push_list: List[str] = []
    if isinstance(push_list_raw, list):
        push_list = [str(s) for s in push_list_raw if str(s).strip() != "" and str(s) != "ε"]
    elif isinstance(push_list_raw, str):
        s = push_list_raw.strip()
        if s not in {"", "ε"}:
            push_list = [ch for ch in s]

    # הרשימה מסודרת מלמטה למעלה → דוחפים במהופך
    for sym in reversed(push_list):
        new_stack.append(sym)

    new_state = t.get("to", current_state)
    if epsilon:
        new_position = position
        consumed_symbol = "ε"
        remaining = input_word[position:]
    else:
        new_position = position + 1
        consumed_symbol = input_word[position]
        remaining = input_word[new_position:]

    # בניית Trace חדש
    new_trace = list(trace)
    next_step_index = (trace[-1]["step"] + 1) if trace else 1
    new_trace.append(
        {
            "step": next_step_index,
            "state": new_state,
            "consumed": consumed_symbol,
            "remaining_input": remaining,
            "stack": list(new_stack),
        }
    )

    return new_state, new_position, new_stack, new_trace
