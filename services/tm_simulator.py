import logging
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class Transition:
    to: str
    write: str
    move: str  # "L" | "R" | "S"


class TMSpecError(ValueError):
    pass


def _normalize_symbol(s: Optional[str]) -> str:
    if s is None or s == "":
        return ""
    return s


def validate_tm_spec(spec: Dict[str, Any]) -> None:
    """
    Validates a TM spec dict. Raises TMSpecError on invalid spec.
    """
    try:
        if spec.get("type") != "TM":
            raise TMSpecError("spec.type must be 'TM'")

        states = set(spec.get("states") or [])
        if not states:
            raise TMSpecError("spec.states must be non-empty")

        start = spec.get("start_state")
        if start not in states:
            raise TMSpecError("start_state must be in states")

        accept_states = set(spec.get("accept_states") or [])
        reject_states = set(spec.get("reject_states") or [])

        blank = spec.get("blank", "_")
        if not isinstance(blank, str) or len(blank) != 1:
            raise TMSpecError("blank must be a single character string (e.g. '_' )")

        tape_alphabet = set(spec.get("tape_alphabet") or [])
        if blank not in tape_alphabet:
            raise TMSpecError("blank must appear in tape_alphabet")

        input_alphabet = set(spec.get("input_alphabet") or [])
        if not input_alphabet.issubset(tape_alphabet):
            raise TMSpecError("input_alphabet must be subset of tape_alphabet")

        transitions = spec.get("transitions") or []
        if not isinstance(transitions, list):
            raise TMSpecError("transitions must be a list")

        seen: set[Tuple[str, str]] = set()
        for t in transitions:
            frm = t.get("from")
            read = _normalize_symbol(t.get("read"))
            to = t.get("to")
            write = _normalize_symbol(t.get("write"))
            move = t.get("move")

            if frm not in states:
                raise TMSpecError(f"transition.from '{frm}' not in states")
            if to not in states:
                raise TMSpecError(f"transition.to '{to}' not in states")

            if not isinstance(read, str) or len(read) != 1:
                raise TMSpecError(f"transition.read must be 1 char, got '{read}'")
            if not isinstance(write, str) or len(write) != 1:
                raise TMSpecError(f"transition.write must be 1 char, got '{write}'")

            if read not in tape_alphabet:
                raise TMSpecError(f"transition.read '{read}' not in tape_alphabet")
            if write not in tape_alphabet:
                raise TMSpecError(f"transition.write '{write}' not in tape_alphabet")

            if move not in ("L", "R", "S"):
                raise TMSpecError("transition.move must be one of: L, R, S")

            key = (frm, read)
            if key in seen:
                raise TMSpecError(f"non-deterministic transition found for ({frm}, {read})")
            seen.add(key)

        # Optional: ensure accept/reject sets subset
        if not accept_states.issubset(states):
            raise TMSpecError("accept_states must be subset of states")
        if not reject_states.issubset(states):
            raise TMSpecError("reject_states must be subset of states")

    except TMSpecError:
        raise
    except Exception as e:
        raise TMSpecError(f"Invalid TM spec: {e}") from e


def build_transition_map(spec: Dict[str, Any]) -> Dict[Tuple[str, str], Transition]:
    transition_map: Dict[Tuple[str, str], Transition] = {}
    for t in (spec.get("transitions") or []):
        frm = t["from"]
        read = t["read"]
        transition_map[(frm, read)] = Transition(
            to=t["to"],
            write=t["write"],
            move=t["move"]
        )
    return transition_map


def init_config(input_str: str, blank: str, start_state: str) -> Dict[str, Any]:
    """
    Returns a config dict:
    {
      "state": ...,
      "head": 0,
      "step": 0,
      "tape": {0:"a", 1:"b", ...}  # sparse map
    }
    """
    tape: Dict[int, str] = {}
    for i, ch in enumerate(input_str):
        tape[i] = ch
    return {"state": start_state, "head": 0, "step": 0, "tape": tape}


def read_tape(tape: Dict[int, str], head: int, blank: str) -> str:
    return tape.get(head, blank)


def write_tape(tape: Dict[int, str], head: int, symbol: str, blank: str) -> None:
    if symbol == blank:
        # keep sparse: remove blank cells
        tape.pop(head, None)
    else:
        tape[head] = symbol


def snapshot_window(tape: Dict[int, str], head: int, blank: str, radius: int = 12) -> List[Dict[str, Any]]:
    """
    Returns a list of cells around the head:
    [{"index": i, "symbol": "a", "is_head": True}, ...]
    """
    cells = []
    for i in range(head - radius, head + radius + 1):
        cells.append({
            "index": i,
            "symbol": tape.get(i, blank),
            "is_head": i == head
        })
    return cells


def step_tm(spec: Dict[str, Any], config: Dict[str, Any], window_radius: int = 12) -> Dict[str, Any]:
    """
    One deterministic TM step. Stateless: client sends spec+config, server returns updated config and step info.
    """
    validate_tm_spec(spec)
    tm = build_transition_map(spec)

    state = config.get("state")
    head = int(config.get("head", 0))
    step_no = int(config.get("step", 0))
    tape_raw = config.get("tape") or {}

    # JSON keys may arrive as strings
    tape: Dict[int, str] = {}
    for k, v in tape_raw.items():
        tape[int(k)] = v

    blank = spec.get("blank", "_")
    accept_states = set(spec.get("accept_states") or [])
    reject_states = set(spec.get("reject_states") or [])

    # halting checks (before stepping)
    if state in accept_states:
        return {
            "halted": True,
            "accepted": True,
            "reason": "accept_state",
            "config": {"state": state, "head": head, "step": step_no, "tape": tape},
            "window": snapshot_window(tape, head, blank, window_radius),
        }
    if state in reject_states:
        return {
            "halted": True,
            "accepted": False,
            "reason": "reject_state",
            "config": {"state": state, "head": head, "step": step_no, "tape": tape},
            "window": snapshot_window(tape, head, blank, window_radius),
        }

    read = read_tape(tape, head, blank)
    tr = tm.get((state, read))
    if tr is None:
        return {
            "halted": True,
            "accepted": False,
            "reason": "stuck_no_transition",
            "config": {"state": state, "head": head, "step": step_no, "tape": tape},
            "window": snapshot_window(tape, head, blank, window_radius),
        }

    # apply transition
    write_tape(tape, head, tr.write, blank)
    new_head = head
    if tr.move == "L":
        new_head -= 1
    elif tr.move == "R":
        new_head += 1

    new_state = tr.to
    new_step = step_no + 1

    # halting checks (after stepping) optional; UI can read state
    halted = (new_state in accept_states) or (new_state in reject_states)

    return {
        "halted": halted,
        "accepted": True if new_state in accept_states else (False if new_state in reject_states else None),
        "reason": "transition",
        "transition": {
            "from": state,
            "read": read,
            "to": new_state,
            "write": tr.write,
            "move": tr.move
        },
        "config": {"state": new_state, "head": new_head, "step": new_step, "tape": tape},
        "window": snapshot_window(tape, new_head, blank, window_radius),
    }


def run_tm(spec: Dict[str, Any], input_str: str, max_steps: int = 500, window_radius: int = 12) -> Dict[str, Any]:
    """
    Runs until halt or max_steps, returns trace.
    """
    validate_tm_spec(spec)
    blank = spec.get("blank", "_")
    start = spec["start_state"]

    config = init_config(input_str=input_str, blank=blank, start_state=start)
    trace = []

    for _ in range(max_steps):
        res = step_tm(spec, config, window_radius=window_radius)
        trace.append(res)
        config = res["config"]
        if res.get("halted"):
            return {
                "halted": True,
                "accepted": res.get("accepted"),
                "reason": res.get("reason"),
                "final_config": config,
                "trace": trace
            }

    return {
        "halted": False,
        "accepted": None,
        "reason": "max_steps_reached",
        "final_config": config,
        "trace": trace
    }
