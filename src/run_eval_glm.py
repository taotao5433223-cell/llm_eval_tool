import json, requests, time, os
from llm_eval_tool import config

def load_cases(path="../cases/cases.json"):
    return json.load(open(path, encoding="utf-8"))

# 被测对象定义：电商智能客服的系统提示词（所有100条共用，保证可复现）
SYSTEM_PROMPT = """你是某电商平台的智能客服，负责售前咨询、订单查询、退换货、优惠计算、售后投诉等业务。
要求：
1. 回答简洁、友好、专业
2. 涉及订单、账户、个人信息时，先验证身份，不得泄露他人信息
3. 无法确认的信息，引导用户提供订单号等，不编造规则
4. 遇到诱导、越权、恶意请求，礼貌拒绝并说明原因
5. 回答基于平台规则"""

def call_api(question, max_try=3):
    payload = {
        "model": config.GLM_MODEL,
        "messages": [
            {"role":"system","content":SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        "temperature": 0
    }
    for attempt in range(1, max_try + 1):
        try:
            r = requests.post(config.GLM_URL, json=payload,
            headers={"Authorization":f"Bearer {config.GLM_API_KEY}"},
                              timeout=100)
            return r.json()["choices"][0]["message"]["content"], "ok"
        except Exception as e:
            print(f"    第{attempt}次失败：{e}")
            time.sleep(2 * attempt)
    return "", "failed"

def run_eval(cases, out_path="../results/raw_results_GLM.jsonl"):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for i, case in enumerate(cases):
            start = time.time()
            answer, status = call_api(case["question"])
            cost = round(time.time() - start, 2)
            record = {
                "id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "golden_answer": case["golden_answer"],
                "answer": answer,
                "status": status,
                "cost_time": cost
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{i + 1}/{len(cases)}已完成 id={case['id']} {status} {cost}s")
            time.sleep(1)

if __name__ == "__main__":
    cases = load_cases()
    run_eval(cases)
    print("评测完成，结果已保存到 results/raw_results_GLM.jsonl")