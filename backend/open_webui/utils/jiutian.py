"""
九天平台相关工具函数
Jiutian Platform utility functions
"""

import time
import jwt
import logging
from typing import Optional, List, Dict, Any
from open_webui.config import JIUTIAN_API_KEY, JIUTIAN_API_BASE, JIUTIAN_MODEL_IDS

log = logging.getLogger(__name__)


def generate_jiutian_token(apikey: Optional[str] = None, expire_seconds: int = 3600) -> str:
    """
    生成九天平台的JWT token
    Generate JWT token for Jiutian Platform
    
    Args:
        apikey: API密钥，格式为 "id.secret"，如果为None则使用配置中的值
        expire_seconds: token过期时间（秒），默认1小时
        
    Returns:
        str: 生成的JWT token
        
    Raises:
        ValueError: 当API密钥格式无效时
        Exception: 当token生成失败时
    """
    try:
        # 使用传入的apikey或配置中的默认值
        api_key = apikey or JIUTIAN_API_KEY.value
        
        if not api_key:
            raise ValueError("九天平台API密钥未配置")
            
        # 解析API密钥
        try:
            key_id, secret = api_key.split('.', 1)
        except ValueError:
            raise ValueError("无效的API密钥格式，应为 'id.secret'")
        
        if not key_id or not secret:
            raise ValueError("API密钥ID或密钥为空")
        
        # 构建JWT payload
        current_time = int(time.time())
        payload = {
            "api_key": key_id,
            "exp": current_time + expire_seconds,
            "timestamp": current_time,
        }
        
        # JWT headers
        headers = {
            'alg': 'HS256', 
            'typ': 'JWT'
        }
        
        # 生成token
        token = jwt.encode(
            payload,
            secret,
            algorithm="HS256",
            headers=headers
        )
        
        log.debug(f"成功生成九天平台JWT token，过期时间: {expire_seconds}秒")
        return token
        
    except Exception as e:
        log.error(f"生成九天平台JWT token失败: {str(e)}")
        raise Exception(f"Token生成失败: {str(e)}")


def get_jiutian_api_base() -> str:
    """
    获取九天平台API基础地址
    Get Jiutian Platform API base URL
    
    Returns:
        str: API基础地址
    """
    return JIUTIAN_API_BASE.value


def get_jiutian_model_ids() -> List[str]:
    """
    获取九天平台可用的模型ID列表
    Get available Jiutian Platform model IDs
    
    Returns:
        List[str]: 模型ID列表
    """
    model_ids = JIUTIAN_MODEL_IDS.value
    if isinstance(model_ids, list):
        return model_ids
    elif isinstance(model_ids, str):
        # 如果是字符串，尝试按逗号分割
        return [mid.strip() for mid in model_ids.split(',') if mid.strip()]
    else:
        return []


def validate_jiutian_config() -> Dict[str, Any]:
    """
    验证九天平台配置
    Validate Jiutian Platform configuration
    
    Returns:
        Dict[str, Any]: 验证结果，包含 'valid' (bool) 和 'errors' (List[str])
    """
    errors = []
    
    # 检查API密钥
    api_key = JIUTIAN_API_KEY.value
    if not api_key:
        errors.append("九天平台API密钥未配置")
    else:
        try:
            key_id, secret = api_key.split('.', 1)
            if not key_id or not secret:
                errors.append("API密钥格式无效")
        except ValueError:
            errors.append("API密钥格式无效，应为 'id.secret'")
    
    # 检查API基础地址
    api_base = JIUTIAN_API_BASE.value
    if not api_base:
        errors.append("九天平台API基础地址未配置")
    elif not api_base.startswith(('http://', 'https://')):
        errors.append("API基础地址格式无效，应以http://或https://开头")
    
    # 检查模型ID列表
    model_ids = get_jiutian_model_ids()
    if not model_ids:
        errors.append("九天平台模型ID列表为空")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


def format_jiutian_history(messages: List[Dict[str, Any]]) -> List[Any]:
    """
    将OpenAI格式的消息历史转换为九天平台格式
    Convert OpenAI format message history to Jiutian Platform format
    
    Args:
        messages: OpenAI格式的消息列表
        
    Returns:
        List[Any]: 九天平台格式的历史记录
    """
    history = []
    
    # 九天平台的历史格式似乎是扁平化的数组
    # 根据文档示例：["问1", "答1", ["问2", "答2"]]
    for i in range(0, len(messages) - 1, 2):  # 跳过最后一条消息（当前问题）
        if i + 1 < len(messages):
            user_msg = messages[i]
            assistant_msg = messages[i + 1]
            
            if user_msg.get('role') == 'user' and assistant_msg.get('role') == 'assistant':
                if i == 0:
                    # 第一对问答直接添加
                    history.extend([user_msg.get('content', ''), assistant_msg.get('content', '')])
                else:
                    # 后续问答用数组包装
                    history.append([user_msg.get('content', ''), assistant_msg.get('content', '')])
    
    return history


def build_jiutian_request_payload(
    model_id: str,
    prompt: str,
    history: List[Any] = None,
    stream: bool = True,
    temperature: float = 0.8,
    top_p: float = 0.95
) -> Dict[str, Any]:
    """
    构建九天平台API请求载荷
    Build Jiutian Platform API request payload
    
    Args:
        model_id: 模型ID
        prompt: 用户提示
        history: 对话历史
        stream: 是否流式返回
        temperature: 温度参数
        top_p: top_p参数
        
    Returns:
        Dict[str, Any]: 请求载荷
    """
    payload = {
        "modelId": model_id,
        "prompt": prompt,
        "history": history or [],
        "stream": stream,
        "params": {
            "temperature": temperature,
            "top_p": top_p
        }
    }
    
    return payload