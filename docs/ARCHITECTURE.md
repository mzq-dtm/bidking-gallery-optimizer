# 项目架构

## 模块结构

项目由五个 Python 模块组成：

| 文件 | 职责 |
|---|---|
| `main.py` | 推荐启动入口 |
| `cabinet_gui.py` | Tkinter 主界面、编辑窗口、分析窗口和方案部署 |
| `optimize_cabinet.py` | 最大费用流与最高银币产出效率方案 |
| `optimize_plan.py` | 同产出效率少移动重排、移动步骤和最终背包 |
| `utils.py` | 常量、数据读写、排序、价值计算、类别与库存工具 |

## 调用流程

```text
main.py
  -> cabinet_gui.main()
  -> CabinetApp
      -> utils 读取数据
      -> optimize_plan 生成替换方案
          -> optimize_cabinet 最大化折后总价值和银币产出效率
          -> 最小费用流减少移动
      -> utils 写回部署结果
```

## 主要函数

### utils.py

- `load_cabinets()`：读取展示柜 TOML，并排序各柜藏品。
- `load_items()`：读取藏品目录 JSON。
- `load_backpack_items()`：读取背包 JSON。
- `write_cabinets()`：排序并写回展示柜 TOML。
- `write_backpack_items()`：写回背包 JSON。
- `sort_cabinet_items()`：统一排序展示柜藏品。
- `calculate_total_value()`：计算决定银币产出效率的展示折后总价值。
- `discount_rate_for_occurrence()`：返回第 N 件同名藏品的价值比例。
- `item_can_go_in_cabinet()`：检查藏品和展示柜的类别匹配。
- `collect_inventory()`：汇总展示柜和背包库存。

### optimize_cabinet.py

- `MaxCostFlow`：最大费用流实现。
- `build_optimized_cabinets()`：计算银币产出效率最高的展示方案。

### optimize_plan.py

- `MinCostFlow`：最小费用满流实现。
- `minimize_steps_for_same_value()`：在保持价值的前提下减少移动步骤。
- `minimize_moves_for_same_value()`：同价值少移动的回退方案。
- `improve_assignment_by_swaps()`：通过合法交换增加原柜保留数量。
- `build_rearrangement_moves()`：生成可执行移动步骤。
- `build_optimized_backpack()`：计算部署后的背包。
- `find_best_replacement_plan()`：生成完整替换方案。
- `format_replacement_plan()`：格式化方案文本。

### cabinet_gui.py

- `CabinetApp`：GUI 主类。
- `refresh_display()`：重建主界面内容。
- `open_editor()`：打开展示柜编辑器。
- `open_backpack_editor()`：打开背包表格编辑器。
- `cabinet_item_summary()`：汇总当前展示藏品及最低生效价值。
- `required_item_summary()`：计算可能值得保留的物品。
- `analyze_backpack_replacements()`：运行替换分析。
- `apply_replacement_plan()`：部署方案并写入文件。

## 运行环境

- Python 3.11 或更高版本，项目使用标准库 `tomllib`。
- Tkinter，用于桌面 GUI。
- 项目当前没有第三方 Python 运行依赖。
