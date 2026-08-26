import time, json, os
from

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

def call_api(question,max_retries=3):
    payload = {
        "model":
    }