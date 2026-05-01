---
name: holiday-checker
description: 查询中国节假日/工作日安排，基于聚合API
---

# holiday-checker

查询指定日期的假日安排（节假日/工作日/周末），返回类型、节日名称、农历、宜忌等信息。

## 触发条件

需要判断某日期是否为工作日/节假日时使用。本技能是纯查询工具，不做报告生成。

## 环境变量

```bash
# ~/.hermes/.env
JUHE_HOLIDAY_KEY=25ff99ed5737fdc2d7438dfa4995030d
```

## 使用方式

```bash
# 查询今天（自动判断工作日/节假日）
python3 ~/.hermes/skills/devops/holiday-checker/scripts/holiday_check.py

# 查询指定日期
python3 ~/.hermes/skills/devops/holiday-checker/scripts/holiday_check.py 2026-05-01

# 查询指定日期（详细信息，含宜忌、农历）
python3 ~/.hermes/skills/devops/holiday-checker/scripts/holiday_check.py 2026-05-01 -d

# 判断某日距下一个工作日
python3 ~/.hermes/skills/devops/holiday-checker/scripts/holiday_check.py 2026-04-18 -n
```

## 返回示例

```
🎉 2026-05-01（星期五）
   类型：节假日
   节日：劳动节
   宜：搬家.装修.开业.结婚.入宅...
   忌：动土.安葬.破土...
   农历：丙午年四月廿七
```

## 常用判断逻辑

| 场景 | 调用 |
|------|------|
| 判断某日是否工作日 | `is_workday("2026-04-20")` → `True/False/None` |
| 获取下一工作日 | `next_workday("2026-04-18")` → `"2026-04-21"` |
| 获取上一工作日 | `prev_workday("2026-04-20")` → `"2026-04-17"` |
| 批量判断日期范围 | 循环调用 `is_workday()` |

## 依赖

- Python 标准库（`urllib`, `json`, `pathlib`, `datetime`）
- 网络访问（访问聚合API）

## 注意事项

- 查询日期必须大于 2021 年
- API 每日有请求次数限制（约 100 次/天），批量查询时建议加缓存
- 周末不一定是节假日，"周末" 状态表示非工作日
