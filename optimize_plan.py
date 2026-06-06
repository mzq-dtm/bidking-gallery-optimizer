from __future__ import annotations

from collections import Counter, defaultdict, deque

from optimize_cabinet import MaxCostFlow, build_optimized_cabinets
from utils import (
    MAX_ITEMS_PER_CABINET,
    cabinet_item_counts,
    calculate_total_value,
    collect_inventory,
    item_can_go_in_cabinet,
    sort_key,
)


class MinCostFlow:
    def __init__(self, node_count: int) -> None:
        self.graph = [[] for _ in range(node_count)]

    def add_edge(self, from_node: int, to_node: int, capacity: int, cost: int, meta: dict | None = None) -> None:
        forward = [to_node, len(self.graph[to_node]), capacity, cost, meta]
        backward = [from_node, len(self.graph[from_node]), 0, -cost, None]
        self.graph[from_node].append(forward)
        self.graph[to_node].append(backward)

    def min_cost_required_flow(self, source: int, sink: int, required_flow: int) -> tuple[int, int]:
        total_flow = 0
        total_cost = 0

        while total_flow < required_flow:
            distance = [float("inf")] * len(self.graph)
            parent: list[tuple[int, int] | None] = [None] * len(self.graph)
            in_queue = [False] * len(self.graph)
            queue = deque([source])
            distance[source] = 0
            in_queue[source] = True

            while queue:
                node = queue.popleft()
                in_queue[node] = False

                for edge_index, edge in enumerate(self.graph[node]):
                    to_node, _, capacity, cost, _ = edge
                    if capacity <= 0:
                        continue

                    new_distance = distance[node] + cost
                    if new_distance < distance[to_node]:
                        distance[to_node] = new_distance
                        parent[to_node] = (node, edge_index)
                        if not in_queue[to_node]:
                            queue.append(to_node)
                            in_queue[to_node] = True

            if parent[sink] is None:
                break

            flow = required_flow - total_flow
            node = sink
            while node != source:
                previous_node, edge_index = parent[node]
                edge = self.graph[previous_node][edge_index]
                flow = min(flow, edge[2])
                node = previous_node

            node = sink
            while node != source:
                previous_node, edge_index = parent[node]
                edge = self.graph[previous_node][edge_index]
                reverse_edge = self.graph[edge[0]][edge[1]]
                edge[2] -= flow
                reverse_edge[2] += flow
                node = previous_node

            total_flow += flow
            total_cost += distance[sink] * flow

        return total_flow, total_cost


def minimize_moves_for_same_value(
    current_cabinets: list[dict],
    flow_cabinets: list[dict],
    items_by_name: dict[str, dict],
) -> list[dict]:
    target_counts = Counter()
    for cabinet in flow_cabinets:
        target_counts.update(cabinet.get("藏品", []))

    original_target_counts = Counter(target_counts)
    flow_value = calculate_total_value(flow_cabinets, items_by_name)
    current_counts = cabinet_item_counts(current_cabinets)
    optimized_cabinets = [
        {
            "名称": cabinet.get("名称", ""),
            "可放类别": list(cabinet.get("可放类别", [])),
            "藏品": [],
        }
        for cabinet in current_cabinets
    ]

    item_names = sorted(target_counts, key=sort_key)
    source = 0
    item_node_start = 1
    cabinet_node_start = item_node_start + len(item_names)
    sink = cabinet_node_start + len(current_cabinets)
    flow = MaxCostFlow(sink + 1)

    for item_index, item_name in enumerate(item_names):
        item_node = item_node_start + item_index
        item_count = target_counts[item_name]
        flow.add_edge(source, item_node, item_count, 0)

        for cabinet_index, cabinet in enumerate(current_cabinets):
            if not item_can_go_in_cabinet(item_name, cabinet, items_by_name):
                continue

            cabinet_node = cabinet_node_start + cabinet_index
            keep_capacity = min(current_counts[cabinet.get("名称", "")][item_name], item_count)
            if keep_capacity:
                flow.add_edge(
                    item_node,
                    cabinet_node,
                    keep_capacity,
                    2,
                    {
                        "kind": "placement",
                        "item_name": item_name,
                        "cabinet_index": cabinet_index,
                    },
                )
            flow.add_edge(
                item_node,
                cabinet_node,
                item_count,
                1,
                {
                    "kind": "placement",
                    "item_name": item_name,
                    "cabinet_index": cabinet_index,
                },
            )

    for cabinet_index, _cabinet in enumerate(current_cabinets):
        flow.add_edge(cabinet_node_start + cabinet_index, sink, MAX_ITEMS_PER_CABINET, 0)

    flow.max_cost_positive_flow(source, sink)

    for edges in flow.graph:
        for edge in edges:
            meta = edge[4]
            if not meta or meta.get("kind") != "placement":
                continue

            reverse_edge = flow.graph[edge[0]][edge[1]]
            placed_count = reverse_edge[2]
            if placed_count > 0:
                optimized_cabinets[meta["cabinet_index"]]["藏品"].extend([meta["item_name"]] * placed_count)

    improve_assignment_by_swaps(current_cabinets, optimized_cabinets, items_by_name)

    inventory = collect_inventory(current_cabinets, [])
    used_items = Counter()
    for cabinet in optimized_cabinets:
        used_items.update(cabinet.get("藏品", []))

    for cabinet_index, current_cabinet in enumerate(current_cabinets):
        optimized_items = optimized_cabinets[cabinet_index]["藏品"]
        for item_name in current_cabinet.get("藏品", []):
            if len(optimized_items) >= MAX_ITEMS_PER_CABINET:
                break
            if item_name in items_by_name:
                continue
            if used_items[item_name] >= inventory[item_name]:
                continue

            optimized_items.append(item_name)
            used_items[item_name] += 1

    improve_assignment_by_swaps(current_cabinets, optimized_cabinets, items_by_name)

    reassigned_counts = Counter()
    for cabinet in optimized_cabinets:
        reassigned_counts.update(cabinet.get("藏品", []))

    if reassigned_counts < original_target_counts:
        return flow_cabinets
    if calculate_total_value(optimized_cabinets, items_by_name) != flow_value:
        return flow_cabinets

    return optimized_cabinets


def minimize_steps_for_same_value(
    current_cabinets: list[dict],
    backpack_items: list[str],
    flow_cabinets: list[dict],
    items_by_name: dict[str, dict],
) -> list[dict]:
    target_counts = Counter()
    for cabinet in flow_cabinets:
        target_counts.update(cabinet.get("藏品", []))

    required_flow = sum(target_counts.values())
    if required_flow == 0:
        return [
            {
                "名称": cabinet.get("名称", ""),
                "可放类别": list(cabinet.get("可放类别", [])),
                "藏品": [],
            }
            for cabinet in current_cabinets
        ]

    flow_value = calculate_total_value(flow_cabinets, items_by_name)
    optimized_cabinets = [
        {
            "名称": cabinet.get("名称", ""),
            "可放类别": list(cabinet.get("可放类别", [])),
            "藏品": [],
        }
        for cabinet in current_cabinets
    ]

    item_names = sorted(target_counts, key=sort_key)
    backpack_counts = Counter(backpack_items)
    source_records = []
    for item_name in item_names:
        item_sources = []
        for cabinet_index, cabinet in enumerate(current_cabinets):
            count = Counter(cabinet.get("藏品", []))[item_name]
            if count:
                item_sources.append(
                    {
                        "item_name": item_name,
                        "origin": "cabinet",
                        "cabinet_index": cabinet_index,
                        "count": count,
                    }
                )

        backpack_count = backpack_counts[item_name]
        if backpack_count:
            item_sources.append(
                {
                    "item_name": item_name,
                    "origin": "backpack",
                    "cabinet_index": None,
                    "count": backpack_count,
                }
            )

        source_records.extend(item_sources)

    source = 0
    item_node_start = 1
    source_node_start = item_node_start + len(item_names)
    cabinet_node_start = source_node_start + len(source_records)
    sink = cabinet_node_start + len(current_cabinets)
    flow = MinCostFlow(sink + 1)

    item_nodes = {item_name: item_node_start + index for index, item_name in enumerate(item_names)}

    source_record_node_indexes = []
    for source_index, record in enumerate(source_records):
        source_record_node_indexes.append(source_node_start + source_index)

    for item_name in item_names:
        flow.add_edge(source, item_nodes[item_name], target_counts[item_name], 0)

    for record, source_node in zip(source_records, source_record_node_indexes):
        item_name = record["item_name"]
        flow.add_edge(item_nodes[item_name], source_node, record["count"], 0)

        for cabinet_index, cabinet in enumerate(current_cabinets):
            if not item_can_go_in_cabinet(item_name, cabinet, items_by_name):
                continue

            if record["origin"] == "cabinet" and record["cabinet_index"] == cabinet_index:
                move_cost = 0
            else:
                move_cost = 1

            flow.add_edge(
                source_node,
                cabinet_node_start + cabinet_index,
                record["count"],
                move_cost,
                {
                    "kind": "step_placement",
                    "item_name": item_name,
                    "cabinet_index": cabinet_index,
                },
            )

    for cabinet_index, _cabinet in enumerate(current_cabinets):
        flow.add_edge(cabinet_node_start + cabinet_index, sink, MAX_ITEMS_PER_CABINET, 0)

    actual_flow, _total_cost = flow.min_cost_required_flow(source, sink, required_flow)
    if actual_flow != required_flow:
        return minimize_moves_for_same_value(current_cabinets, flow_cabinets, items_by_name)

    for edges in flow.graph:
        for edge in edges:
            meta = edge[4]
            if not meta or meta.get("kind") != "step_placement":
                continue

            reverse_edge = flow.graph[edge[0]][edge[1]]
            placed_count = reverse_edge[2]
            if placed_count > 0:
                optimized_cabinets[meta["cabinet_index"]]["藏品"].extend([meta["item_name"]] * placed_count)

    if calculate_total_value(optimized_cabinets, items_by_name) != flow_value:
        return minimize_moves_for_same_value(current_cabinets, flow_cabinets, items_by_name)

    return optimized_cabinets


def assignment_keep_score(current_cabinets: list[dict], optimized_cabinets: list[dict]) -> int:
    score = 0
    for current_cabinet, optimized_cabinet in zip(current_cabinets, optimized_cabinets):
        current_counts = Counter(current_cabinet.get("藏品", []))
        optimized_counts = Counter(optimized_cabinet.get("藏品", []))
        for item_name, count in optimized_counts.items():
            score += min(count, current_counts[item_name])
    return score


def improve_assignment_by_swaps(
    current_cabinets: list[dict],
    optimized_cabinets: list[dict],
    items_by_name: dict[str, dict],
) -> None:
    while True:
        current_score = assignment_keep_score(current_cabinets, optimized_cabinets)
        best_swap = None
        best_score = current_score

        for first_index, first_cabinet in enumerate(optimized_cabinets):
            for second_index in range(first_index + 1, len(optimized_cabinets)):
                second_cabinet = optimized_cabinets[second_index]
                for first_item_index, first_item in enumerate(first_cabinet.get("藏品", [])):
                    for second_item_index, second_item in enumerate(second_cabinet.get("藏品", [])):
                        if first_item == second_item:
                            continue
                        if not item_can_go_in_cabinet(first_item, second_cabinet, items_by_name):
                            continue
                        if not item_can_go_in_cabinet(second_item, first_cabinet, items_by_name):
                            continue

                        first_cabinet["藏品"][first_item_index] = second_item
                        second_cabinet["藏品"][second_item_index] = first_item
                        new_score = assignment_keep_score(current_cabinets, optimized_cabinets)
                        first_cabinet["藏品"][first_item_index] = first_item
                        second_cabinet["藏品"][second_item_index] = second_item

                        if new_score > best_score:
                            best_score = new_score
                            best_swap = (first_index, first_item_index, second_index, second_item_index)

        if best_swap is None:
            return

        first_index, first_item_index, second_index, second_item_index = best_swap
        first_cabinet = optimized_cabinets[first_index]
        second_cabinet = optimized_cabinets[second_index]
        first_cabinet["藏品"][first_item_index], second_cabinet["藏品"][second_item_index] = (
            second_cabinet["藏品"][second_item_index],
            first_cabinet["藏品"][first_item_index],
        )


def build_rearrangement_moves(
    current_cabinets: list[dict],
    optimized_cabinets: list[dict],
    backpack_items: list[str],
) -> list[str]:
    current_counts = cabinet_item_counts(current_cabinets)
    optimized_counts = cabinet_item_counts(optimized_cabinets)
    item_names = set(backpack_items)

    for counts in current_counts.values():
        item_names.update(counts)
    for counts in optimized_counts.values():
        item_names.update(counts)

    moves = []
    removals_by_cabinet = defaultdict(list)
    insertions_by_cabinet = defaultdict(list)
    cabinet_names = [cabinet.get("名称", "") for cabinet in current_cabinets]

    for item_name in sorted(item_names, key=sort_key):
        for cabinet_name in cabinet_names:
            current_count = current_counts.get(cabinet_name, Counter())[item_name]
            optimized_count = optimized_counts.get(cabinet_name, Counter())[item_name]
            if current_count > optimized_count:
                removals_by_cabinet[cabinet_name].extend([item_name] * (current_count - optimized_count))
            elif optimized_count > current_count:
                insertions_by_cabinet[cabinet_name].extend([item_name] * (optimized_count - current_count))

    if removals_by_cabinet:
        moves.append("先腾出展示柜位置：")
        for cabinet_name in cabinet_names:
            for item_name in sorted(removals_by_cabinet[cabinet_name], key=sort_key):
                moves.append(f"将「{item_name}」从「{cabinet_name}」移入背包")
    if insertions_by_cabinet:
        moves.append("再放入推荐展品：")
        for cabinet_name in cabinet_names:
            for item_name in sorted(insertions_by_cabinet[cabinet_name], key=sort_key):
                moves.append(f"将「{item_name}」从背包放入「{cabinet_name}」")
    return moves


def build_optimized_backpack(
    cabinets: list[dict],
    backpack_items: list[str],
    optimized_cabinets: list[dict],
) -> list[str]:
    remaining = collect_inventory(cabinets, backpack_items)
    for cabinet in optimized_cabinets:
        remaining.subtract(cabinet.get("藏品", []))

    optimized_backpack = []
    for item_name in backpack_items:
        if remaining[item_name] > 0:
            optimized_backpack.append(item_name)
            remaining[item_name] -= 1

    for cabinet in cabinets:
        for item_name in cabinet.get("藏品", []):
            if remaining[item_name] > 0:
                optimized_backpack.append(item_name)
                remaining[item_name] -= 1

    for item_name in sorted(remaining, key=sort_key):
        optimized_backpack.extend([item_name] * max(0, remaining[item_name]))

    return optimized_backpack


def total_cabinet_item_counts(cabinets: list[dict]) -> Counter:
    counts = Counter()
    for cabinet in cabinets:
        counts.update(cabinet.get("藏品", []))
    return counts


def format_item_counts(items: Counter | list[str]) -> str:
    counts = Counter(items)
    if not counts:
        return "无"

    parts = []
    for item_name in sorted(counts, key=sort_key):
        count = counts[item_name]
        if count == 1:
            parts.append(item_name)
        else:
            parts.append(f"{item_name} x{count}")
    return "、".join(parts)


def find_best_replacement_plan(
    cabinets: list[dict],
    backpack_items: list[str],
    items_by_name: dict[str, dict],
) -> dict:
    base_value = calculate_total_value(cabinets, items_by_name)
    flow_cabinets, _flow_value = build_optimized_cabinets(cabinets, backpack_items, items_by_name)
    optimized_cabinets = minimize_steps_for_same_value(cabinets, backpack_items, flow_cabinets, items_by_name)

    for cabinet in optimized_cabinets:
        cabinet["藏品"].sort(key=sort_key)

    new_value = calculate_total_value(optimized_cabinets, items_by_name)
    if new_value <= base_value:
        return {"base_value": base_value, "new_value": base_value, "increase": 0, "moves": []}

    moves = build_rearrangement_moves(cabinets, optimized_cabinets, backpack_items)
    optimized_backpack = build_optimized_backpack(cabinets, backpack_items, optimized_cabinets)
    current_item_counts = total_cabinet_item_counts(cabinets)
    optimized_item_counts = total_cabinet_item_counts(optimized_cabinets)
    return {
        "base_value": base_value,
        "new_value": new_value,
        "increase": new_value - base_value,
        "moves": moves,
        "optimized_cabinets": optimized_cabinets,
        "optimized_backpack": optimized_backpack,
        "removed_items": current_item_counts - optimized_item_counts,
        "added_items": optimized_item_counts - current_item_counts,
        "useless_backpack_items": Counter(backpack_items) - (optimized_item_counts - current_item_counts),
    }


def format_replacement_plan(plan: dict) -> str:
    lines = [
        f"当前总价值：{plan['base_value']:,}",
        f"推荐后总价值：{plan['new_value']:,}",
        f"增加价值：{plan['increase']:,}",
        f"移除的物品：{format_item_counts(plan.get('removed_items', Counter()))}",
        f"加入展柜的物品：{format_item_counts(plan.get('added_items', Counter()))}",
        f"背包中无用的物品：{format_item_counts(plan.get('useless_backpack_items', []))}",
        "",
        "调整方案：",
    ]
    lines.extend(plan["moves"])
    return "\n".join(lines)
