# NLU 10 条样本 Tracking 表

## 使用方法

1. 先按 `docs/postman_nlu_runbook.md` 跑通登录和 `/api/v1/nlu/parse`。
2. 手工在 Postman 里逐条验证时，可以直接填下面这张表。
3. 如果想自动生成 CSV，执行：

```powershell
python scripts/nlu_accuracy_eval.py --base-url http://localhost --token "<access_token>"
```

## 样本来源

- JSON 样本文件：`scripts/nlu_eval_samples.json`
- 自动输出文件：`docs/nlu_accuracy_tracking.csv`

## Tracking Table

| ID | 输入样本 | 期望职位 | 期望技能 | 期望年限 | 期望地点 | 实际抽取摘要 | 样本准确率 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | 3年Python工程师，成都 | Python工程师 | Python | 3-3 | 成都 |  |  |  |
| S02 | 招高级Java后端，5年以上经验，北京海淀，40-60K | Java后端工程师 | Java | 5+ | 北京 |  |  |  |
| S03 | 上海招1-3年产品经理，熟悉B端SaaS | 产品经理 | SaaS | 1-3 | 上海 |  |  |  |
| S04 | 深圳数据分析师，2年经验，熟练SQL和Power BI，15-25K | 数据分析师 | SQL, Power BI | 2-2 | 深圳 |  |  |  |
| S05 | 杭州算法工程师，机器学习/深度学习，3到5年，30-45K | 算法工程师 | 机器学习, 深度学习 | 3-5 | 杭州 |  |  |  |
| S06 | 广州前端开发，React+TypeScript，2年以上 | 前端开发工程师 | React, TypeScript | 2+ | 广州 |  |  |  |
| S07 | 远程DevOps工程师，Kubernetes Docker，5年，35K以上 | DevOps工程师 | Kubernetes, Docker | 5-5 | 远程 |  |  |  |
| S08 | 成都测试开发，Python自动化测试，3年，20-30K | 测试开发工程师 | Python, 自动化测试 | 3-3 | 成都 |  |  |  |
| S09 | 西安HRBP，4年招聘和员工关系经验 | HRBP | 招聘, 员工关系 | 4-4 | 西安 |  |  |  |
| S10 | 南京C++嵌入式工程师，STM32，2-4年，双休 | C++嵌入式工程师 | C++, STM32 | 2-4 | 南京 |  |  |  |

## 建议记录口径

- `实际抽取摘要`：建议简写成 `职位 / 技能 / 年限 / 地点 / 薪资`。
- `样本准确率`：建议和 `scripts/nlu_accuracy_eval.py` 一致，按 5 个维度平均：
  - 职位名
  - 技能
  - 年限
  - 地点
  - 薪资
- `备注`：标异常点，比如“只抽到了 Java，没识别后端”“地点抽成北京海淀也算通过”等。
