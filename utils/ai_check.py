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
    prompt = f"""作为学校的辅导员老师，请从以下维度严格审核学生请假理由：

评分维度（每个维度0-5分）:
1. 真实性 - 是否有合理细节支持（如课程安排、学术活动等）
2. 必要性 - 是否影响正常学业活动
3. 规范性 - 是否符合高校请假流程
4. 学业影响 - 请假时长对学习的影响程度

评分标准:
- 4分：理由充分合理（如学术会议、专业竞赛）
- 3分：理由合理但需要补充细节
- 2分：理由普通但可以接受
- 1分：理由牵强需要改进
- 0分：违反校规或明显不合理

待审核内容：
{reason}

请返回严格遵循以下格式的JSON:
{{
    "score": 总分数,
    "details": {{
        "authenticity": 真实性得分,
        "necessity": 必要性得分,
        "compliance": 规范性得分,
        "academic_impact": 学业影响得分
    }},
    "reason": "审核意见(包含具体改进建议)",
    "suggestion": "请假流程优化建议"
}}"""

    # 请求参数
    # 修改后的系统提示词
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "你是一位通情达理的大学辅导员，负责审核学生的请假申请。请结合大学生实际情况评估：1)理由合理性 2)学业影响程度 3)是否符合高校管理规定 4)是否有改进空间"
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