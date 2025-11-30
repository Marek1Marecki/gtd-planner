# apps/projects/domain/services.py
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class CPMNode:
    task_id: int
    duration: int
    dependencies: List[int]  # ID zadań, od których to zadanie zależy (Predecessors)

    # Obliczane wartości
    es: int = 0
    ef: int = 0
    ls: int = 0
    lf: int = 0
    float_val: int = 0
    is_critical: bool = False


class CPMService:
    def calculate_critical_path(self, tasks: List[CPMNode]) -> Dict[int, CPMNode]:
        """
        Oblicza ścieżkę krytyczną dla listy węzłów.
        Zwraca słownik {task_id: node} z wypełnionymi wartościami.
        """
        node_map = {t.task_id: t for t in tasks}

        # 1. Forward Pass (ES, EF)
        # Sortujemy topologicznie (uproszczone: pętla wielokrotna lub rekurencja z memoizacją)
        # Dla uproszczenia załóżmy, że graf jest acykliczny.

        processed = set()

        def calc_forward(node_id):
            if node_id in processed: return
            node = node_map[node_id]

            max_predecessor_ef = 0
            for dep_id in node.dependencies:
                calc_forward(dep_id)  # Rekurencja
                if node_map[dep_id].ef > max_predecessor_ef:
                    max_predecessor_ef = node_map[dep_id].ef

            node.es = max_predecessor_ef
            node.ef = node.es + node.duration
            processed.add(node_id)

        for tid in node_map:
            calc_forward(tid)

        # 2. Backward Pass (LS, LF)
        project_duration = max((n.ef for n in tasks), default=0)
        processed = set()

        # Znajdź zadania końcowe (te, od których nic nie zależy) - albo po prostu iteruj wstecz
        # Tutaj musimy znać następników (Successors). Zbudujmy mapę odwrotną.
        successors = {tid: [] for tid in node_map}
        for node in tasks:
            for dep_id in node.dependencies:
                successors[dep_id].append(node.task_id)

        def calc_backward(node_id):
            if node_id in processed: return
            node = node_map[node_id]

            min_successor_ls = project_duration

            my_successors = successors[node_id]
            if not my_successors:
                # To jest zadanie końcowe
                node.lf = project_duration
            else:
                for succ_id in my_successors:
                    calc_backward(succ_id)
                    if node_map[succ_id].ls < min_successor_ls:
                        min_successor_ls = node_map[succ_id].ls
                node.lf = min_successor_ls

            node.ls = node.lf - node.duration
            node.float_val = node.ls - node.es
            node.is_critical = (node.float_val == 0)
            processed.add(node_id)

        for tid in node_map:
            calc_backward(tid)

        return node_map