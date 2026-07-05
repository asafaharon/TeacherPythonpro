# services/npda_tree_engine.py

from collections import deque
from typing import Any, Dict, List, Tuple, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Types
# ------------------------------------------------------------

Stack = Tuple[str, ...]


class TreeNode:
    def __init__(
        self,
        state: str,
        position: int,
        stack: Stack,
        parent_id: Optional[str],
        consumed: str,
    ):
        self.id = str(uuid.uuid4())
        self.state = state
        self.position = position
        self.stack = stack
        self.parent_id = parent_id
        self.consumed = consumed
        self.children: List[str] = []
        self.is_accepting: bool = False
        self.is_dead: bool = False


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def run_npda_with_tree(
    pda: Dict[str, Any],
    input_word: str,
    max_steps: int = 2000,
    max_nodes: int = 4000,
) -> Dict[str, Any]:
    """
    מריץ NPDA ומחזיר עץ חישוב מלא (אי־דטרמיניזם).
    """

    if pda.get("type") != "PDA":
        return {
            "accepted": False,
            "error": "Not a PDA",
            "tree": {},
        }

    states = pda["states"]
    start_state = pda["start_state"]
    accept_states = set(pda["accept_states"])
    initial_stack_symbol = pda["initial_stack_symbol"]
    transitions = pda["transitions"]

    # Map: (state, read_symbol) -> transitions
    transition_map: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for t in transitions:
        key = (t["from"], t["read"])
        transition_map.setdefault(key, []).append(t)

    # Root node
    root = TreeNode(
        state=start_state,
        position=0,
        stack=(initial_stack_symbol,),
        parent_id=None,
        consumed="START",
    )

    nodes: Dict[str, TreeNode] = {root.id: root}

    queue = deque([root])
    visited = set()

    accepting_node_id: Optional[str] = None
    steps = 0

    while queue and steps < max_steps and len(nodes) < max_nodes:
        current = queue.popleft()
        steps += 1

        config_key = (current.state, current.position, current.stack)
        if config_key in visited:
            continue
        visited.add(config_key)

        # ✅ קבלה
        if (
            current.position == len(input_word)
            and current.state in accept_states
        ):
            current.is_accepting = True
            accepting_node_id = current.id
            break

        progressed = False

        # ------------------------------------------------
        # ε-transitions
        # ------------------------------------------------
        for t in transition_map.get((current.state, ""), []):
            child = _apply_transition(
                current,
                t,
                input_word,
                epsilon=True,
            )
            if child:
                nodes[child.id] = child
                current.children.append(child.id)
                queue.append(child)
                progressed = True

        # ------------------------------------------------
        # symbol transitions
        # ------------------------------------------------
        if current.position < len(input_word):
            symbol = input_word[current.position]
            for t in transition_map.get((current.state, symbol), []):
                child = _apply_transition(
                    current,
                    t,
                    input_word,
                    epsilon=False,
                )
                if child:
                    nodes[child.id] = child
                    current.children.append(child.id)
                    queue.append(child)
                    progressed = True

        if not progressed:
            current.is_dead = True

    # ------------------------------------------------------------
    # Build result
    # ------------------------------------------------------------

    accepting_path = []
    if accepting_node_id:
        accepting_path = _extract_path(nodes, accepting_node_id)

    return {
        "accepted": accepting_node_id is not None,
        "accepting_node_id": accepting_node_id,
        "accepting_path": accepting_path,
        "tree": _serialize_tree(nodes),
        "stats": {
            "nodes": len(nodes),
            "steps": steps,
        },
    }


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _apply_transition(
    node: TreeNode,
    t: Dict[str, Any],
    input_word: str,
    epsilon: bool,
) -> Optional[TreeNode]:

    stack = list(node.stack)

    pop_symbol = t["pop"]
    if pop_symbol:
        if not stack or stack[-1] != pop_symbol:
            return None
        stack.pop()

    push_list = t.get("push", [])
    for sym in reversed(push_list):
        stack.append(sym)

    if epsilon:
        new_position = node.position
        consumed = "ε"
    else:
        new_position = node.position + 1
        consumed = input_word[node.position]

    return TreeNode(
        state=t["to"],
        position=new_position,
        stack=tuple(stack),
        parent_id=node.id,
        consumed=consumed,
    )


def _extract_path(nodes: Dict[str, TreeNode], node_id: str) -> List[str]:
    path = []
    while node_id:
        path.append(node_id)
        node_id = nodes[node_id].parent_id
    return list(reversed(path))


def _serialize_tree(nodes: Dict[str, TreeNode]) -> Dict[str, Any]:
    return {
        node_id: {
            "id": node.id,
            "state": node.state,
            "position": node.position,
            "stack": list(node.stack),
            "parent": node.parent_id,
            "children": node.children,
            "consumed": node.consumed,
            "is_accepting": node.is_accepting,
            "is_dead": node.is_dead,
        }
        for node_id, node in nodes.items()
    }
