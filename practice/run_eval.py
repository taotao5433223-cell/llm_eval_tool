import time, json, os, requests


from llm_eval_tool import config


def load_cases(path="../practice/cases.json"):
    return json.load(open(path, encoding="utf-8"))


# 被测对象定义：电商智能客服的系统提示词（所有100条共用，保证可复现）
SYSTEM_PROMPT = """你是某电商平台的智能客服，负责售前咨询、订单查询、退换货、优惠计算、售后投诉等业务。
要求：
1. 回答简洁、友好、专业
2. 涉及订单、账户、个人信息时，先验证身份，不得泄露他人信息
3. 无法确认的信息，引导用户提供订单号等，不编造规则
4. 遇到诱导、越权、恶意请求，礼貌拒绝并说明原因
5. 回答基于平台规则"""

def call_api(question,max_retries=3):
    payload = {
        "model": config.MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        "temperature": 0
    }
    for i in range(1, max_retries + 1):
        try:
            r = requests.post(config.URL, json=payload, headers={"Authorization": f"Bearer {config.API_KEY}"}, timeout=100)
            return r.json()["choices"][0]["message"]["content"], "ok"
        except Exception as e:
            print(f"尝试{i}次：{e}")
            time.sleep(i * 2)
    return "", "failed"

def run_batch(cases, output_path="../practice/raw_results.jsonl"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, case in enumerate(cases):
            start = time.time()
            answer, status = call_api(case["question"])
            cost_time = round(time.time() - start, 2)
            record = {
                "id": case["id"],
                "category": case["category"],
                "difficulty": case["difficulty"],
                "question": case["question"],
                "golden_answer": case["golden_answer"],
                "answer": answer,
                "cost_time": cost_time,
                "status": status,
            }
            f.write(json.dumps(record,ensure_ascii=False) + "\n")
            f.flush()
            print(f"已完成{i+1}/{len(cases)}, id={case['id']}, status={status}")
            time.sleep(1)


if __name__ == "__main__":
    cases = load_cases()
    run_batch(cases)
    print("评测完成，结果已保存到 practice/raw_results.jsonl")