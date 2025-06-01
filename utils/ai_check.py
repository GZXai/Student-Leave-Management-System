import hashlib
import json
import logging
import os
from functools import lru_cache

import requests

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 缓存最近100个审核结果
@lru_cache(maxsize=100)
def get_cache_key(reason: str, min_score: int) -> str:
    return hashlib.md5(f"{reason}_{min_score}".encode()).hexdigest()

def check_reason_validity(reason: str, min_score: int = 12) -> dict:
    """
    审核请假理由有效性的改进版本
    
    参数:
        reason (str): 待审核的请假理由文本
        min_score (int): 通过的最低总分（默认12分）
    
    返回:
        dict: 包含完整审核结果的对象
    """
    # 检查缓存
    cache_key = get_cache_key(reason, min_score)
    if cache_key in check_reason_validity.cache:
        logging.info("从缓存获取审核结果")
        return check_reason_validity.cache[cache_key]
    
    # 从环境变量获取API密钥
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logging.error("API key not found in environment variables")
        return False

    # API配置
    api_url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 优化后的提示词（包含更详细的评分标准）
    prompt = f"""作为学校的班主任老师，请从以下维度严格审核学生请假理由：

评分维度（每个维度0-5分）:
1. 真实性 - 是否有具体细节支持（如医院证明、具体时间等）
2. 紧急性 - 是否确实无法推迟（如急诊、突发事件等）
3. 合理性 - 请假时长是否与事由匹配
4. 合规性 - 是否符合学校请假规定

评分标准:
- 5分：有明确证明（如医院证明、家长说明等）
- 4分：理由充分但无书面证明
- 3分：理由合理但细节不足
- 2分：理由模糊
- 1分：明显不合理
- 0分：违反学校规定

待审核内容：
{reason}

请返回严格遵循以下格式的JSON:
{{
    "score": 总分数,
    "details": {{
        "authenticity": 真实性得分,
        "urgency": 紧急性得分,
        "reasonableness": 合理性得分,
        "compliance": 规范性得分
    }},
    "reason": "审核意见(包含具体改进建议)",
    "suggestion": "对学生请假理由的优化建议"
}}"""

    # 请求参数
    # 修改后的系统提示词
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "你是一位严谨的学校班主任老师，负责审核学生的请假申请。请从以下方面严格评估：1)真实性必须有具体细节 2)紧急事务必须说明时间敏感性 3)请假时长必须合理 4)必须符合学校规定"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 600,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=20  # 增加超时时间
        )
        response.raise_for_status()

        result = response.json()

        # 多层数据校验
        if not isinstance(result, dict):
            raise ValueError("Invalid response format")

        choices = result.get("choices", [])
        if not choices or not isinstance(choices, list):
            raise ValueError("No choices in response")

        message = choices[0].get("message", {})
        if not isinstance(message, dict) or message.get("role") != "assistant":
            raise ValueError("Invalid message structure")

        content = message.get("content")
        if not content:
            raise ValueError("Empty response content")

        # 严格解析JSON内容
        try:
            content_data = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON content")

        # 验证评分数据
        required_keys = {"score", "details"}
        if not required_keys.issubset(content_data.keys()):
            raise ValueError("Missing required keys in response")

        # 记录审核结果
        logging.info(f"审核结果: {content_data}")

        # 判断是否通过
        # 更新缓存
        # 修改返回值为完整内容
        check_reason_validity.cache[cache_key] = {
            'is_valid': content_data.get("score", 0) >= min_score,
            'details': content_data
        }
        return check_reason_validity.cache[cache_key]

    except requests.exceptions.RequestException as e:
        logging.error(f"API请求失败: {str(e)}", exc_info=True)
        return False
    except Exception as e:
        logging.exception("审核过程中发生未预期错误")
        return False

# 初始化缓存
check_reason_validity.cache = {}

# 使用示例
if __name__ == "__main__":
    os.environ["DEEPSEEK_API_KEY"] = "your_api_key_here"
    test_reason = "明天需要照顾生病的宠物狗"
    is_valid = check_reason_validity(test_reason)
    print(f"审核结果: {'通过' if is_valid else '不通过'}")