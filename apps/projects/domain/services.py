# apps/projects/domain/services.py
from typing import List, Dict
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

        # Jeśli graf jest pusty, zwróć pusty słownik
        if not node_map:
            return {}

        # ---------------------------
        # 1. Forward Pass (ES, EF)
        # ---------------------------
        processed = set()

        def calc_forward(node_id):
            if node_id in processed: return

            # Zabezpieczenie: jeśli węzeł nie istnieje (np. został usunięty/zakończony), ignoruj
            node = node_map.get(node_id)
            if not node: return

            max_predecessor_ef = 0
            for dep_id in node.dependencies:
                calc_forward(dep_id)

                # Zabezpieczenie: bierzemy pod uwagę tylko istniejące zależności
                if dep_id in node_map:
                    if node_map[dep_id].ef > max_predecessor_ef:
                        max_predecessor_ef = node_map[dep_id].ef

            node.es = max_predecessor_ef
            node.ef = node.es + node.duration
            processed.add(node_id)

        for tid in node_map:
            calc_forward(tid)

        # ---------------------------
        # 2. Backward Pass (LS, LF)
        # ---------------------------
        # Czas trwania projektu to maksymalny EF
        project_duration = max((n.ef for n in node_map.values()), default=0)
        processed = set()

        # Budowa mapy odwrotnej (Successors) dla łatwiejszego przeszukiwania
        successors = {tid: [] for tid in node_map}
        for node in node_map.values():
            for dep_id in node.dependencies:
                if dep_id in successors:
                    successors[dep_id].append(node.task_id)

        def calc_backward(node_id):
            if node_id in processed: return

            node = node_map.get(node_id)
            if not node: return

            min_successor_ls = project_duration

            my_successors = successors.get(node_id, [])
            if not my_successors:
                # Zadanie końcowe (nie ma następców w grafie)
                node.lf = project_duration
            else:
                for succ_id in my_successors:
                    calc_backward(succ_id)
                    if succ_id in node_map:
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