from __future__ import annotations

from collections import deque

from utils import (
    MAX_ITEMS_PER_CABINET,
    calculate_total_value,
    collect_inventory,
    discount_rate_for_occurrence,
    item_can_go_in_cabinet,
)


class MaxCostFlow:
    def __init__(self, node_count: int) -> None:
        self.graph = [[] for _ in range(node_count)]

    def add_edge(self, from_node: int, to_node: int, capacity: int, cost: int, meta: dict | None = None) -> None:
        forward = [to_node, len(self.graph[to_node]), capacity, cost, meta]
        backward = [from_node, len(self.graph[from_node]), 0, -cost, None]
        self.graph[from_node].append(forward)
        self.graph[to_node].append(backward)

    def max_cost_positive_flow(self, source: int, sink: int) -> int:
        total_cost = 0

        while True:
            distance = [float("-inf")] * len(self.graph)
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
                    if new_distance > distance[to_node]:
                        distance[to_node] = new_distance
                        parent[to_node] = (node, edge_index)
                        if not in_queue[to_node]:
                            queue.append(to_node)
                            in_queue[to_node] = True

            if parent[sink] is None or distance[sink] <= 0:
                break

            flow = 1
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

            total_cost += distance[sink] * flow

        return total_cost


def build_optimized_cabinets(
    cabinets: list[dict],
    backpack_items: list[str],
    items_by_name: dict[str, dict],
) -> tuple[list[dict], int]:
    inventory = collect_inventory(cabinets, backpack_items)
    source = 0
    item_nodes = []

    for item_name, count in inventory.items():
        item = items_by_name.get(item_name)
        if item is None:
            continue

        base_value = int(item.get("价值", 0))
        for occurrence in range(count):
            marginal_value = round(base_value * discount_rate_for_occurrence(occurrence + 1))
            if marginal_value <= 0:
                continue
            item_nodes.append({"item_name": item_name, "value": marginal_value})

    cabinet_node_start = 1 + len(item_nodes)
    sink = cabinet_node_start + len(cabinets)
    flow = MaxCostFlow(sink + 1)

    for item_index, item_node in enumerate(item_nodes):
        node = 1 + item_index
        flow.add_edge(source, node, 1, item_node["value"])

        for cabinet_index, cabinet in enumerate(cabinets):
            if item_can_go_in_cabinet(item_node["item_name"], cabinet, items_by_name):
                flow.add_edge(
                    node,
                    cabinet_node_start + cabinet_index,
                    1,
                    0,
                    {
                        "kind": "assignment",
                        "item_name": item_node["item_name"],
                        "cabinet_index": cabinet_index,
                    },
                )

    for cabinet_index, _cabinet in enumerate(cabinets):
        flow.add_edge(cabinet_node_start + cabinet_index, sink, MAX_ITEMS_PER_CABINET, 0)

    flow.max_cost_positive_flow(source, sink)
    optimized_cabinets = [
        {
            "名称": cabinet.get("名称", ""),
            "可放类别": list(cabinet.get("可放类别", [])),
            "藏品": [],
        }
        for cabinet in cabinets
    ]

    for edges in flow.graph:
        for edge in edges:
            meta = edge[4]
            if not meta or meta.get("kind") != "assignment":
                continue

            reverse_edge = flow.graph[edge[0]][edge[1]]
            if reverse_edge[2] > 0:
                optimized_cabinets[meta["cabinet_index"]]["藏品"].append(meta["item_name"])

    return optimized_cabinets, calculate_total_value(optimized_cabinets, items_by_name)
