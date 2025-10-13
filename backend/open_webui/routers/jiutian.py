"""
九天平台API路由
Jiutian Platform API Router
"""

import asyncio
import json
import logging
from typing import Optional, List, Dict, Any
import aiohttp
from fastapi import Depends, HTTPException, Request, APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from open_webui.models.users import UserModel
from open_webui.utils.auth import get_verified_user
from open_webui.utils.jiutian import (
    generate_jiutian_token,
    get_jiutian_api_base,
    get_jiutian_model_ids,
    validate_jiutian_config,
    format_jiutian_history,
    build_jiutian_request_payload
)
from open_webui.config import ENABLE_JIUTIAN_MULTI_CHAT
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("JIUTIAN", logging.INFO))

router = APIRouter()


class JiutianMultiChatRequest(BaseModel):
    """九天平台多智能体聊天请求模型"""
    prompt: str
    selected_model_ids: List[str]
    history: Optional[List[Dict[str, Any]]] = []
    stream: Optional[bool] = True
    temperature: Optional[float] = 0.8
    top_p: Optional[float] = 0.95


class JiutianConfigResponse(BaseModel):
    """九天平台配置响应模型"""
    enabled: bool
    available_models: List[str]
    api_base: str
    config_valid: bool
    errors: List[str]


@router.get("/config")
async def get_jiutian_config(request: Request, user=Depends(get_verified_user)):
    """
    获取九天平台配置信息
    Get Jiutian Platform configuration
    """
    try:
        # 验证配置
        validation_result = validate_jiutian_config()
        
        # 获取可用模型
        available_models = get_jiutian_model_ids() if validation_result['valid'] else []
        
        return JiutianConfigResponse(
            enabled=ENABLE_JIUTIAN_MULTI_CHAT.value,
            available_models=available_models,
            api_base=get_jiutian_api_base(),
            config_valid=validation_result['valid'],
            errors=validation_result['errors']
        )
    except Exception as e:
        log.error(f"获取九天平台配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


async def stream_jiutian_response(
    model_id: str,
    payload: Dict[str, Any],
    token: str,
    api_base: str
) -> str:
    """
    处理单个模型的流式响应
    Handle streaming response for a single model
    """
    url = f"{api_base}/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    timeout = aiohttp.ClientTimeout(total=300)  # 5分钟超时
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log.error(f"九天API请求失败 (模型: {model_id}): {response.status} - {error_text}")
                    yield f"data: {json.dumps({'modelId': model_id, 'error': f'API请求失败: {response.status}'})}\n\n"
                    return
                
                # 处理流式响应
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data:'):
                        try:
                            # 解析九天平台的响应数据
                            data_str = line[5:].strip()  # 移除 'data:' 前缀
                            if data_str:
                                data = json.loads(data_str)
                                
                                # 包装响应数据，添加模型ID标识
                                wrapped_data = {
                                    'modelId': model_id,
                                    'chunk': data
                                }
                                
                                yield f"data: {json.dumps(wrapped_data)}\n\n"
                                
                                # 检查是否结束
                                if data.get('finished') == 'Stop' or data.get('delta') == '[EOS]':
                                    break
                                    
                        except json.JSONDecodeError as e:
                            log.error(f"解析九天API响应失败 (模型: {model_id}): {str(e)}")
                            continue
                        except Exception as e:
                            log.error(f"处理九天API响应失败 (模型: {model_id}): {str(e)}")
                            continue
                            
    except asyncio.TimeoutError:
        log.error(f"九天API请求超时 (模型: {model_id})")
        yield f"data: {json.dumps({'modelId': model_id, 'error': '请求超时'})}\n\n"
    except Exception as e:
        log.error(f"九天API请求异常 (模型: {model_id}): {str(e)}")
        yield f"data: {json.dumps({'modelId': model_id, 'error': f'请求异常: {str(e)}'})}\n\n"


async def aggregate_multi_model_responses(
    selected_model_ids: List[str],
    prompt: str,
    history: List[Any],
    stream: bool = True,
    temperature: float = 0.8,
    top_p: float = 0.95
):
    """
    聚合多个模型的响应
    Aggregate responses from multiple models
    """
    try:
        # 验证配置
        validation_result = validate_jiutian_config()
        if not validation_result['valid']:
            error_msg = f"九天平台配置无效: {', '.join(validation_result['errors'])}"
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
            return
        
        # 生成token
        token = generate_jiutian_token()
        api_base = get_jiutian_api_base()
        
        # 转换历史记录格式
        jiutian_history = format_jiutian_history(history)
        
        # 为每个模型创建异步任务
        tasks = []
        for model_id in selected_model_ids:
            # 构建请求载荷
            payload = build_jiutian_request_payload(
                model_id=model_id,
                prompt=prompt,
                history=jiutian_history,
                stream=stream,
                temperature=temperature,
                top_p=top_p
            )
            
            # 创建异步任务
            task = stream_jiutian_response(model_id, payload, token, api_base)
            tasks.append(task)
        
        # 并发处理所有模型的响应
        async def process_all_responses():
            async def process_single_response(response_generator):
                async for chunk in response_generator:
                    yield chunk
            
            # 创建所有响应生成器的任务
            response_tasks = [process_single_response(task) for task in tasks]
            
            # 使用asyncio.gather来并发处理
            try:
                async for chunk in merge_async_generators(response_tasks):
                    yield chunk
            except Exception as e:
                log.error(f"处理多模型响应时发生错误: {str(e)}")
                yield f"data: {json.dumps({'error': f'处理响应时发生错误: {str(e)}'})}\n\n"
        
        async for chunk in process_all_responses():
            yield chunk
            
        # 发送结束信号
        yield f"data: {json.dumps({'finished': True})}\n\n"
        
    except Exception as e:
        log.error(f"聚合多模型响应失败: {str(e)}")
        yield f"data: {json.dumps({'error': f'聚合响应失败: {str(e)}'})}\n\n"


async def merge_async_generators(generators):
    """
    合并多个异步生成器的输出
    Merge outputs from multiple async generators
    """
    import asyncio
    from asyncio import Queue
    
    queue = Queue()
    active_generators = set()
    
    async def feed_queue(gen, gen_id):
        try:
            async for item in gen:
                await queue.put((gen_id, item))
        except Exception as e:
            log.error(f"生成器 {gen_id} 发生错误: {str(e)}")
        finally:
            active_generators.discard(gen_id)
            if not active_generators:
                await queue.put((None, None))  # 结束信号
    
    # 启动所有生成器
    for i, gen in enumerate(generators):
        active_generators.add(i)
        asyncio.create_task(feed_queue(gen, i))
    
    # 从队列中读取数据
    while True:
        gen_id, item = await queue.get()
        if gen_id is None:  # 结束信号
            break
        yield item


@router.post("/multi_chat/completions")
async def multi_chat_completions(
    request: Request,
    form_data: JiutianMultiChatRequest,
    user=Depends(get_verified_user)
):
    """
    九天平台多智能体聊天API
    Jiutian Platform multi-agent chat API
    """
    try:
        # 检查功能是否启用
        if not ENABLE_JIUTIAN_MULTI_CHAT.value:
            raise HTTPException(status_code=403, detail="九天平台多智能体聊天功能未启用")
        
        # 验证请求参数
        if not form_data.selected_model_ids:
            raise HTTPException(status_code=400, detail="未选择任何模型")
        
        if not form_data.prompt.strip():
            raise HTTPException(status_code=400, detail="提示内容不能为空")
        
        # 验证模型ID
        available_models = get_jiutian_model_ids()
        invalid_models = [mid for mid in form_data.selected_model_ids if mid not in available_models]
        if invalid_models:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的模型ID: {', '.join(invalid_models)}"
            )
        
        log.info(f"用户 {user.email} 发起九天平台多智能体聊天，模型: {form_data.selected_model_ids}")
        
        # 返回流式响应
        return StreamingResponse(
            aggregate_multi_model_responses(
                selected_model_ids=form_data.selected_model_ids,
                prompt=form_data.prompt,
                history=form_data.history,
                stream=form_data.stream,
                temperature=form_data.temperature,
                top_p=form_data.top_p
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"九天平台多智能体聊天失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"聊天请求失败: {str(e)}")


@router.get("/models")
async def get_available_models(request: Request, user=Depends(get_verified_user)):
    """
    获取九天平台可用模型列表
    Get available Jiutian Platform models
    """
    try:
        # 验证配置
        validation_result = validate_jiutian_config()
        if not validation_result['valid']:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "九天平台配置无效",
                    "details": validation_result['errors']
                }
            )
        
        # 获取模型列表
        models = get_jiutian_model_ids()
        
        return {
            "models": [
                {
                    "id": model_id,
                    "name": f"九天-{model_id}",
                    "provider": "jiutian"
                }
                for model_id in models
            ]
        }
        
    except Exception as e:
        log.error(f"获取九天平台模型列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")