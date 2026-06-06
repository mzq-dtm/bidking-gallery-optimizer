# 竞拍之王展示柜优化工具

竞拍之王展示柜优化工具是一个面向游戏《竞拍之王》的展示柜管理与银币产出优化工具，使用 Python 和 Tkinter 编写。

在游戏中，玩家可以将竞拍得到的战利品放入展示柜，展示柜内藏品的折后总价值决定每小时银币产出效率。本工具的核心目标是从现有库存中寻找折后总价值最高的摆放方案，从而最大化银币产出效率，并在产出效率相同时尽量减少移动步骤。

## 功能

- 图形化管理 11 个展示柜和背包库存
- 按展示柜类别限制可放藏品
- 自动排序展示柜中的藏品及对应 TOML 数据
- 汇总藏品数量和最低生效价值
- 筛选可能值得保留的物品
- 使用最大费用流最大化折后总价值和银币产出效率
- 使用最小费用流减少同产出效率方案的移动步骤
- 预览替换步骤，确认后再写入数据文件
- 使用表格按物品名和数量编辑背包，背包数量不设上限

## 环境要求

- Python 3.11 或更高版本
- Tkinter

项目只使用 Python 标准库，没有第三方运行依赖。

## 快速开始

克隆或下载项目后，在项目目录运行：

```bash
python main.py
```

也可以直接启动 GUI 模块：

```bash
python cabinet_gui.py
```

使用 Conda 时，可以先激活自己的 Python 3.11+ 环境：

```powershell
conda activate <your-environment>
python main.py
```

## 数据文件

程序直接读取和更新项目根目录中的数据文件：

| 文件 | 用途 |
|---|---|
| `display_cabinets.toml` | 展示柜、允许类别和当前藏品 |
| `item_category.json` | 藏品名称、价值和类别 |
| `backpack_items.json` | 背包库存 |

运行前建议备份自己的数据文件。

## 项目结构

```text
bidking_gallery/
├── main.py
├── cabinet_gui.py
├── optimize_cabinet.py
├── optimize_plan.py
├── utils.py
├── display_cabinets.toml
├── item_category.json
├── backpack_items.json
└── docs/
    ├── USER_GUIDE.md
    ├── DATA_FORMAT.md
    ├── OPTIMIZATION.md
    └── ARCHITECTURE.md
```

## 文档

- [用户指南](docs/USER_GUIDE.md)
- [数据格式](docs/DATA_FORMAT.md)
- [优化算法](docs/OPTIMIZATION.md)
- [项目架构](docs/ARCHITECTURE.md)

## 工作原理

展示柜内藏品的折后总价值越高，每小时银币产出效率越高。因此，最大化折后总价值就是本工具的首要优化目标。

优化分为两个阶段：

1. 最大费用流从展示柜和背包总库存中选择折后总价值最高的藏品，最大化银币产出效率。
2. 最小费用流在保持最高银币产出效率的前提下，尽量让藏品留在原展示柜，减少移动。

详细推导见 [优化算法](docs/OPTIMIZATION.md)。
