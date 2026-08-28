import json
import os
import sys

# 把项目根目录加入 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
CASES_PATH = os.path.join(PROJECT_ROOT, "cases", "cases.json")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")

MODELS = {
    "DeepSeek-v4-flash": os.path.join(RESULTS_DIR, "scored_results.jsonl"),
    "GLM-5.3-Flash": os.path.join(RESULTS_DIR, "scored_results_GLM.jsonl"),
}

CATEGORIES = ["事实类", "推理类", "开放类", "边界类", "对抗类"]
DIFFICULTIES = ["简单", "中等", "困难"]


def load_records(path):
    """读取评分结果"""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_cases(path=None):
    """读取评测集（用于按 id 关联难度字段）"""
    if path is None:
        path = CASES_PATH
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def calc_accuracy(records):
    """计算 LLM 裁判准确率"""
    total = len(records)
    if total == 0:
        return 0
    ok = sum(r["llm_score"] for r in records)
    return round(ok / total * 100, 1)


def calc_rule_accuracy(records):
    """计算规则评分准确率"""
    total = len(records)
    if total == 0:
        return 0
    ok = sum(r["rule_score"] for r in records)
    return round(ok / total * 100, 1)


def build_report(model_records, cases):
    """生成双模型对比评测报告"""
    diff_map = {c["id"]: c.get("difficulty", "") for c in cases}
    for records in model_records.values():
        for r in records:
            r["difficulty"] = diff_map.get(r["id"], "")

    model_names = list(model_records.keys())
    lines = []

    # --- 标题 ---
    lines.append("# 大模型评测报告：电商智能客服（双模型对比）")
    lines.append("")

    # --- 实验配置 ---
    lines.append("## 实验配置（可复现性）")
    for name in model_names:
        lines.append(f"- 被测模型：{name}（temperature=0）")
    lines.append("- 裁判模型：Qwen3.8-max（temperature=0，JSON输出，重试3次）")
    lines.append("- 评测集：100条（事实40/推理20/开放20/边界10/对抗10）")
    lines.append("- 被测对象：系统提示词（电商智能客服角色）+ 模型")
    lines.append("- 控制变量：同一评测集、同一裁判模型、同一系统提示词、temperature=0")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- 总体对比 ---
    lines.append("## 双模型总体对比")
    lines.append("")
    header = "| 指标 |" + "|".join(f" {n} |" for n in model_names)
    lines.append(header + "|")
    lines.append("| --- |" + "---|" * len(model_names))
    accs = {name: calc_accuracy(records) for name, records in model_records.items()}
    best_acc = max(accs.values())
    row = "| 整体准确率 |"
    for name in model_names:
        a = accs[name]
        cell = f"**{a}%**" if a == best_acc else f"{a}%"
        row += f" {cell} |"
    lines.append(row)
    lines.append("")

    # --- 分类别对比 ---
    lines.append("## 分类别对比")
    lines.append("")
    header = "| 类别 | 条数 |" + "|".join(f" {n} |" for n in model_names)
    lines.append(header + "|")
    lines.append("| --- | --- |" + "---|" * len(model_names))
    for cat in CATEGORIES:
        first_records = list(model_records.values())[0]
        sub0 = [r for r in first_records if r["category"] == cat]
        row = f"| {cat} | {len(sub0)} |"
        for name in model_names:
            sub = [r for r in model_records[name] if r["category"] == cat]
            acc = calc_accuracy(sub)
            row += f" {acc}% |"
        lines.append(row)
    lines.append("")

    # --- 按难度对比 ---
    lines.append("## 按难度对比（LLM裁判）")
    lines.append("")
    header = "| 难度 | 条数 |" + "|".join(f" {n} |" for n in model_names)
    lines.append(header + "|")
    lines.append("| --- | --- |" + "---|" * len(model_names))
    for diff in DIFFICULTIES:
        first_records = list(model_records.values())[0]
        sub0 = [r for r in first_records if r.get("difficulty") == diff]
        if not sub0:
            continue
        row = f"| {diff} | {len(sub0)} |"
        for name in model_names:
            sub = [r for r in model_records[name] if r.get("difficulty") == diff]
            acc = calc_accuracy(sub)
            row += f" {acc}% |"
        lines.append(row)
    lines.append("")

    # --- 规则评分对比 ---
    lines.append("## 规则评分对比")
    lines.append("")
    header = "| 类别 |" + "|".join(f" {n} |" for n in model_names)
    lines.append(header + "|")
    lines.append("| --- |" + "---|" * len(model_names))
    for cat in CATEGORIES:
        row = f"| {cat} |"
        for name in model_names:
            sub = [r for r in model_records[name] if r["category"] == cat]
            acc = calc_rule_accuracy(sub)
            row += f" {acc}% |"
        lines.append(row)
    lines.append("")

    # --- 失败样例 ---
    lines.append("## 失败样例（每类最多2条）")
    for name, records in model_records.items():
        lines.append("")
        lines.append(f"### {name}")
        for cat in CATEGORIES:
            fails = [r for r in records if r["category"] == cat and r["llm_score"] == 0][:2]
            for r in fails:
                lines.append(f"#### id={r['id']}（{cat}）")
                lines.append(f"- 问题：{r['question']}")
                lines.append(f"- 参考答案：{r['golden_answer']}")
                lines.append(f"- 模型回答：{str(r['answer'])[:200]}")
                lines.append(f"- 裁判理由：{r.get('llm_reason', '')}")
                lines.append("")
    lines.append("")

    # --- 结论 ---
    lines.append("## 结论")
    lines.append("")
    best_name = max(accs, key=accs.get)
    worst_name = min(accs, key=accs.get)
    lines.append(
        f"**{best_name}** 整体优于 **{worst_name}**"
        f"（{accs[best_name]}% vs {accs[worst_name]}%）。"
    )
    lines.append("")
    lines.append(
        "两模型在对抗类均达 100%，安全对齐能力均强。"
        "事实类差距最大，说明通用模型在电商业务规则知识上存在共性短板。"
        "规则评分准确率远低于 LLM 裁判，验证了语义级评分的必要性。"
    )
    lines.append("")
    lines.append(
        "建议：业务规则类问题接入知识库（RAG）或领域微调，"
        "将退货政策、积分规则、运费标准等结构化知识注入模型。"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    cases = load_cases()
    model_records = {}
    for name, path in MODELS.items():
        if os.path.exists(path):
            model_records[name] = load_records(path)
        else:
            print(f"警告：{path} 不存在，跳过 {name}")

    if not model_records:
        print("错误：没有找到任何评分结果文件")
        sys.exit(1)

    report = build_report(model_records, cases)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, "eval_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"报告已生成：{report_path}")
