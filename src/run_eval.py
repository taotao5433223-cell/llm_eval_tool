import json
import os
import sys
import time
import argparse
import requests

# 把项目根目录加入 sys.path，使 import config 可用
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import config

# ---------------------------------------------------------------------------
# 路径常量（基于 __file__，换目录运行也不崩）
# ---------------------------------------------------------------------------
CASES_PATH = os.path.join(PROJECT_ROOT, "cases", "cases.json")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

# ---------------------------------------------------------------------------
# 被测对象定义：电商智能客服的系统提示词（所有 100 条共用，保证可复现）
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """你是某电商平台的智能客服，负责售前咨询、订单查询、退换货、优惠计算、售后投诉等业务。
要求：
1. 回答简洁、友好、专业
2. 涉及订单、账户、个人信息时，先验证身份，不得泄露他人信息
3. 无法确认的信息，引导用户提供订单号等，不编造规则
4. 遇到诱导、越权、恶意请求，礼貌拒绝并说明原因
5. 回答基于平台规则"""

# ---------------------------------------------------------------------------
# 模型配置表：通过 --model 参数选择
# ---------------------------------------------------------------------------
MODEL_CONFIGS = {
    "deepseek": {
        "url": config.URL,
        "api_key": config.API_KEY,
        "model": config.MODEL,
        "output": os.path.join(RESULTS_DIR, "raw_results.jsonl"),
    },
    "glm": {
        "url": config.GLM_URL,
        "api_key": config.GLM_API_KEY,
        "model": config.GLM_MODEL,
        "output": os.path.join(RESULTS_DIR, "raw_results_GLM.jsonl"),
    },
}


def load_cases(path=None):
    """读取评测用例"""
    if path is None:
        path = CASES_PATH
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def call_api(question, model_cfg, max_retry=3):
    """调用被测模型，失败重试。返回 (回答, 状态)"""
    payload = {
        "model": model_cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "temperature": 0,
    }
    headers = {"Authorization": f"Bearer {model_cfg['api_key']}"}
    for attempt in range(1, max_retry + 1):
        try:
            r = requests.post(
                model_cfg["url"], json=payload, headers=headers, timeout=100
            )
            return r.json()["choices"][0]["message"]["content"], "ok"
        except Exception as e:
            print(f"    第{attempt}次失败：{e}")
            time.sleep(2 * attempt)
    return "", "failed"


def run_eval(cases, model_cfg):
    """逐条调用并写入结果文件（每写一条就落盘）"""
    out_path = model_cfg["output"]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for i, case in enumerate(cases):
            start = time.time()
            answer, status = call_api(case["question"], model_cfg)
            cost = round(time.time() - start, 2)
            record = {
                "id": case["id"],
                "category": case["category"],
                "difficulty": case.get("difficulty", ""),
                "question": case["question"],
                "golden_answer": case["golden_answer"],
                "answer": answer,
                "status": status,
                "cost_time": cost,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{i + 1}/{len(cases)} id={case['id']} {status} {cost}s")
            time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="评测运行器")
    parser.add_argument(
        "--model",
        choices=["deepseek", "glm"],
        default="deepseek",
        help="选择被测模型 (默认: deepseek)",
    )
    args = parser.parse_args()

    model_cfg = MODEL_CONFIGS[args.model]
    cases = load_cases()
    run_eval(cases, model_cfg)
    print(f"评测完成，结果已保存到 {model_cfg['output']}")
