import os
import requests
import json
import logging
from typing import Dict, Any

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def check_reason_validity(reason: str, min_score: int = 12) -> bool:
    """
    审核请假理由有效性的改进版本

    参数:
        reason (str): 待审核的请假理由文本
        min_score (int): 通过的最低总分（默认12分）

    返回:
        bool: 是否通过审核
    """
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

    # 优化后的提示词（包含示例）
    prompt = f"""作为专业的人事审核助手，请从以下维度严格审核请假理由：

评分维度（每个维度0-5分）:
1. 真实性 - 是否有明确细节支持理由
2. 紧急性 - 是否不可推迟
3. 合理性 - 时间长度是否合适
4. 规范性 - 是否符合公司政策

示例审核:
请假内容：祖父去世需参加葬礼
评分：真实性5 紧急性5 合理性4 规范性5 → 总分19

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
    "reason": "简要审核意见"
}}"""

    # 请求参数
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "你是一个严谨的人事审核助手，严格按照评分标准进行量化评估"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 500,
        "response_format": {"type": "json_object"}
    }

    try:
        # 带重试的请求（生产环境建议使用retrying库）
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()

        # 解析响应
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
        return content_data.get("score", 0) >= min_score

    except requests.exceptions.HTTPError as e:
        logging.error(f"API请求失败: {e.response.status_code} - {e.response.text}")
        return False
    except (requests.exceptions.RequestException, ValueError) as e:
        logging.error(f"处理失败: {str(e)}")
        return False
    except Exception as e:
        logging.exception("未处理的异常发生")
        return False


# 使用示例
if __name__ == "__main__":
    # 设置环境变量（测试用，实际应通过系统环境设置）
    os.environ["DEEPSEEK_API_KEY"] = "your_api_key_here"

    test_reason = "明天需要照顾生病的宠物狗"
    is_valid = check_reason_validity(test_reason)
    print(f"审核结果: {'通过' if is_valid else '不通过'}")