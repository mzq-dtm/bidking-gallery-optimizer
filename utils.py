from __future__ import annotations
import sys
import json
import locale
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
CABINETS_PATH = BASE_DIR / "display_cabinets.toml"
ITEMS_PATH = BASE_DIR / "item_category.json"
BACKPACK_PATH = BASE_DIR / "backpack_items.json"
MAX_ITEMS_PER_CABINET = 15
DISCOUNT_RATES = [1.0, 0.5, 0.25, 0.13, 0.07, 0.04]

try:
    locale.setlocale(locale.LC_COLLATE, "zh_CN.UTF-8")
except locale.Error:
    pass


def sort_key(value: str) -> str:
    return locale.strxfrm(value)


def sort_cabinet_items(cabinets: list[dict]) -> list[dict]:
    for cabinet in cabinets:
        cabinet["藏品"] = sorted((str(item) for item in cabinet.get("藏品", [])), key=sort_key)
    return cabinets


def load_cabinets(path: Path = CABINETS_PATH) -> list[dict]:
    with path.open("rb") as file:
        data = tomllib.load(file)
    return sort_cabinet_items(data.get("展示柜", []))


def load_items(path: Path = ITEMS_PATH) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_backpack_items(path: Path = BACKPACK_PATH) -> list[str]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{path.name} 必须是字符串数组")

    return [str(item) for item in data]


def write_backpack_items(items: list[str], path: Path = BACKPACK_PATH) -> None:
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def toml_array(values: list[str]) -> str:
    return "[" + ", ".join(toml_string(value) for value in values) + "]"


def write_cabinets(cabinets: list[dict], path: Path = CABINETS_PATH) -> None:
    blocks = []
    for cabinet in cabinets:
        name = cabinet.get("名称", "")
        allowed_categories = list(cabinet.get("可放类别", []))
        collection_items = sorted((str(item) for item in cabinet.get("藏品", [])), key=sort_key)
        blocks.append(
            "\n".join(
                [
                    '[["展示柜"]]',
                    f'"名称" = {toml_string(name)}',
                    f'"可放类别" = {toml_array(allowed_categories)}',
                    f'"藏品" = {toml_array(collection_items)}',
                ]
            )
        )

    content = "\n\n".join(blocks) + "\n"
    tomllib.loads(content)
    path.write_text(content, encoding="utf-8")

    with path.open("rb") as file:
        tomllib.load(file)


def item_index(items: list[dict]) -> dict[str, dict]:
    return {item["藏品名"]: item for item in items}


def allowed_item_names(cabinet: dict, items: list[dict]) -> list[str]:
    allowed_categories = set(cabinet.get("可放类别", []))
    names = []
    for item in items:
        item_categories = set(item.get("藏品类别", []))
        if allowed_categories & item_categories:
            names.append(item["藏品名"])
    return sorted(names, key=sort_key)


def discount_rate_for_occurrence(occurrence: int) -> float:
    if occurrence <= 0:
        return 0.0
    if occurrence <= len(DISCOUNT_RATES):
        return DISCOUNT_RATES[occurrence - 1]
    return DISCOUNT_RATES[-1]


def calculate_total_value(cabinets: list[dict], items_by_name: dict[str, dict]) -> int:
    seen_counts: dict[str, int] = defaultdict(int)
    total = 0

    for cabinet in cabinets:
        for name in cabinet.get("藏品", []):
            seen_counts[name] += 1
            occurrence = seen_counts[name]

            item = items_by_name.get(name)
            if item is None:
                continue

            total += round(int(item.get("价值", 0)) * discount_rate_for_occurrence(occurrence))

    return total


def item_can_go_in_cabinet(item_name: str, cabinet: dict, items_by_name: dict[str, dict]) -> bool:
    item = items_by_name.get(item_name)
    if item is None:
        return False

    allowed_categories = set(cabinet.get("可放类别", []))
    item_categories = set(item.get("藏品类别", []))
    return bool(allowed_categories & item_categories)


def collect_inventory(cabinets: list[dict], backpack_items: list[str]) -> Counter:
    inventory = Counter(backpack_items)
    for cabinet in cabinets:
        inventory.update(cabinet.get("藏品", []))
    return inventory


def cabinet_item_counts(cabinets: list[dict]) -> dict[str, Counter]:
    return {cabinet.get("名称", ""): Counter(cabinet.get("藏品", [])) for cabinet in cabinets}
