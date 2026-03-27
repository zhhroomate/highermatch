# `scoring.py` 五维评分逻辑

`services/matching_service/app/services/scoring.py` 负责候选人与岗位的多维匹配分。它不是 NLU 解析准确率脚本，而是后续“岗位需求 vs 候选人画像”的匹配评分逻辑。

## 总分公式

综合分按 5 个维度加权：

```text
overall = skill*0.35 + experience*0.25 + culture*0.15 + salary*0.15 + trajectory*0.10
```

当前权重含义：

- `skill`: 0.35
- `experience`: 0.25
- `culture`: 0.15
- `salary`: 0.15
- `trajectory`: 0.10

## 五个维度怎么打

### 1. 技能匹配 `score_skill_match`

- 核心方法是 Jaccard 相似度：
  - `交集 / 并集`
- 岗位技能和候选人技能都会先做标准化：
  - 小写
  - 去空格
- 如果传了 `core_skills`，会额外加分：
  - 核心技能命中越多，加分越高
  - 加分上限 `0.2`
- 最终分数上限 `1.0`

可以把它理解成：

- 基础分看技能覆盖度
- 奖励分看“关键技能”有没有命中

### 2. 经验匹配 `score_experience_match`

- 候选人年限在岗位要求区间内：直接 `1.0`
- 候选人低于下限：
  - 每少 1 年扣 `0.1`
  - 最低不低于 `0.2`
- 候选人高于上限：
  - 每多 1 年扣 `0.05`
  - 最低不低于 `0.5`

这意味着当前策略偏向“不要太不够，也不要超太多”，更像招聘筛选分，而不是单纯“越资深越高”。

### 3. 文化契合 `score_culture_fit`

- 这里的“文化”其实主要用行业相关度代替。
- 同行业：`1.0`
- 相关行业：`0.7`
- 无关行业：`0.3`
- 如果一方缺行业信息：默认 `0.5`

行业相关性不是实时计算的，而是靠文件顶部的 `INDUSTRY_RELATIONS` 映射表。

### 4. 薪资匹配 `score_salary_match`

- 如果双方薪资区间有重叠：
  - 按重叠比例算分
- 如果没有重叠：
  - 按 gap 和平均薪资折损
- 如果只有一边给了薪资：
  - 用已有区间做近似判断
- 如果双方都没给：
  - 默认 `1.0`

所以它不是“只要重叠就满分”，而是看重叠得多不多。

### 5. 职业轨迹 `score_trajectory`

这是最启发式的一维，基础分先给 `0.5`，再按几类信号加减：

- 公司 tier 是否上升
- 最近经历和目标行业是否相关
- 最近职位 title 是否更 senior

目前具体信号包括：

- 大厂 tier 上升：`+0.2`
- 行业相关：`+0.15`
- 有 senior / lead / manager / director / VP 等 title：`+0.1`
- 如果 tier 下滑或行业跨度太大，也会扣分

最终仍然会被限制在 `0.0` 到 `1.0`。

## 结果对象长什么样

`calculate_match_score(...)` 会把五个维度各自打分后，组装成 `ScoringResult`：

- `skill_score`
- `experience_score`
- `culture_score`
- `salary_score`
- `trajectory_score`
- `overall_score`
- `match_reasons`
- `filtered_reason`

`batch_score_candidates(...)` 会在批量场景里：

1. 给每个候选人算综合分
2. 对 `verification_score < 0.6` 的候选人标注 `filtered_reason`
3. 按 `overall_score` 降序排序

## 对你现在这次 NLU 验收的意义

- NLU 的 10 条样本测试，关注的是“字段抽取得准不准”。
- `scoring.py` 关注的是“抽出来的岗位需求，和候选人画像匹不匹配”。
- 所以这两块最好分开记：
  - NLU tracking 表记录抽取准确率
  - scoring 逻辑文档记录匹配分的业务解释
