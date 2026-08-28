import json, os

def load_records(path="../results/scored_results.jsonl"):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

def load_cases(path="../cases/cases.json"):
    return json.load(open(path, encoding="utf-8"))

def calc_accuracy(records):
    total = len(records)
    ok = sum(r["llm_score"] for r in records)
    return round(ok / total * 100, 1) if total else 0

def build_report(records, cases):
    diff_map = {c["id"]: c.get("difficulty","") for c in cases}
    for r in records:
        r["difficulty"] = diff_map.get(r["id"],"")

    lines = []
    lines.append("# 大模型评测报告：电商智能客服")
    lines.append("")
    lines.append("## 实验配置（可复现性）")
    lines.append("- 被测模型：DeepSeek（temperature=0）")
    lines.append("- 裁判模型：Qwen（temperature=0，JSON输出，重试3次）")
    lines.append("- 评测集：100条（事实40/推理20/开放20/边界10/对抗10）")
    lines.append("- 被测对象：系统提示词（电商智能客服角色）+ 模型")
    lines.append("")
    lines.append("## 总体结果")
    lines.append(f"- 整体准确率：{calc_accuracy(records)}%（LLM裁判）")
    lines.append("")
    lines.append("| 类别 | 条数 | 准确率（裁判） | 规则评分 |")
    lines.append("| --- | --- | --- | --- |")
    for cat in ["事实类", "推理类", "开放类", "边界类", "对抗类"]:
        sub = [r for r in records if r["category"] == cat]
        llm = calc_accuracy(sub)
        rule = round(sum(r["rule_score"] for r in sub) / len(sub) * 100, 1)
        lines.append(f"| {cat} | {len(sub)} | {llm}% | {rule}% |")
    lines.append("")
    lines.append("## 按难度统计（LLM裁判）")
    for diff in ["简单", "中等", "困难"]:
        sub = [r for r in records if r.get("difficulty") == diff]
        if sub:
            lines.append(f"- {diff}：{calc_accuracy(sub)}%（n={len(sub)}）")
    lines.append("")
    lines.append("## 失败样例（每类最多2条）")
    for cat in ["事实类", "推理类", "开放类", "边界类", "对抗类"]:
        fails = [r for r in records if r["category"] == cat and r["llm_score"] == 0][:2]
        for f in fails:
            lines.append(f"### id={f['id']}（{cat}）")
            lines.append(f"- 问题：{f['question']}")
            lines.append(f"- 参考答案：{f['golden_answer']}")
            lines.append(f"- 模型回答：{str(f['answer'])[:200]}")
            lines.append(f"- 裁判理由：{f.get('llm_reason', '')}")
    lines.append("")
    lines.append("## 结论")
    lines.append("（把下面的模板改成你自己的真实数字）")
    return "\n".join(lines)


if __name__ == "__main__":
    records = load_records()
    cases = load_cases()
    report = build_report(records, cases)
    os.makedirs("reports", exist_ok=True)
    with open("../reports/eval_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("报告已生成：reports/eval_report.md")