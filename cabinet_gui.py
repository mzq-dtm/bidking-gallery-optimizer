from __future__ import annotations

from collections import Counter

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ModuleNotFoundError:  # The non-GUI modules should remain importable without Tk installed.
    tk = None
    messagebox = None
    ttk = None

from optimize_plan import find_best_replacement_plan, format_replacement_plan
from utils import (
    MAX_ITEMS_PER_CABINET,
    allowed_item_names,
    calculate_total_value,
    discount_rate_for_occurrence,
    item_index,
    load_backpack_items,
    load_cabinets,
    load_items,
    sort_key,
    write_backpack_items,
    write_cabinets,
)


_TkBase = tk.Tk if tk is not None else object


class CabinetApp(_TkBase):
    def __init__(self) -> None:
        if tk is None:
            raise RuntimeError("当前 Python 环境缺少 tkinter，请先安装 python3-tk 后再运行 GUI。")

        super().__init__()
        self.title("竞拍之王展示柜优化工具")
        self.geometry("2000x900")
        self.minsize(1040, 560)
        self.resizable(False, False)

        self.cabinets = load_cabinets()
        self.items = load_items()
        self.backpack_items = load_backpack_items()
        self.items_by_name = item_index(self.items)

        self.total_value_var = tk.StringVar()
        self.list_frame: ttk.Frame | None = None

        self.build_layout()
        self.refresh_display()

    def build_layout(self) -> None:
        header = ttk.Frame(self, padding=(12, 12, 12, 6))
        header.pack(fill="x")

        title = ttk.Label(header, text="竞拍之王展示柜优化工具", font=("", 16, "bold"))
        title.pack(side="left")

        analyze_button = ttk.Button(header, text="分析背包替换", command=self.analyze_backpack_replacements)
        analyze_button.pack(side="right")

        analyze_cabinets_button = ttk.Button(header, text="分析展示柜", command=self.show_cabinet_analysis)
        analyze_cabinets_button.pack(side="right", padx=(0, 8))

        required_items_button = ttk.Button(header, text="需保留的物品", command=self.show_required_items)
        required_items_button.pack(side="right", padx=(0, 8))

        total_label = ttk.Label(header, textvariable=self.total_value_var, font=("", 12, "bold"))
        total_label.pack(side="right", padx=(0, 12))

        container = ttk.Frame(self, padding=(12, 6, 12, 12))
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.list_frame = ttk.Frame(canvas)
        self.list_frame.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas_window = canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(canvas_window, width=event.width),
        )

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def refresh_display(self) -> None:
        assert self.list_frame is not None
        for child in self.list_frame.winfo_children():
            child.destroy()

        cabinets_grid = ttk.Frame(self.list_frame)
        cabinets_grid.pack(fill="x")
        for column in range(3):
            cabinets_grid.columnconfigure(column, weight=1, uniform="cabinet_columns")

        for index, cabinet in enumerate(self.cabinets):
            self.add_cabinet_row(cabinets_grid, index, cabinet)
        self.add_backpack_row(cabinets_grid, len(self.cabinets))

        total = calculate_total_value(self.cabinets, self.items_by_name)
        self.total_value_var.set(f"总价值：{total:,}")

    def add_cabinet_row(self, parent: ttk.Frame, index: int, cabinet: dict) -> None:
        item_count = len(cabinet.get("藏品", []))
        row = ttk.LabelFrame(
            parent,
            text=f"{cabinet.get('名称', '')} ({item_count}/{MAX_ITEMS_PER_CABINET})",
            padding=(10, 8, 10, 10),
        )
        row.grid(row=index % 4, column=index // 4, sticky="nsew", padx=5, pady=5)

        title_row = ttk.Frame(row)
        title_row.pack(fill="x")

        edit_button = ttk.Button(
            title_row,
            text="编辑展品",
            command=lambda cabinet_index=index: self.open_editor(cabinet_index),
        )
        edit_button.pack(side="right")

        displayed_items = sorted(cabinet.get("藏品", []), key=sort_key)
        self.add_item_grid(row, displayed_items, "暂无藏品", column_count=3, wraplength=200)

    def add_backpack_row(self, parent: ttk.Frame, index: int) -> None:
        row = ttk.LabelFrame(
            parent,
            text=f"背包内物品 ({len(self.backpack_items)})",
            padding=(10, 8, 10, 10),
        )
        row.grid(row=index % 4, column=index // 4, sticky="nsew", padx=5, pady=5)

        title_row = ttk.Frame(row)
        title_row.pack(fill="x")

        edit_button = ttk.Button(title_row, text="编辑展品", command=self.open_backpack_editor)
        edit_button.pack(side="right")

        clear_button = ttk.Button(title_row, text="清空背包", command=self.clear_backpack)
        clear_button.pack(side="right", padx=(0, 8))

        self.add_backpack_table(row)

    def add_backpack_table(self, parent: ttk.Frame) -> None:
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="both", expand=True, pady=(8, 0))

        style = ttk.Style(parent)
        style.configure("Backpack.Treeview", rowheight=22)

        table = ttk.Treeview(
            table_frame,
            columns=("item_name_1", "count_1", "item_name_2", "count_2"),
            show="headings",
            height=5,
            style="Backpack.Treeview",
        )
        table.heading("item_name_1", text="物品名")
        table.heading("count_1", text="数量")
        table.heading("item_name_2", text="物品名")
        table.heading("count_2", text="数量")
        table.column("item_name_1", minwidth=100, width=180, anchor="w")
        table.column("count_1", minwidth=45, width=55, anchor="center", stretch=False)
        table.column("item_name_2", minwidth=100, width=180, anchor="w")
        table.column("count_2", minwidth=45, width=55, anchor="center", stretch=False)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)

        item_counts = Counter(self.backpack_items)
        if item_counts:
            item_names = sorted(item_counts, key=sort_key)
            for index in range(0, len(item_names), 2):
                first_name = item_names[index]
                second_name = item_names[index + 1] if index + 1 < len(item_names) else ""
                table.insert(
                    "",
                    "end",
                    values=(
                        first_name,
                        item_counts[first_name],
                        second_name,
                        item_counts[second_name] if second_name else "",
                    ),
                )
        else:
            table.insert("", "end", values=("暂无物品", "", "", ""))

        table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def clear_backpack(self) -> None:
        if not self.backpack_items:
            messagebox.showinfo("清空背包", "背包已经是空的")
            return

        confirmed = messagebox.askokcancel("清空背包", "确定要清空 backpack_items.json 中记录的所有背包物品吗？")
        if not confirmed:
            return

        old_backpack_items = list(self.backpack_items)
        self.backpack_items = []
        try:
            write_backpack_items(self.backpack_items)
        except Exception as exc:  # pragma: no cover - messagebox path is GUI-only.
            self.backpack_items = old_backpack_items
            messagebox.showerror("清空失败", f"backpack_items.json 写入失败：\n{exc}")
            return

        self.backpack_items = load_backpack_items()
        self.refresh_display()

    def add_item_grid(
        self,
        parent: ttk.Frame,
        items: list[str],
        empty_text: str,
        column_count: int,
        wraplength: int,
    ) -> None:
        if not items:
            empty_label = ttk.Label(parent, text=empty_text, foreground="#777777")
            empty_label.pack(fill="x", pady=(8, 0))
            return

        grid = ttk.Frame(parent)
        grid.pack(fill="x", pady=(8, 0))

        for column in range(column_count):
            grid.columnconfigure(column, weight=1, uniform="item_columns")

        for item_index, item_name in enumerate(items):
            row = item_index // column_count
            column = item_index % column_count
            item_label = ttk.Label(
                grid,
                text=f"{item_index + 1}. {item_name}",
                wraplength=wraplength,
                justify="left",
                padding=(2, 0),
            )
            item_label.grid(row=row, column=column, sticky="ew", padx=(0, 20), pady=1)

    def open_editor(self, cabinet_index: int) -> None:
        cabinet = self.cabinets[cabinet_index]
        allowed_names = allowed_item_names(cabinet, self.items)
        self.open_item_editor(
            title=f"编辑展品 - {cabinet.get('名称', '')}",
            info_text=f"{cabinet.get('名称', '')} 最多可放 {MAX_ITEMS_PER_CABINET} 个展品",
            options=[""] + allowed_names,
            current_items=sorted(list(cabinet.get("藏品", []))[:MAX_ITEMS_PER_CABINET], key=sort_key),
            save_command=lambda variables, editor: self.save_editor(cabinet_index, variables, editor),
        )

    def open_backpack_editor(self) -> None:
        all_item_names = sorted((item["藏品名"] for item in self.items), key=sort_key)
        item_counts = Counter(self.backpack_items)

        editor = tk.Toplevel(self)
        editor.title("编辑展品 - 背包内物品")
        editor.geometry("760x560")
        editor.minsize(620, 460)
        editor.transient(self)
        editor.grab_set()

        wrapper = ttk.Frame(editor, padding=12)
        wrapper.pack(fill="both", expand=True)

        total_var = tk.StringVar()
        info_row = ttk.Frame(wrapper)
        info_row.pack(fill="x", pady=(0, 10))
        ttk.Label(
            info_row,
            text="通过下拉菜单选择物品并设置数量",
            font=("", 12),
        ).pack(side="left")
        ttk.Label(info_row, textvariable=total_var, font=("", 12, "bold")).pack(side="right")

        table_frame = ttk.Frame(wrapper)
        table_frame.pack(fill="both", expand=True)

        style = ttk.Style(editor)
        style.configure("BackpackEditor.Treeview", font=("", 12), rowheight=30)
        style.configure("BackpackEditor.Treeview.Heading", font=("", 12, "bold"))

        table = ttk.Treeview(
            table_frame,
            columns=("item_name_1", "count_1", "item_name_2", "count_2"),
            show="headings",
            style="BackpackEditor.Treeview",
        )
        table.heading("item_name_1", text="物品名")
        table.heading("count_1", text="数量")
        table.heading("item_name_2", text="物品名")
        table.heading("count_2", text="数量")
        table.column("item_name_1", minwidth=150, width=250, anchor="w")
        table.column("count_1", minwidth=50, width=70, anchor="center", stretch=False)
        table.column("item_name_2", minwidth=150, width=250, anchor="w")
        table.column("count_2", minwidth=50, width=70, anchor="center", stretch=False)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)
        table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        edit_row = ttk.LabelFrame(wrapper, text="添加或修改物品", padding=10)
        edit_row.pack(fill="x", pady=(12, 0))
        edit_row.columnconfigure(1, weight=1)

        item_var = tk.StringVar()
        count_var = tk.IntVar(value=1)
        ttk.Label(edit_row, text="物品", font=("", 12)).grid(row=0, column=0, sticky="w", padx=(0, 8))
        item_combo = ttk.Combobox(
            edit_row,
            textvariable=item_var,
            values=all_item_names,
            state="readonly",
            font=("", 12),
        )
        item_combo.grid(row=0, column=1, sticky="ew", padx=(0, 12))

        ttk.Label(edit_row, text="数量", font=("", 12)).grid(row=0, column=2, sticky="w", padx=(0, 8))
        count_entry = ttk.Entry(
            edit_row,
            textvariable=count_var,
            width=6,
            font=("", 12),
        )
        count_entry.grid(row=0, column=3, sticky="w", padx=(0, 12))

        def refresh_table(selected_item: str = "") -> None:
            table.delete(*table.get_children())
            selected_id = ""
            item_names = sorted(item_counts, key=sort_key)
            for index in range(0, len(item_names), 2):
                first_name = item_names[index]
                second_name = item_names[index + 1] if index + 1 < len(item_names) else ""
                row_id = table.insert(
                    "",
                    "end",
                    values=(
                        first_name,
                        item_counts[first_name],
                        second_name,
                        item_counts[second_name] if second_name else "",
                    ),
                )
                if selected_item in (first_name, second_name):
                    selected_id = row_id

            total_var.set(f"当前总数：{sum(item_counts.values())}")
            if selected_id:
                table.selection_set(selected_id)
                table.focus(selected_id)
                table.see(selected_id)

        def load_clicked_item(event) -> None:
            row_id = table.identify_row(event.y)
            column_id = table.identify_column(event.x)
            if not row_id or column_id not in ("#1", "#2", "#3", "#4"):
                return

            values = table.item(row_id, "values")
            item_offset = 0 if column_id in ("#1", "#2") else 2
            item_name = values[item_offset]
            count = values[item_offset + 1]
            if not item_name:
                return

            table.selection_set(row_id)
            table.focus(row_id)
            item_var.set(item_name)
            count_var.set(int(count))

        def add_or_update_item() -> None:
            item_name = item_var.get()
            if not item_name:
                messagebox.showwarning("背包编辑", "请先选择一个物品", parent=editor)
                return

            try:
                count = int(count_var.get())
            except (tk.TclError, ValueError):
                messagebox.showwarning("背包编辑", "数量必须是整数", parent=editor)
                return

            if count < 1:
                messagebox.showwarning("背包编辑", "数量至少为 1", parent=editor)
                return

            item_counts[item_name] = count
            refresh_table(item_name)

        def delete_selected_item() -> None:
            item_name = item_var.get()
            if not item_name or item_name not in item_counts:
                messagebox.showwarning("背包编辑", "请先点击表格中的一个物品", parent=editor)
                return

            item_counts.pop(item_name, None)
            item_var.set("")
            count_var.set(1)
            refresh_table()

        table.bind("<ButtonRelease-1>", load_clicked_item)
        ttk.Button(edit_row, text="添加/更新", command=add_or_update_item).grid(row=0, column=4)
        ttk.Button(edit_row, text="删除当前", command=delete_selected_item).grid(row=0, column=5, padx=(8, 0))

        button_row = ttk.Frame(wrapper)
        button_row.pack(fill="x", pady=(12, 0))
        ttk.Button(button_row, text="取消", command=editor.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(
            button_row,
            text="保存",
            command=lambda: self.save_backpack_editor(item_counts, editor),
        ).pack(side="right")

        refresh_table()
        editor.update_idletasks()
        self.center_child_window(editor)

    def cabinet_item_summary(self) -> list[dict]:
        seen_counts: dict[str, int] = {}
        summary: dict[str, dict] = {}

        for cabinet in self.cabinets:
            for item_name in cabinet.get("藏品", []):
                seen_counts[item_name] = seen_counts.get(item_name, 0) + 1
                occurrence = seen_counts[item_name]
                item = self.items_by_name.get(item_name)
                if item is None:
                    effective_value = 0
                else:
                    base_value = int(item.get("价值", 0))
                    effective_value = round(base_value * discount_rate_for_occurrence(occurrence))

                if item_name not in summary:
                    summary[item_name] = {
                        "name": item_name,
                        "count": 0,
                        "min_effective_value": effective_value,
                    }

                summary[item_name]["count"] += 1
                summary[item_name]["min_effective_value"] = min(
                    summary[item_name]["min_effective_value"],
                    effective_value,
                )

        return sorted(
            summary.values(),
            key=lambda row: (row["min_effective_value"], sort_key(row["name"])),
        )

    def required_item_summary(self) -> tuple[int, list[dict]]:
        cabinet_summary = self.cabinet_item_summary()
        lowest_effective_value = cabinet_summary[0]["min_effective_value"] if cabinet_summary else 0

        current_counts = Counter()
        for cabinet in self.cabinets:
            current_counts.update(cabinet.get("藏品", []))

        required_items = []
        for item in self.items:
            item_name = item["藏品名"]
            occurrence = current_counts[item_name] + 1
            base_value = int(item.get("价值", 0))
            added_effective_value = round(base_value * discount_rate_for_occurrence(occurrence))
            if added_effective_value <= lowest_effective_value:
                continue

            required_items.append(
                {
                    "name": item_name,
                    "current_count": current_counts[item_name],
                    "added_effective_value": added_effective_value,
                }
            )

        return lowest_effective_value, sorted(
            required_items,
            key=lambda row: (-row["added_effective_value"], sort_key(row["name"])),
        )

    def show_cabinet_analysis(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("展示柜分析")
        dialog.geometry("780x560")
        dialog.minsize(640, 420)
        dialog.transient(self)
        dialog.grab_set()

        wrapper = ttk.Frame(dialog, padding=12)
        wrapper.pack(fill="both", expand=True)

        title = ttk.Label(wrapper, text="展示柜藏品汇总（按最低生效价值升序）", font=("", 14, "bold"))
        title.pack(anchor="w", pady=(0, 10))

        table_frame = ttk.Frame(wrapper)
        table_frame.pack(fill="both", expand=True)

        style = ttk.Style(dialog)
        style.configure("CabinetAnalysis.Treeview", font=("", 12), rowheight=30)
        style.configure("CabinetAnalysis.Treeview.Heading", font=("", 12, "bold"))

        table = ttk.Treeview(
            table_frame,
            columns=("item_name", "count", "min_effective_value"),
            show="headings",
            style="CabinetAnalysis.Treeview",
        )
        table.heading("item_name", text="藏品")
        table.heading("count", text="数量")
        table.heading("min_effective_value", text="最低生效价值")
        table.column("item_name", width=420, anchor="w")
        table.column("count", width=100, anchor="center")
        table.column("min_effective_value", width=160, anchor="e")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)

        for row in self.cabinet_item_summary():
            table.insert(
                "",
                "end",
                values=(
                    row["name"],
                    row["count"],
                    f"{row['min_effective_value']:,}",
                ),
            )

        table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        button_row = ttk.Frame(wrapper)
        button_row.pack(fill="x", pady=(12, 0))
        ttk.Button(button_row, text="关闭", command=dialog.destroy).pack(side="right")

        dialog.update_idletasks()
        self.center_child_window(dialog)

    def show_required_items(self) -> None:
        lowest_effective_value, required_items = self.required_item_summary()

        dialog = tk.Toplevel(self)
        dialog.title("需保留的物品")
        dialog.geometry("840x560")
        dialog.minsize(680, 420)
        dialog.transient(self)
        dialog.grab_set()

        wrapper = ttk.Frame(dialog, padding=12)
        wrapper.pack(fill="both", expand=True)

        title = ttk.Label(
            wrapper,
            text=f"需保留的物品（当前最低生效价值：{lowest_effective_value:,}）",
            font=("", 14, "bold"),
        )
        title.pack(anchor="w", pady=(0, 10))

        table_frame = ttk.Frame(wrapper)
        table_frame.pack(fill="both", expand=True)

        style = ttk.Style(dialog)
        style.configure("RequiredItems.Treeview", font=("", 12), rowheight=30)
        style.configure("RequiredItems.Treeview.Heading", font=("", 12, "bold"))

        table = ttk.Treeview(
            table_frame,
            columns=("item_name", "current_count", "added_effective_value"),
            show="headings",
            style="RequiredItems.Treeview",
        )
        table.heading("item_name", text="藏品")
        table.heading("current_count", text="当前数量")
        table.heading("added_effective_value", text="加入后实际价值")
        table.column("item_name", width=460, anchor="w")
        table.column("current_count", width=120, anchor="center")
        table.column("added_effective_value", width=180, anchor="e")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)

        for row in required_items:
            table.insert(
                "",
                "end",
                values=(
                    row["name"],
                    row["current_count"],
                    f"{row['added_effective_value']:,}",
                ),
            )

        table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        button_row = ttk.Frame(wrapper)
        button_row.pack(fill="x", pady=(12, 0))
        ttk.Button(button_row, text="关闭", command=dialog.destroy).pack(side="right")

        dialog.update_idletasks()
        self.center_child_window(dialog)

    def analyze_backpack_replacements(self) -> None:
        if not self.backpack_items:
            messagebox.showinfo("背包替换分析", "背包内没有物品")
            return

        plan = find_best_replacement_plan(self.cabinets, self.backpack_items, self.items_by_name)
        if plan["increase"] <= 0:
            messagebox.showinfo("背包替换分析", "没有找到能增加总价值的替换方案")
            return

        self.show_replacement_plan_dialog(plan)

    def show_replacement_plan_dialog(self, plan: dict) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("背包替换分析")
        dialog.geometry("720x520")
        dialog.minsize(520, 360)
        dialog.transient(self)
        dialog.grab_set()

        wrapper = ttk.Frame(dialog, padding=12)
        wrapper.pack(fill="both", expand=True)

        text_frame = ttk.Frame(wrapper)
        text_frame.pack(fill="both", expand=True)

        text = tk.Text(text_frame, wrap="word", height=20, font=("", 12), spacing1=2, spacing3=4)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.insert("1.0", format_replacement_plan(plan) + "\n\n点击“确定部署”将部署该方案并同步保存文件。")
        text.configure(state="disabled")

        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        button_row = ttk.Frame(wrapper)
        button_row.pack(fill="x", pady=(12, 0))

        ttk.Button(button_row, text="取消", command=dialog.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(
            button_row,
            text="确定部署",
            command=lambda: self.apply_replacement_plan_from_dialog(plan, dialog),
        ).pack(side="right")

    def apply_replacement_plan_from_dialog(self, plan: dict, dialog: tk.Toplevel) -> None:
        dialog.destroy()
        self.apply_replacement_plan(plan)

    def apply_replacement_plan(self, plan: dict) -> None:
        old_cabinets = self.cabinets
        old_backpack_items = self.backpack_items
        self.cabinets = plan["optimized_cabinets"]
        self.backpack_items = plan["optimized_backpack"]

        try:
            write_cabinets(self.cabinets)
            write_backpack_items(self.backpack_items)
        except Exception as exc:  # pragma: no cover - messagebox path is GUI-only.
            self.cabinets = old_cabinets
            self.backpack_items = old_backpack_items
            try:
                write_cabinets(old_cabinets)
                write_backpack_items(old_backpack_items)
            except Exception:
                pass
            messagebox.showerror("部署失败", f"方案部署失败：\n{exc}")
            return

        self.cabinets = load_cabinets()
        self.backpack_items = load_backpack_items()
        self.refresh_display()
        messagebox.showinfo("部署完成", "方案已部署，并已同步保存展示柜和背包文件。")

    def open_item_editor(
        self,
        title: str,
        info_text: str,
        options: list[str],
        current_items: list[str],
        save_command,
        max_slots: int = MAX_ITEMS_PER_CABINET,
    ) -> None:
        editor = tk.Toplevel(self)
        editor.title(title)
        editor.transient(self)
        editor.grab_set()

        editor_font = ("", 12)
        wrapper = ttk.Frame(editor, padding=12)
        wrapper.pack(fill="both", expand=True)

        info = ttk.Label(wrapper, text=info_text, font=editor_font)
        info.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        variables: list[tk.StringVar] = []
        for slot in range(max_slots):
            ttk.Label(wrapper, text=f"展品 {slot + 1}", font=editor_font).grid(
                row=slot + 1,
                column=0,
                sticky="w",
                pady=4,
            )
            value = current_items[slot] if slot < len(current_items) else ""
            variable = tk.StringVar(value=value)
            variables.append(variable)

            combo = ttk.Combobox(
                wrapper,
                textvariable=variable,
                values=options,
                state="readonly",
                width=38,
                font=editor_font,
            )
            combo.grid(row=slot + 1, column=1, sticky="ew", pady=4)

        wrapper.columnconfigure(1, weight=1)

        button_row = ttk.Frame(wrapper)
        button_row.grid(row=max_slots + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))

        ttk.Button(button_row, text="取消", command=editor.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(
            button_row,
            text="保存",
            command=lambda: save_command(variables, editor),
        ).pack(side="right")

        editor.update_idletasks()
        self.center_child_window(editor)

    def center_child_window(self, child: tk.Toplevel) -> None:
        self.update_idletasks()
        child_width = child.winfo_width()
        child_height = child.winfo_height()
        parent_x = self.winfo_rootx()
        parent_y = self.winfo_rooty()
        parent_width = self.winfo_width()
        parent_height = self.winfo_height()
        x = parent_x + (parent_width - child_width) // 2
        y = parent_y + (parent_height - child_height) // 2
        child.geometry(f"+{max(0, x)}+{max(0, y)}")

    def save_editor(self, cabinet_index: int, variables: list[tk.StringVar], editor: tk.Toplevel) -> None:
        new_items = sorted((variable.get() for variable in variables if variable.get()), key=sort_key)
        old_items = list(self.cabinets[cabinet_index].get("藏品", []))
        self.cabinets[cabinet_index]["藏品"] = new_items

        try:
            write_cabinets(self.cabinets)
        except Exception as exc:  # pragma: no cover - messagebox path is GUI-only.
            self.cabinets[cabinet_index]["藏品"] = old_items
            messagebox.showerror("保存失败", f"display_cabinets.toml 写入失败：\n{exc}")
            return

        self.cabinets = load_cabinets()
        self.refresh_display()
        editor.destroy()

    def save_backpack_editor(self, item_counts: Counter, editor: tk.Toplevel) -> None:
        new_items = []
        for item_name in sorted(item_counts, key=sort_key):
            new_items.extend([item_name] * item_counts[item_name])

        old_items = list(self.backpack_items)
        self.backpack_items = new_items

        try:
            write_backpack_items(self.backpack_items)
        except Exception as exc:  # pragma: no cover - messagebox path is GUI-only.
            self.backpack_items = old_items
            messagebox.showerror("保存失败", f"backpack_items.json 写入失败：\n{exc}")
            return

        self.backpack_items = load_backpack_items()
        self.refresh_display()
        editor.destroy()


def main() -> None:
    app = CabinetApp()
    app.mainloop()


if __name__ == "__main__":
    main()
